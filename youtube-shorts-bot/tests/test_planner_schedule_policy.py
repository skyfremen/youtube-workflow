import unittest
from pathlib import Path


PROMPT = Path("youtube-shorts-bot/planner/DAILY_GROWTH_PROMPT.md")


class PlannerSchedulePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PROMPT.read_text(encoding="utf-8")

    def test_normal_8pm_mode_still_plans_next_day(self):
        self.assertIn("runs at **20:00 Asia/Singapore**", self.text)
        self.assertIn("plan the **next Singapore calendar day**", self.text)
        self.assertIn("`00:00` through `23:00`", self.text)

    def test_before_8pm_manual_run_is_same_day_catch_up(self):
        self.assertIn("before 20:00 Asia/Singapore", self.text)
        self.assertIn("same-day catch-up", self.text)
        self.assertIn("**current Singapore calendar day**", self.text)

    def test_catch_up_keeps_only_safe_exact_hourly_slots(self):
        self.assertIn("at least **30 minutes in the future**", self.text)
        self.assertIn("Never recreate, backfill, or shift elapsed/too-close hours", self.text)
        self.assertIn("At `01:35`, `02:00` is too close", self.text)
        self.assertIn("first eligible slot is `03:00`", self.text)

    def test_existing_daily_plan_uses_production_recovery_not_replanning(self):
        self.assertIn("daily-growth-batch.yml", self.text)
        self.assertIn("manual `workflow_dispatch`", self.text)
        self.assertIn("do **not** create a second plan", self.text)

    def test_catch_up_audit_is_explicit(self):
        self.assertIn("`same_day_catch_up`", self.text)
        self.assertIn("omitted elapsed/too-close slots", self.text)


if __name__ == "__main__":
    unittest.main()
