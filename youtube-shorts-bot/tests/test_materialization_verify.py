import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


BOT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = BOT_ROOT / "planning" / "PLANNER_MATERIALIZATION.json"
CHECKPOINT = BOT_ROOT / "planning" / "connector_checkpoint.py"
LEGACY_VERIFY = BOT_ROOT / "planning" / "materialization_verify.py"


class MaterializationVerifyTests(unittest.TestCase):
    def test_legacy_materialization_verify_is_not_canonical_chatgpt_dependency(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        requirements = manifest["chatgpt_work_requirements"]
        self.assertFalse(requirements["repository_tree_materialization_required"])
        self.assertFalse(requirements["materialization_verify_required"])
        self.assertEqual(
            manifest["connector_native_checkpoint"]["path"],
            "youtube-shorts-bot/planning/connector_checkpoint.py",
        )
        # The old developer/CI helper may remain for historical compatibility, but
        # ChatGPT/Work correctness no longer depends on invoking it.
        self.assertTrue(LEGACY_VERIFY.is_file())

    def test_exact_connector_checkpoint_runs_from_one_file_without_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "connector_checkpoint.py"
            shutil.copyfile(CHECKPOINT, target)
            self.assertFalse((root / ".git").exists())
            completed = subprocess.run(
                [sys.executable, str(target), "contract"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        execution = payload["execution_environment"]
        self.assertEqual(execution["canonical_mode"], "connector_native_checkpoint")
        self.assertFalse(execution["repository_tree_materialization_required"])
        self.assertFalse(execution["full_background_registry_local_copy_required"])
        self.assertEqual(
            execution["local_files_required"],
            [
                "connector_checkpoint.py",
                "authored pool JSON",
                "small connector-evidence JSON",
            ],
        )


if __name__ == "__main__":
    unittest.main()
