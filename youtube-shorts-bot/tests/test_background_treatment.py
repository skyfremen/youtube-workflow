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
)
from validation.validate_content import validate_request_data
from test_request_schema import valid_request


def asset(asset_id="satisfying-001", *, duration=720.0, category="baking"):
    return {
        "id": asset_id,
        "duration_seconds": duration,
        "retention_category": category,
        "motion_intensity": "high",
        "motion_type": "continuous_process",
        "orientation": "vertical",
        "visual_tags": [category],
    }


def receipt(asset_id, start, duration, *, minutes_ago=0, state="verified_scheduled"):
    now = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    result = {
        "content_id": f"wd-{minutes_ago:04d}",
        "background_asset_id": asset_id,
        "background_treatment": {
            "mode": "fit_to_short",
            "segment_start_seconds": start,
            "segment_duration_seconds": duration,
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
            "satisfying-001", 0, 300,
            state="verified_immediate_public",
        )
        self.assertTrue(is_successful_receipt(record))
        history = derive_treatment_history([record], "satisfying-001")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["mode"], "fit_to_short")
        self.assertEqual(history[0]["segment_duration_seconds"], 300.0)

    def test_long_source_avoids_recent_and_planned_ranges(self):
        source = asset(duration=900.0)
        receipts = [receipt(source["id"], 0, 300, minutes_ago=2)]
        planned = [{
            "asset_id": source["id"],
            "treatment": {
                "mode": "fit_to_short",
                "segment_start_seconds": 300.0,
                "segment_duration_seconds": 300.0,
            },
        }]
        chosen = select_background_treatment(source, receipts, planned)
        self.assertEqual(chosen["mode"], "fit_to_short")
        self.assertEqual(chosen["segment_start_seconds"], 600.0)
        self.assertEqual(chosen["segment_duration_seconds"], 300.0)
        self.assertNotIn("playback_rate", chosen)

    def test_insufficient_or_unknown_duration_fails_closed(self):
        with self.assertRaises(ValueError):
            select_background_treatment(asset(duration=100.0), [], [])
        unknown = asset()
        unknown.pop("duration_seconds")
        with self.assertRaises(ValueError):
            select_background_treatment(unknown, [], [])

    def test_pair_allocator_returns_continuous_ranges_without_rate(self):
        registry = {
            "assets": [
                asset("satisfying-001", duration=720, category="baking"),
                asset("satisfying-002", duration=360, category="pov_movement"),
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
        for treatment in selected.values():
            self.assertEqual(treatment["mode"], "fit_to_short")
            self.assertGreaterEqual(treatment["segment_duration_seconds"], 180.0)
            self.assertNotIn("playback_rate", treatment)


class PrivateTreatmentSchemaTests(unittest.TestCase):
    def test_v5_request_with_frozen_pair_treatments_remains_valid_for_recovery(self):
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

    def test_v6_request_freezes_range_not_rate(self):
        data = copy.deepcopy(valid_request())
        data["schema_version"] = 6
        data["visual"].update({
            "background_primary_treatment": {
                "mode": "fit_to_short",
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": 300.0,
            },
            "background_backup_treatment": {
                "mode": "fit_to_short",
                "segment_start_seconds": 300.0,
                "segment_duration_seconds": 300.0,
            },
        })
        self.assertEqual(validate_request_data(data), [])


if __name__ == "__main__":
    unittest.main()
