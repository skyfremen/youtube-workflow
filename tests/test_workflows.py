import hashlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
STRUCTURE_HASHES = {
    "backgrounds.yml": "62a7fff2f653ed81dd1377d3e38f8b1608ea04f016494a5eef56d1f8896df563",
    "context.yml": "02778b1bf3b875163d7b08e63c0c1fdf150b399d794169e257e611a896aaee49",
    "dispatch.yml": "1e8631c6e1b97aaf363a0a93b7cf9273a375d54099738dd39c890ea958bd9bc8",
    "finalize-draft.yml": "8fa1e7b779cc604d26ea5e5f8cca751e42edaa5a428dd5055af327a21f486394",
    "rerender.yml": "ff5227d8ff587799c94f505c141b55dc13dc9c3e80e65dcc33d9d7037bc49f63",
    "result.yml": "1a816ae9c75818b5652fe9fb5bc115ccd4bea3c69c3b67f7846d89d0e95c2c25",
}


class WorkflowPinTests(unittest.TestCase):
    def test_all_external_actions_are_full_sha_pinned(self):
        for path in sorted(WORKFLOWS.glob("*.yml")):
            for target in re.findall(r"\buses:\s*([^\s#]+)", path.read_text(encoding="utf-8")):
                if target.startswith("./"):
                    continue
                with self.subTest(workflow=path.name, target=target):
                    self.assertRegex(target, r"^[^@\s]+@[0-9a-f]{40}$")

    def test_exactly_six_checkouts_use_approved_v7_pin(self):
        references = []
        for path in sorted(WORKFLOWS.glob("*.yml")):
            references.extend(
                (path.name, sha, version)
                for sha, version in re.findall(
                    r"actions/checkout@([0-9a-f]{40})\s+#\s+(v[^\s]+)",
                    path.read_text(encoding="utf-8"),
                )
            )
        self.assertEqual(6, len(references))
        self.assertEqual({CHECKOUT_SHA}, {sha for _name, sha, _version in references})
        self.assertEqual({"v7.0.1"}, {version for _name, _sha, version in references})

    def test_checkout_upgrade_changes_no_other_workflow_structure(self):
        for name, expected in STRUCTURE_HASHES.items():
            source = (WORKFLOWS / name).read_text(encoding="utf-8")
            normalized = re.sub(
                r"actions/checkout@[0-9a-f]{40} # v[^\n]+",
                "actions/checkout@<PIN> # <VERSION>",
                source,
            )
            with self.subTest(workflow=name):
                self.assertEqual(expected, hashlib.sha256(normalized.encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
