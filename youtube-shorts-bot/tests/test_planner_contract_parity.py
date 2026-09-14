import unittest
from pathlib import Path

from media import continuous_background
from planning import connector_checkpoint, planner_core
from planning.planner_profiles import ADHOC, DAILY
from validation import validate_content


BOT_ROOT = Path(__file__).resolve().parents[1]


class PlannerContractParityTests(unittest.TestCase):
    def test_standalone_checkpoint_matches_repository_contract_versions(self):
        self.assertEqual(
            connector_checkpoint.POOL_SCHEMA_VERSION,
            planner_core.POOL_SCHEMA_VERSION,
        )
        self.assertEqual(
            connector_checkpoint.REQUEST_SCHEMA_VERSION,
            validate_content.SCHEMA_VERSION,
        )

    def test_standalone_checkpoint_matches_profile_contract(self):
        pairs = (("daily", DAILY), ("adhoc", ADHOC))
        for name, profile in pairs:
            with self.subTest(profile=name):
                standalone = connector_checkpoint.PROFILE[name]
                self.assertEqual(standalone["pool_type"], profile.pool_type)
                self.assertEqual(standalone["pool_size"], profile.pool_size)
                self.assertEqual(
                    standalone["planning_modes"], set(profile.planning_modes)
                )
                self.assertEqual(
                    standalone["fixed_target_count"], profile.fixed_target_count
                )
                self.assertEqual(
                    standalone.get("normal_target_count"), profile.normal_target_count
                )
                self.assertEqual(
                    standalone["publication"], profile.publication_template
                )

    def test_standalone_checkpoint_matches_sequence_contract(self):
        self.assertEqual(
            connector_checkpoint.BACKGROUND_MODE,
            continuous_background.CONCATENATED_FIT_TO_SHORT_MODE,
        )
        self.assertEqual(
            connector_checkpoint.MIN_SEQUENCE_CLIP_SECONDS,
            continuous_background.MIN_SEQUENCE_CLIP_SECONDS,
        )
        self.assertEqual(
            connector_checkpoint.MIN_SEQUENCE_CLIPS,
            continuous_background.MIN_SEQUENCE_CLIPS,
        )
        self.assertEqual(
            connector_checkpoint.MAX_SEQUENCE_CLIPS,
            continuous_background.MAX_SEQUENCE_CLIPS,
        )
        self.assertEqual(
            connector_checkpoint.MIN_SEQUENCE_SOURCE_SECONDS,
            continuous_background.MIN_SEQUENCE_SOURCE_SECONDS,
        )
        self.assertEqual(
            connector_checkpoint.PREFERRED_SEQUENCE_SOURCE_SECONDS,
            continuous_background.PREFERRED_SEQUENCE_SOURCE_SECONDS,
        )
        self.assertEqual(
            connector_checkpoint.MAX_SEQUENCE_SOURCE_SECONDS,
            continuous_background.MAX_SEQUENCE_SOURCE_SECONDS,
        )
        self.assertNotIn("playback_rate", connector_checkpoint.SEQUENCE_SEGMENT_KEYS)

    def test_profile_rule_docs_describe_current_request_ownership(self):
        for name in ("DAILY_PLANNER_RULES.md", "ADHOC_PLANNER_RULES.md"):
            with self.subTest(file=name):
                text = (BOT_ROOT / "planning" / name).read_text(encoding="utf-8")
                lower = text.lower()
                self.assertIn("schema-v7", lower)
                self.assertIn("do not freeze playback rate", lower)
                self.assertIn("runtime derives", lower)
                self.assertNotIn("schema v5 ranked-pool contract", lower)
                self.assertNotIn("selection_enabled=false", lower)
                self.assertNotIn("git rev-parse head", lower)

    def test_profile_rule_docs_preserve_current_ranked_pool_contract(self):
        daily = (BOT_ROOT / "planning" / "DAILY_PLANNER_RULES.md").read_text(
            encoding="utf-8"
        )
        adhoc = (BOT_ROOT / "planning" / "ADHOC_PLANNER_RULES.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("exactly **36** complete candidates", daily)
        self.assertIn("target count: exactly **24**", daily)
        self.assertIn("exactly **5** complete candidates", adhoc)
        self.assertIn("`target_count=1`", adhoc)
        self.assertIn("manual_on_demand", adhoc)


if __name__ == "__main__":
    unittest.main()
