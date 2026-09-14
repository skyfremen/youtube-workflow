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

    def test_profiles_cannot_own_shared_schema_or_creative_contracts(self):
        self.assertTrue(assert_profiles_do_not_override_shared_contract())
        fields = set(PlannerProfile.__dataclass_fields__)
        for forbidden in (
            "schema",
            "voice",
            "narration",
            "punchline",
            "request_validator",
        ):
            self.assertFalse(
                any(forbidden in field for field in fields),
                f"shared contract leaked into profile field containing {forbidden}",
            )

    def test_profiles_express_simplified_cardinality_and_media_routing(self):
        self.assertEqual(DAILY.pool_size, 24)
        self.assertEqual(ADHOC.pool_size, 1)
        self.assertEqual(DAILY.publication_template["mode"], "scheduled")
        self.assertEqual(ADHOC.publication_template["mode"], "immediate")
        self.assertEqual(ADHOC.planning_modes, frozenset({"manual_on_demand"}))
        self.assertEqual(ADHOC.fixed_target_count, 1)
        self.assertEqual(DAILY.normal_target_count, 24)
        self.assertEqual(DAILY.reserve_candidate_count, 0)
        self.assertEqual(ADHOC.reserve_candidate_count, 0)
        self.assertFalse(DAILY.global_media_readiness_required)
        self.assertFalse(ADHOC.global_media_readiness_required)
        self.assertFalse(DAILY.automatic_replenishment_enabled)
        self.assertFalse(ADHOC.automatic_replenishment_enabled)
        self.assertTrue(DAILY.selected_background_validation_required)
        self.assertTrue(ADHOC.selected_background_validation_required)
        self.assertTrue(DAILY.background_same_category_required)
        self.assertTrue(ADHOC.background_same_category_required)

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
        self.assertTrue(checkpoint["single_mechanical_authority"])
        self.assertIn("repository checkout", checkpoint["forbidden_local_dependencies"])
        self.assertIn(".git metadata", checkpoint["forbidden_local_dependencies"])
        self.assertIn(
            "media-library/backgrounds.json local copy",
            checkpoint["forbidden_local_dependencies"],
        )

    def test_connector_is_canonical_without_git_or_replenishment_dependency(self):
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
        self.assertFalse(requirements["checkout_required"])
        self.assertFalse(requirements["repository_tree_materialization_required"])
        self.assertEqual(requirements["planning_passes"], 4)
        self.assertFalse(requirements["post_commit_planner_monitoring"])
        evidence = manifest["connector_evidence"]
        self.assertEqual(evidence["schema_version"], 2)
        self.assertNotIn("media_readiness", evidence["required_fields"])
        self.assertNotIn("replenishment", evidence["required_fields"])
        self.assertIn("media_readiness", evidence["forbidden_fields"])
        self.assertIn("replenishment", evidence["forbidden_fields"])

    def test_shared_prompt_is_canonical_four_pass_contract(self):
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
        self.assertIn("Exactly four", shared)
        self.assertIn("CHATGPT / WORK PLANNING ENDS", shared)
        self.assertIn("Global media-library readiness is **not**", shared)
        self.assertIn("docs/private/PLANNER_PROMPT.md", daily)
        self.assertIn("docs/private/PLANNER_PROMPT.md", adhoc)
        self.assertIn("--profile daily", daily)
        self.assertIn("--profile adhoc", adhoc)
        self.assertNotIn("--verify-git-head", daily)
        self.assertNotIn("--verify-git-head", adhoc)

    def test_background_strategy_separates_maintenance_from_planning(self):
        strategy = (BOT_ROOT / "docs" / "background-media-strategy.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("maintenance signal", strategy)
        self.assertIn("not a Daily/Ad-hoc planner admission gate", strategy)
        self.assertIn("same category", strategy)
        self.assertIn("canonical fallback category", strategy)
        self.assertIn("does **not** choose, calculate or freeze playback rate", strategy)
        self.assertIn("separate media-library maintenance", strategy.lower())
        self.assertIn("Historical replenishment", strategy)


if __name__ == "__main__":
    unittest.main()
