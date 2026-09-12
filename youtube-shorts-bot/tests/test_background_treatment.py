import copy
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from media.background_selector import is_successful_receipt
from media.background_treatment import (
    derive_treatment_history,
    select_background_treatment,
    select_pair_treatments,
    speed_range,
)
from validation.validate_content import validate_request_data
from test_request_schema import valid_request


def asset(asset_id="satisfying-001", *, duration=42.0, category="baking"):
    item = {
        "id": asset_id,
        "retention_category": category,
        "motion_intensity": "high",
        "motion_type": "continuous_process",
        "orientation": "vertical",
        "visual_tags": [category],
    }
    if duration is not None:
        item["duration_seconds"] = duration
    return item


def receipt(asset_id, start, duration, rate, *, minutes_ago=0, state="verified_scheduled"):
    now = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    result = {
        "content_id": f"wd-{minutes_ago:04d}",
        "background_asset_id": asset_id,
        "background_treatment": {
            "segment_start_seconds": start,
            "segment_duration_seconds": duration,
            "playback_rate": rate,
        },
        "receipt_created_at": now.isoformat(),
        "verification": {"passed": True},
        "verification_state": state,
        "privacy_status": "private",
        "publication_mode": "scheduled",
        "publish_at": "2099-01-01T00:00:00Z",
    }
    if state == "verified_immediate_public":
        result.update({
            "privacy_status": "public",
            "publication_mode": "immediate",
            "publish_at": None,
            "publish_at_absent": True,
        })
    return result


class PrivateTreatmentHistoryTests(unittest.TestCase):
    def test_immediate_public_adhoc_receipt_counts_as_success(self):
        record = receipt(
            "satisfying-001", 0, 12, 1.4,
            state="verified_immediate_public",
        )
        self.assertTrue(is_successful_receipt(record))
        history = derive_treatment_history([record], "satisfying-001")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["treatment"]["playback_rate"], 1.4)

    def test_long_source_avoids_recent_and_planned_segments(self):
        source = asset(duration=42.0)
        receipts = [receipt(source["id"], 0, 12, 1.2, minutes_ago=2)]
        planned = [{
            "asset_id": source["id"],
            "treatment": {
                "segment_start_seconds": 12.0,
                "segment_duration_seconds": 12.0,
                "playback_rate": 1.35,
            },
        }]
        chosen = select_background_treatment(source, receipts, planned)
        self.assertEqual(chosen["segment_start_seconds"], 24.0)
        self.assertEqual(chosen["segment_duration_seconds"], 12.0)

    def test_unknown_duration_stays_full_source_and_backward_compatible(self):
        chosen = select_background_treatment(asset(duration=None), [], [])
        self.assertEqual(chosen["segment_start_seconds"], 0.0)
        self.assertIsNone(chosen["segment_duration_seconds"])
        self.assertGreaterEqual(chosen["playback_rate"], 1.0)
        self.assertLessEqual(chosen["playback_rate"], 2.0)

    def test_speed_ranges_are_category_aware_and_bounded(self):
        minimum, maximum = speed_range(asset(category="cleaning"))
        self.assertEqual((minimum, maximum), (1.3, 1.8))
        source = asset(category="cleaning")
        source["recommended_speed_min"] = 0.5
        source["recommended_speed_max"] = 3.0
        self.assertEqual(speed_range(source), (1.0, 2.0))

    def test_pair_allocator_returns_frozen_primary_and_backup_treatments(self):
        registry = {
            "assets": [
                asset("satisfying-001", duration=42, category="baking"),
                asset("satisfying-002", duration=30, category="pov_movement"),
            ]
        }
        selected = select_pair_treatments(
            registry,
            "satisfying-001",
            "satisfying-002",
            [],
        )
        self.assertEqual(
            set(selected),
            {"background_primary_treatment", "background_backup_treatment"},
        )
        self.assertGreaterEqual(
            selected["background_primary_treatment"]["playback_rate"], 1.2
        )
        self.assertLessEqual(
            selected["background_backup_treatment"]["playback_rate"], 1.35
        )


class PrivateTreatmentSchemaTests(unittest.TestCase):
    def test_v5_request_with_frozen_pair_treatments_is_valid(self):
        data = copy.deepcopy(valid_request())
        data["schema_version"] = 5
        data["visual"].update({
            "background_primary_treatment": {
                "segment_start_seconds": 2.0,
                "segment_duration_seconds": 12.0,
                "playback_rate": 1.4,
            },
            "background_backup_treatment": {
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": None,
                "playback_rate": 1.2,
            },
        })
        self.assertEqual(validate_request_data(data), [])

    def test_v4_request_remains_valid_during_staged_rollout(self):
        self.assertEqual(validate_request_data(valid_request()), [])


if __name__ == "__main__":
    unittest.main()
