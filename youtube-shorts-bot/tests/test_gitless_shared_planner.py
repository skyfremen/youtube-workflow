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
        self.assertFalse(
            manifest["chatgpt_work_requirements"][
                "full_background_registry_local_copy_required"
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
        self.assertEqual(contract["profiles"]["daily"]["normal_next_day"]["expected_candidates"], 24)
        self.assertEqual(contract["profiles"]["daily"]["reserve_candidate_count"], 0)
        self.assertEqual(contract["profiles"]["adhoc"]["expected_candidates"], 1)
        self.assertEqual(contract["profiles"]["adhoc"]["allowed_planning_modes"], ["manual_on_demand"])
        self.assertEqual(contract["profiles"]["adhoc"]["reserve_candidate_count"], 0)
        self.assertFalse(contract["profiles"]["daily"]["global_media_readiness_required"])
        self.assertFalse(contract["profiles"]["adhoc"]["global_media_readiness_required"])
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
        self.assertFalse(contract["background"]["planner_freezes_playback_rate"])
        self.assertTrue(contract["background"]["runtime_derives_playback_rate_after_tts"])
        self.assertTrue(contract["background"]["canonical_fallback_category"])


if __name__ == "__main__":
    unittest.main()
