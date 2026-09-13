import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


BOT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = BOT_ROOT / "planning" / "PLANNER_MATERIALIZATION.json"
CHECKPOINT = BOT_ROOT / "planning" / "connector_checkpoint.py"


class GitlessSharedPlannerTests(unittest.TestCase):
    def test_connector_checkpoint_runs_both_profiles_contract_without_repository_metadata(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["planner_bootstrap"]["preferred"],
            "connector_native_checkpoint",
        )
        self.assertFalse(
            manifest["chatgpt_work_requirements"][
                "repository_tree_materialization_required"
            ]
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "connector_checkpoint.py"
            shutil.copyfile(CHECKPOINT, target)
            self.assertFalse((root / ".git").exists())
            self.assertEqual(list(root.iterdir()), [target])
            completed = subprocess.run(
                [sys.executable, str(target), "contract"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        contract = json.loads(completed.stdout)
        self.assertEqual(contract["profiles"]["daily"]["pool_size"], 36)
        self.assertEqual(contract["profiles"]["adhoc"]["pool_size"], 5)
        self.assertFalse(contract["execution_environment"]["git_checkout_required"])
        self.assertFalse(
            contract["execution_environment"][
                "repository_tree_materialization_required"
            ]
        )
        self.assertFalse(
            contract["execution_environment"][
                "full_background_registry_local_copy_required"
            ]
        )


if __name__ == "__main__":
    unittest.main()
