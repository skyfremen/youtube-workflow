import unittest

from media.continuous_background import (
    CONCATENATED_FIT_TO_SHORT_MODE,
    derived_sequence_playback_rate,
    sequence_source_duration_eligible,
)
from validation.validate_content import validate_background_sequence


class BackgroundSequenceV7Tests(unittest.TestCase):
    def _sequence(self):
        return [
            {"background_id": "satisfying-px-1", "segment_start_seconds": 0, "segment_duration_seconds": 80},
            {"background_id": "satisfying-px-2", "segment_start_seconds": 4, "segment_duration_seconds": 80},
            {"background_id": "satisfying-px-3", "segment_start_seconds": 2, "segment_duration_seconds": 80},
        ]

    def test_valid_three_clip_sequence(self):
        self.assertEqual(validate_background_sequence(self._sequence()), [])
        self.assertTrue(sequence_source_duration_eligible(240))
        self.assertAlmostEqual(derived_sequence_playback_rate(self._sequence(), 150), 1.6)

    def test_duplicate_clip_fails(self):
        sequence = self._sequence()
        sequence[2]["background_id"] = sequence[0]["background_id"]
        self.assertTrue(any("repeat" in error for error in validate_background_sequence(sequence)))

    def test_insufficient_total_coverage_fails(self):
        sequence = self._sequence()[:2]
        self.assertTrue(any("total source duration" in error for error in validate_background_sequence(sequence)))

    def test_mode_name_is_stable(self):
        self.assertEqual(CONCATENATED_FIT_TO_SHORT_MODE, "concatenated_fit_to_short")


if __name__ == "__main__":
    unittest.main()
