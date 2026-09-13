import unittest

from media.media_readiness import (
    MIN_SELECTABLE_ASSETS,
    REQUIRED_CATEGORY_MINIMUMS,
    audit_registry,
    is_selectable,
)
from media.validate_media_library import validate_registry_data


def asset(asset_id, category, *, duration=300.0):
    return {
        "id": asset_id,
        "status": "active",
        "verified": True,
        "commercial_use": True,
        "has_watermark": False,
        "has_embedded_text": False,
        "retention_category": category,
        "orientation": "vertical",
        "motion_intensity": "high",
        "motion_type": "continuous-process",
        "visual_satisfaction_score": 100,
        "loopability_score": 100,
        "caption_readability_score": 100,
        "duration_seconds": duration,
        "renditions": [
            {
                "id": f"r-{asset_id}",
                "width": 1080,
                "height": 1920,
                "fps": 30.0,
                "file_type": "video/mp4",
                "direct_url": "https://videos.pexels.com/example.mp4",
            }
        ],
    }


class MediaReadinessTests(unittest.TestCase):
    def test_empty_active_registry_is_valid_replenish_state(self):
        registry = {"schema_version": 3, "assets": []}
        self.assertEqual(validate_registry_data(registry), [])
        report = audit_registry(registry)
        self.assertEqual(report["status"], "REPLENISH")
        self.assertEqual(report["selectable_assets"], 0)
        self.assertGreaterEqual(report["required_new_assets_at_least"], MIN_SELECTABLE_ASSETS)
        self.assertTrue(report["automatic_continuation_required"])

    def test_obsolete_soft_retirement_state_is_not_valid_active_registry(self):
        old = asset("old", "cooking")
        old["selection_enabled"] = False
        errors = validate_registry_data({"schema_version": 3, "assets": [old]})
        self.assertTrue(any("selection_enabled" in item for item in errors))

    def test_short_asset_is_not_selectable(self):
        self.assertFalse(is_selectable(asset("short", "cooking", duration=30.0)))
        report = audit_registry({"schema_version": 3, "assets": [asset("short", "cooking", duration=30.0)]})
        self.assertEqual(report["status"], "REPLENISH")
        self.assertEqual(report["duration_ineligible_assets"], 1)

    def test_diverse_long_form_pool_passes(self):
        assets = []
        counter = 0
        for category, minimum in REQUIRED_CATEGORY_MINIMUMS.items():
            for _ in range(minimum):
                counter += 1
                assets.append(asset(f"a-{counter}", category))
        while len(assets) < MIN_SELECTABLE_ASSETS:
            counter += 1
            assets.append(asset(f"a-{counter}", "satisfying_process"))
        report = audit_registry({"schema_version": 3, "assets": assets})
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["ready"])
        self.assertEqual(report["selectable_assets"], len(assets))
        self.assertFalse(any(report["category_deficits"].values()))


if __name__ == "__main__":
    unittest.main()
