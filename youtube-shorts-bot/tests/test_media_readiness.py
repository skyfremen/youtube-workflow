import unittest

from media.media_readiness import (
    MIN_SELECTABLE_ASSETS,
    REQUIRED_CATEGORY_MINIMUMS,
    audit_registry,
    is_selectable,
)
from validation.validate_content import _validate_registry_asset


def asset(asset_id, category, *, selection_enabled=True):
    return {
        "id": asset_id,
        "status": "active",
        "verified": True,
        "commercial_use": True,
        "has_watermark": False,
        "has_embedded_text": False,
        "selection_enabled": selection_enabled,
        "retention_category": category,
        "orientation": "vertical",
        "motion_intensity": "high",
        "motion_type": "continuous-process",
        "visual_satisfaction_score": 100,
        "loopability_score": 100,
        "caption_readability_score": 100,
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
    def test_retired_asset_is_not_selectable(self):
        self.assertFalse(is_selectable(asset("old", "cooking", selection_enabled=False)))

    def test_new_production_rejects_retired_but_recovery_can_resolve_it(self):
        retired = asset("old", "cooking", selection_enabled=False)
        new_errors = _validate_registry_asset(
            retired, "old", "visual.background_primary_id", allow_retired=False
        )
        recovery_errors = _validate_registry_asset(
            retired, "old", "visual.background_primary_id", allow_retired=True
        )
        self.assertTrue(any("retired from new production" in item for item in new_errors))
        self.assertEqual(recovery_errors, [])

    def test_empty_selectable_pool_requires_replenishment(self):
        report = audit_registry({"assets": [asset("old", "cooking", selection_enabled=False)]})
        self.assertEqual(report["status"], "REPLENISH")
        self.assertEqual(report["selectable_assets"], 0)
        self.assertEqual(report["retired_from_selection"], 1)
        self.assertGreaterEqual(report["required_new_assets_at_least"], MIN_SELECTABLE_ASSETS)

    def test_diverse_pool_passes(self):
        assets = []
        counter = 0
        for category, minimum in REQUIRED_CATEGORY_MINIMUMS.items():
            for _ in range(minimum):
                counter += 1
                assets.append(asset(f"a-{counter}", category))
        while len(assets) < MIN_SELECTABLE_ASSETS:
            counter += 1
            assets.append(asset(f"a-{counter}", "satisfying_process"))
        report = audit_registry({"assets": assets})
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["ready"])
        self.assertEqual(report["selectable_assets"], len(assets))
        self.assertFalse(any(report["category_deficits"].values()))


if __name__ == "__main__":
    unittest.main()
