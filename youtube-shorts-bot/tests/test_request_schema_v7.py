import copy
import unittest

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


if __name__ == "__main__":
    unittest.main()
