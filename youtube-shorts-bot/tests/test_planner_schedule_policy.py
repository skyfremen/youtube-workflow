import unittest
from datetime import datetime, timezone
from pathlib import Path

from planning.planner_core import canonical_normal_slots, validate_daily_slots
from planning.planner_profiles import DAILY


PLANNER = Path("youtube-shorts-bot/planning")
PROMPT = PLANNER / "DAILY_PLANNER_PROMPT.md"
RULES = PLANNER / "DAILY_PLANNER_RULES.md"


class PlannerSchedulePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (
            PROMPT.read_text(encoding="utf-8")
            + "\n"
            + RULES.read_text(encoding="utf-8")
        )

    def test_normal_8pm_mode_still_plans_next_day(self):
        self.assertIn("20:00 Asia/Singapore", self.text)
        self.assertIn("next Singapore calendar day", self.text)
        self.assertEqual(DAILY.normal_target_count, 24)
        slots = canonical_normal_slots("2026-09-15")
        self.assertEqual(len(slots), 24)
        self.assertEqual(len(set(slots)), 24)
        parsed, errors = validate_daily_slots(
            DAILY.normal_mode,
            DAILY.normal_target_count,
            slots,
            "2026-09-15",
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(parsed), 24)

    def test_before_8pm_manual_run_is_same_day_catch_up(self):
        self.assertIn("`same_day_catch_up`", self.text)
        self.assertIn("current Singapore calendar day", self.text)
        self.assertIn("30 minutes", self.text)

    def test_catch_up_keeps_only_safe_exact_hourly_slots(self):
        safe_slots = ["2026-09-14T03:00:00Z", "2026-09-14T04:00:00Z"]
        _, errors = validate_daily_slots(
            "same_day_catch_up",
            2,
            safe_slots,
            "2026-09-14",
            now_utc=datetime(2026, 9, 14, 2, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(errors, [])
        _, errors = validate_daily_slots(
            "same_day_catch_up",
            1,
            ["2026-09-14T03:00:00Z"],
            "2026-09-14",
            now_utc=datetime(2026, 9, 14, 2, 45, tzinfo=timezone.utc),
        )
        self.assertTrue(any("30 minutes" in error for error in errors))
        self.assertIn("fail closed", self.text)

    def test_existing_daily_plan_uses_production_recovery_not_replanning(self):
        self.assertIn("daily-production.yml", self.text)
        self.assertIn("canonical `content/planning/YYYY-MM-DD.json` already exists", self.text)
        self.assertIn("recover the existing immutable content IDs", self.text)

    def test_failed_pool_uses_new_immutable_attempt(self):
        self.assertIn("content/planning-pools/daily/YYYY-MM-DD/dp-<attempt-id>.json", self.text)
        self.assertIn("failed immutable attempt is never edited or deleted", self.text.lower())
        self.assertIn("corrected new attempt may be created", self.text.lower())

    def test_catch_up_pool_is_explicit(self):
        self.assertEqual(DAILY.pool_size, 36)
        self.assertIn("`same_day_catch_up`", self.text)
        self.assertIn("target count: exactly the number of valid remaining publication slots", self.text)
        _, errors = validate_daily_slots(
            "same_day_catch_up",
            2,
            ["2026-09-14T03:00:00Z"],
            "2026-09-14",
            now_utc=datetime(2026, 9, 14, 2, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(any("exactly target_count" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
