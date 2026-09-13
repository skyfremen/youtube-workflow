import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent
MANIFEST_PATH = BOT_ROOT / "planning" / "PLANNER_MATERIALIZATION.json"
RULES_SHA = "1" * 40


def _blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _materialize(root: Path):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    required = [manifest["connector_materialization"]["manifest_path"]]
    required += manifest["shared_required_python_files"]
    required += manifest["shared_required_data_files"]
    for profile in ("daily", "adhoc"):
        entry = manifest["profile_required_files"][profile]
        required += entry["python_files"]
        required += entry["data_files"]
    required = list(dict.fromkeys(required))

    for relative in required:
        source = REPO_ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    evidence = {
        "schema_version": 1,
        "rules_source_sha": RULES_SHA,
        "files": {
            relative: {
                "rules_source_sha": RULES_SHA,
                "blob_sha": _blob_sha(root / relative),
            }
            for relative in required
        },
    }
    evidence_path = root / "materialization-evidence.json"
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest, evidence, evidence_path


def _run(root: Path, profile: str, evidence_path: Path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "youtube-shorts-bot")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "planning.materialization_verify",
            "--profile",
            profile,
            "--root",
            str(root),
            "--rules-source-sha",
            RULES_SHA,
            "--evidence",
            str(evidence_path),
        ],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class MaterializationVerifyTests(unittest.TestCase):
    def test_exact_connector_materialization_passes_without_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest, _evidence, evidence_path = _materialize(root)

            self.assertFalse((root / ".git").exists())
            result = _run(root, "adhoc", evidence_path)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            expected_required = 1 + len(manifest["shared_required_python_files"])
            expected_required += len(manifest["shared_required_data_files"])
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["required_files"], expected_required)
            self.assertEqual(payload["verified_files"], expected_required)
            self.assertEqual(
                payload["compiled_python_files"],
                len(manifest["shared_required_python_files"]),
            )
            self.assertEqual(
                set(payload["critical_imports_verified"]),
                set(manifest["connector_materialization"]["critical_imports"]),
            )
            self.assertEqual(payload["errors"], [])

    def test_tampered_materialized_file_fails_with_exact_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _manifest, _evidence, evidence_path = _materialize(root)
            relative = "youtube-shorts-bot/planning/planner_profiles.py"
            path = root / relative
            path.write_text(path.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")

            result = _run(root, "adhoc", evidence_path)

            self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "FAIL")
            matches = [
                error
                for error in payload["errors"]
                if error["code"] == "blob_sha_mismatch" and error.get("path") == relative
            ]
            self.assertEqual(len(matches), 1)

    def test_mixed_source_sha_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _manifest, evidence, evidence_path = _materialize(root)
            relative = "youtube-shorts-bot/planning/planner_contract.py"
            evidence["files"][relative]["rules_source_sha"] = "2" * 40
            evidence_path.write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            result = _run(root, "daily", evidence_path)

            self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "FAIL")
            matches = [
                error
                for error in payload["errors"]
                if error["code"] == "mixed_source_sha" and error.get("path") == relative
            ]
            self.assertEqual(len(matches), 1)


if __name__ == "__main__":
    unittest.main()
