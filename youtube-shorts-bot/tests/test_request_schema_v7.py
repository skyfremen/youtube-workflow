import copy
import json
import tempfile
import unittest
from pathlib import Path

from tests.test_request_schema import valid_request
from validation.validate_content import validate_request_data


def valid_v7_request():
    data = copy.deepcopy(valid_request())
    data["schema_version"] = 7
    data["visual"] = {
        "background_mode": "concatenated_fit_to_short",
        "background_primary_sequence": [
            {"background_id": "satisfying-001", "segment_start_seconds": 0, "segment_duration_seconds": 80},
            {"background_id": "satisfying-002", "segment_start_seconds": 5, "segment_duration_seconds": 80},
            {"background_id": "satisfying-003", "segment_start_seconds": 10, "segment_duration_seconds": 80},
        ],
        "background_backup_sequence": [
            {"background_id": "satisfying-004", "segment_start_seconds": 0, "segment_duration_seconds": 80},
            {"background_id": "satisfying-005", "segment_start_seconds": 5, "segment_duration_seconds": 80},
            {"background_id": "satisfying-006", "segment_start_seconds": 10, "segment_duration_seconds": 80},
        ],
    }
    return data


def selected_only_registry():
    assets = []
    for index in range(1, 7):
        asset_id = f"satisfying-{index:03d}"
        assets.append(
            {
                "id": asset_id,
                "status": "active",
                "verified": True,
                "commercial_use": True,
                "has_watermark": False,
                "has_embedded_text": False,
                "retention_category": "satisfying_process",
                "orientation": "vertical",
                "motion_type": "continuous-process",
                "motion_intensity": "high",
                "visual_satisfaction_score": 100,
                "loopability_score": 100,
                "caption_readability_score": 100,
                "duration_seconds": 120.0,
                "renditions": [
                    {
                        "id": f"test-v7-r-{index:03d}",
                        "width": 1080,
                        "height": 1920,
                        "fps": 30.0,
                        "file_type": "video/mp4",
                        "direct_url": f"https://videos.pexels.com/test-v7-{index:03d}.mp4",
                    }
                ],
            }
        )
    return {"schema_version": 3, "assets": assets}


class RequestSchemaV7Tests(unittest.TestCase):
    def test_valid_sequence_request_passes_schema_validation(self):
        self.assertEqual(validate_request_data(valid_v7_request()), [])

    def test_sequences_must_be_disjoint(self):
        data = valid_v7_request()
        data["visual"]["background_backup_sequence"][0]["background_id"] = "satisfying-001"
        self.assertTrue(any("disjoint" in error for error in validate_request_data(data)))

    def test_sequence_total_must_cover_short_without_looping(self):
        data = valid_v7_request()
        for segment in data["visual"]["background_primary_sequence"]:
            segment["segment_duration_seconds"] = 60
        self.assertTrue(any("total source duration" in error for error in validate_request_data(data)))

    def test_new_v7_request_still_requires_shared_media_readiness(self):
        errors = validate_request_data(
            valid_v7_request(),
            enforce_registry=True,
            registry=selected_only_registry(),
        )
        self.assertTrue(
            any("media readiness requires automatic replenishment" in error for error in errors)
        )
        self.assertFalse(any("references unknown background" in error for error in errors))

    def test_existing_immutable_v7_request_ignores_unrelated_inventory_shortage(self):
        data = valid_v7_request()
        registry = selected_only_registry()
        with tempfile.TemporaryDirectory() as temporary:
            request_path = Path(temporary) / f"{data['content_id']}.json"
            request_path.write_text(json.dumps(data), encoding="utf-8")
            errors = validate_request_data(
                data,
                request_path=request_path,
                enforce_registry=True,
                registry=registry,
            )
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
