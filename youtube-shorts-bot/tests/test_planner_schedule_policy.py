import unittest
from pathlib import Path


PROMPT = Path("youtube-shorts-bot/planning/DAILY_PLANNER_PROMPT.md")


class PlannerSchedulePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PROMPT.read_text(encoding="utf-8")

    def test_normal_8pm_mode_still_plans_next_day(self):
        self.assertIn("at/after 20:00 Asia/Singapore", self.text)
        self.assertIn("next Singapore calendar day", self.text)
        self.assertIn("`00:00` through `23:00`", self.text)
        self.assertIn("`target_count` is exactly **24**", self.text)

    def test_before_8pm_manual_run_is_same_day_catch_up(self):
        self.assertIn("`same_day_catch_up`", self.text)
        self.assertIn("current Singapore calendar day", self.text)
        self.assertIn("when the canonical timing rules require catch-up", self.text)

    def test_catch_up_keeps_only_safe_exact_hourly_slots(self):
        self.assertIn("top-of-hour slots at least **30 minutes in the future**", self.text)
        self.assertIn("`publication_slots` contains exactly those eligible slots", self.text)
        self.assertIn("If no eligible catch-up slot remains, fail closed", self.text)
        self.assertIn("independently rechecks the 30-minute lead at promotion time", self.text)

    def test_existing_daily_plan_uses_production_recovery_not_replanning(self):
        self.assertIn("daily-production.yml", self.text)
        self.assertIn("manual recovery", self.text)
        self.assertIn("canonical `content/planning/YYYY-MM-DD.json` already exists", self.text)
        self.assertIn("do **not** create another pool", self.text)

    def test_failed_pool_uses_new_immutable_attempt(self):
        self.assertIn("dp-YYYYMMDD-a01", self.text)
        self.assertIn("dp-YYYYMMDD-a02", self.text)
        self.assertIn("new immutable attempt", self.text)
        self.assertIn("Failed candidates are not repaired or re-ranked", self.text)

    def test_catch_up_pool_is_explicit(self):
        self.assertIn("`same_day_catch_up`", self.text)
        self.assertIn("`target_count` equals the number of eligible remaining slots", self.text)
        self.assertIn("ChatGPT still returns exactly **36 ranked candidates**", self.text)


if __name__ == "__main__":
    unittest.main()
