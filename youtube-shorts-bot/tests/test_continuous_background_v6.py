import unittest

from media.continuous_background import FIT_TO_SHORT_MODE, derived_playback_rate, preferred_range_duration
from media.media_readiness import audit_registry
from media.validate_media_library import validate_registry_data
from validation.validate_content import validate_background_treatment


class ContinuousBackgroundContractTests(unittest.TestCase):
    def test_empty_registry_is_valid_and_replenishes(self):
        registry = {"schema_version": 3, "assets": []}
        self.assertEqual(validate_registry_data(registry), [])
        report = audit_registry(registry)
        self.assertEqual(report["status"], "REPLENISH")
        self.assertEqual(report["selectable_assets"], 0)

    def test_fit_math(self):
        self.assertAlmostEqual(derived_playback_rate(300, 150), 2.0)
        self.assertAlmostEqual(derived_playback_rate(240, 160), 1.5)

    def test_too_short_fit_fails(self):
        with self.assertRaises(ValueError):
            derived_playback_rate(100, 160)

    def test_preferred_range_caps_long_source(self):
        self.assertEqual(preferred_range_duration({"duration_seconds": 720}), 300.0)

    def test_v6_treatment_has_no_frozen_playback_rate(self):
        treatment = {"mode": FIT_TO_SHORT_MODE, "segment_start_seconds": 10.0, "segment_duration_seconds": 300.0}
        self.assertEqual(validate_background_treatment(treatment), [])
        bad = dict(treatment, playback_rate=2.0)
        self.assertTrue(validate_background_treatment(bad))


if __name__ == "__main__":
    unittest.main()
