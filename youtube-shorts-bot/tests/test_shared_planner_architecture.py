import json
import unittest
from pathlib import Path

from planning import adhoc_precommit, daily_precommit
from planning.planner_contract import build_contract
from planning.planner_profiles import (
    ADHOC,
    DAILY,
    PlannerProfile,
    assert_profiles_do_not_override_shared_contract,
)


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent
MANIFEST = BOT_ROOT / "planning" / "PLANNER_MATERIALIZATION.json"


class SharedPlannerArchitectureTests(unittest.TestCase):
    def test_daily_and_adhoc_share_one_contract_fingerprint(self):
        contract = build_contract()
        profiles = contract["profiles"]
        self.assertEqual(
            profiles["daily"]["shared_contract_fingerprint"],
            profiles["adhoc"]["shared_contract_fingerprint"],
        )
        self.assertEqual(
            profiles["daily"]["shared_contract_fingerprint"],
            contract["shared_contract_fingerprint"],
        )
        self.assertEqual(
            contract["shared_implementation"]["developer_ci_precommit"],
            "planning.planner_precommit",
        )
        self.assertEqual(
            contract["shared_implementation"]["chatgpt_work_checkpoint"],
            "planning/connector_checkpoint.py",
        )
        self.assertEqual(
            contract["shared_implementation"]["drift_classification"],
            "planning.planner_drift",
        )

    def test_profiles_cannot_own_shared_validation_contracts(self):
        self.assertTrue(assert_profiles_do_not_override_shared_contract())
        fields = set(PlannerProfile.__dataclass_fields__)
        for forbidden in (
            "schema",
            "semantic",
            "background",
            "voice",
            "narration",
            "punchline",
            "media_readiness",
            "request_validator",
        ):
            self.assertFalse(
                any(forbidden in field for field in fields),
                f"shared contract leaked into profile field containing {forbidden}",
            )

    def test_profiles_contain_only_expected_mode_differences(self):
        self.assertEqual(DAILY.pool_size, 36)
        self.assertEqual(ADHOC.pool_size, 5)
        self.assertEqual(DAILY.publication_template["mode"], "scheduled")
        self.assertEqual(ADHOC.publication_template["mode"], "immediate")
        self.assertEqual(ADHOC.fixed_target_count, 1)
        self.assertEqual(DAILY.normal_target_count, 24)

    def test_legacy_precommit_modules_are_thin_shared_engine_wrappers(self):
        self.assertEqual(
            daily_precommit.SHARED_ENGINE_MODULE, "planning.planner_precommit"
        )
        self.assertEqual(
            adhoc_precommit.SHARED_ENGINE_MODULE, "planning.planner_precommit"
        )
        self.assertEqual(daily_precommit.PROFILE, "daily")
        self.assertEqual(adhoc_precommit.PROFILE, "adhoc")

    def test_connector_checkpoint_excludes_repository_tree_dependency(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checkpoint = manifest["connector_native_checkpoint"]
        self.assertEqual(
            checkpoint["path"], "youtube-shorts-bot/planning/connector_checkpoint.py"
        )
        self.assertTrue(checkpoint["standard_library_only"])
        self.assertFalse(checkpoint["repository_imports"])
        self.assertIn("repository checkout", checkpoint["forbidden_local_dependencies"])
        self.assertIn(".git metadata", checkpoint["forbidden_local_dependencies"])
        self.assertIn(
            "media-library/backgrounds.json local copy",
            checkpoint["forbidden_local_dependencies"],
        )

    def test_connector_is_canonical_without_git_dependency(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["planner_bootstrap"]["preferred"],
            "connector_native_checkpoint",
        )
        self.assertEqual(manifest["planner_bootstrap"]["fallback"], "none")
        self.assertFalse(
            manifest["planner_bootstrap"]["shell_git_attempted_in_chatgpt_work"]
        )
        requirements = manifest["chatgpt_work_requirements"]
        self.assertFalse(requirements["git_required"])
        self.assertFalse(requirements["git_executable_required"])
        self.assertFalse(requirements["checkout_required"])
        self.assertFalse(requirements["git_metadata_required"])
        self.assertFalse(requirements["repository_tree_materialization_required"])
        self.assertFalse(requirements["materialization_verify_required"])
        self.assertTrue(
            any(
                "GitHub Actions" in value
                for value in manifest["forbidden_bootstrap_requirements"]
            )
        )

    def test_shared_prompt_is_canonical_for_bootstrap(self):
        shared = (
            REPO_ROOT / "docs" / "private" / "PLANNER_PROMPT.md"
        ).read_text(encoding="utf-8")
        daily = (BOT_ROOT / "planning" / "DAILY_PLANNER_PROMPT.md").read_text(
            encoding="utf-8"
        )
        adhoc = (BOT_ROOT / "planning" / "ADHOC_PLANNER_PROMPT.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("one planner", shared.lower())
        self.assertIn("authorized GitHub connector/API", shared)
        self.assertIn("connector_checkpoint.py", shared)
        self.assertIn("CHECKPOINT_STAGING_BLOCKED", shared)
        self.assertIn("E_MEDIA_REPLENISH_EXHAUSTED", shared)
        self.assertIn("docs/private/PLANNER_PROMPT.md", daily)
        self.assertIn("docs/private/PLANNER_PROMPT.md", adhoc)
        self.assertIn("--profile daily", daily)
        self.assertIn("--profile adhoc", adhoc)
        self.assertNotIn("--verify-git-head", daily)
        self.assertNotIn("--verify-git-head", adhoc)

    def test_replenishment_visual_review_is_transport_adaptive_and_durable(self):
        shared = (
            REPO_ROOT / "docs" / "private" / "PLANNER_PROMPT.md"
        ).read_text(encoding="utf-8")
        strategy = (BOT_ROOT / "docs" / "background-media-strategy.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Background Management", shared)
        self.assertIn("review-decisions/<request_id>.json", shared)
        self.assertIn("authoritative session memory", shared)
        self.assertIn("E_MEDIA_REPLENISH_EXHAUSTED", shared)
        self.assertIn("DEFERRED_REPLENISHMENT", shared)

        self.assertIn("private Background Management review-evidence artifact", strategy)
        self.assertIn("GitHub connector delivery", strategy)
        self.assertIn("contact-sheet.jpg", strategy)
        self.assertIn("--input-dir", strategy)
        self.assertIn("EVIDENCE_ACCESS_BLOCKED", strategy)
        self.assertIn("REVIEW_EVIDENCE_TRANSPORT_FAILED", strategy)
        self.assertIn("GitHub Actions must never set `verified_preview`", strategy)
        self.assertIn("replenishment_session_id", strategy)
        self.assertIn("review-decisions/<request_id>.json", strategy)
        self.assertIn("attempt < 5", strategy)


if __name__ == "__main__":
    unittest.main()
