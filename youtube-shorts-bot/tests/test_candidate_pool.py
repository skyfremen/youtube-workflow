import unittest
from datetime import datetime, timedelta, timezone

from media.validate_media_library import load_registry
from planning.candidate_pool import (
    CandidatePoolError,
    _parse_daily_slots,
    _validate_candidate_envelopes,
)
from planning.planning_config import (
    ADHOC_RANKED_POOL_COUNT,
    DAILY_PUBLISH_COUNT,
    DAILY_RANKED_POOL_COUNT,
)
from validation.validate_content import _strict_background_errors


class CandidatePoolTests(unittest.TestCase):
    def candidates(self, count):
        return [
            {
                "rank": index,
                "candidate_id": f"candidate-{index:03d}",
                "request": {"content_id": f"wd-20990101-story-{index:03d}"},
            }
            for index in range(1, count + 1)
        ]

    def test_canonical_pool_sizes_are_36_daily_and_5_adhoc(self):
        self.assertEqual(DAILY_RANKED_POOL_COUNT, 36)
        self.assertEqual(DAILY_PUBLISH_COUNT, 24)
        self.assertEqual(ADHOC_RANKED_POOL_COUNT, 5)

    def test_ranked_envelopes_require_contiguous_frozen_order(self):
        daily = self.candidates(DAILY_RANKED_POOL_COUNT)
        ids, content_ids = _validate_candidate_envelopes(
            daily, DAILY_RANKED_POOL_COUNT
        )
        self.assertEqual(len(ids), 36)
        self.assertEqual(len(content_ids), 36)

        daily[10]["rank"] = 99
        with self.assertRaises(CandidatePoolError):
            _validate_candidate_envelopes(daily, DAILY_RANKED_POOL_COUNT)

    def test_ranked_envelopes_reject_duplicate_content_ids(self):
        candidates = self.candidates(ADHOC_RANKED_POOL_COUNT)
        candidates[1]["request"]["content_id"] = candidates[0]["request"]["content_id"]
        with self.assertRaises(CandidatePoolError):
            _validate_candidate_envelopes(candidates, ADHOC_RANKED_POOL_COUNT)

    def test_normal_daily_slots_are_exact_24_singapore_hours(self):
        plan_date = "2099-01-02"
        singapore_midnight_utc = datetime(2099, 1, 1, 16, 0, tzinfo=timezone.utc)
        slots = [
            (singapore_midnight_utc + timedelta(hours=hour)).strftime("%Y-%m-%dT%H:%M:%SZ")
            for hour in range(24)
        ]
        resolved = _parse_daily_slots(
            plan_date, "normal_next_day", slots, DAILY_PUBLISH_COUNT
        )
        self.assertEqual(resolved, slots)

    def test_strict_background_contract_accepts_safe_assets_and_rejects_overrun(self):
        registry = load_registry()
        request = {
            "schema_version": 5,
            "visual": {
                "background_primary_id": "satisfying-001",
                "background_backup_id": "satisfying-002",
                "background_primary_treatment": {
                    "segment_start_seconds": 0.0,
                    "segment_duration_seconds": 12.0,
                    "playback_rate": 1.25,
                },
                "background_backup_treatment": {
                    "segment_start_seconds": 0.0,
                    "segment_duration_seconds": 12.0,
                    "playback_rate": 1.25,
                },
            },
        }
        self.assertEqual(_strict_background_errors(request, registry), [])

        request["visual"]["background_primary_treatment"].update(
            segment_start_seconds=10.0,
            segment_duration_seconds=12.0,
        )
        errors = _strict_background_errors(request, registry)
        self.assertTrue(any("exceeds background duration" in error for error in errors))

    def test_strict_background_contract_rejects_unknown_asset(self):
        registry = load_registry()
        request = {
            "schema_version": 5,
            "visual": {
                "background_primary_id": "missing-background",
                "background_backup_id": "satisfying-002",
                "background_primary_treatment": {
                    "segment_start_seconds": 0.0,
                    "segment_duration_seconds": None,
                    "playback_rate": 1.0,
                },
                "background_backup_treatment": {
                    "segment_start_seconds": 0.0,
                    "segment_duration_seconds": 12.0,
                    "playback_rate": 1.25,
                },
            },
        }
        errors = _strict_background_errors(request, registry)
        self.assertTrue(any("unknown registered background" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
