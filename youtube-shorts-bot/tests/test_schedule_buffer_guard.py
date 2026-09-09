import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from publish import SCHEDULE_FRESHNESS_BUFFER_MINUTES, scheduled_slot_guard


class ScheduledSlotGuardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 10, 0, 0, 0, tzinfo=timezone.utc)

    def request_at(self, when):
        return {
            "publication": {
                "mode": "scheduled",
                "timezone": "Asia/Singapore",
                "publish_at": when.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        }

    def test_policy_is_exactly_ten_minutes(self):
        self.assertEqual(SCHEDULE_FRESHNESS_BUFFER_MINUTES, 10)

    def test_past_slot_is_skipped(self):
        result = scheduled_slot_guard(self.request_at(self.now - timedelta(minutes=1)), now_utc=self.now)
        self.assertTrue(result["skip"])
        self.assertLess(result["remaining_seconds"], 0)

    def test_exactly_ten_minutes_is_skipped(self):
        result = scheduled_slot_guard(self.request_at(self.now + timedelta(minutes=10)), now_utc=self.now)
        self.assertTrue(result["skip"])
        self.assertEqual(result["remaining_seconds"], 600)

    def test_less_than_ten_minutes_is_skipped(self):
        result = scheduled_slot_guard(self.request_at(self.now + timedelta(minutes=9, seconds=59)), now_utc=self.now)
        self.assertTrue(result["skip"])

    def test_more_than_ten_minutes_can_generate(self):
        result = scheduled_slot_guard(self.request_at(self.now + timedelta(minutes=10, seconds=1)), now_utc=self.now)
        self.assertFalse(result["skip"])
        self.assertIsNone(result["reason"])

    def test_unscheduled_ad_hoc_is_not_guarded(self):
        result = scheduled_slot_guard({}, now_utc=self.now)
        self.assertFalse(result["skip"])
        self.assertIsNone(result["remaining_seconds"])


if __name__ == "__main__":
    unittest.main()
