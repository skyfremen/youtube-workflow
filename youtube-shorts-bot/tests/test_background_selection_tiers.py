import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from media.background_selector import select_logical_backgrounds


def item(n, *, category, tags, quality, intensity, motion_type):
    return {
        "id": f"satisfying-tier-{n}",
        "status": "active",
        "verified": True,
        "title": "Background",
        "visual_tags": list(tags),
        "motion_type": motion_type,
        "motion_intensity": intensity,
        "orientation": "vertical",
        "loopability_score": quality,
        "visual_satisfaction_score": quality,
        "caption_readability_score": quality,
        "source": "Pexels",
        "source_page": f"https://www.pexels.com/video/{9000+n}/",
        "license": "Pexels License",
        "commercial_use": True,
        "retention_category": category,
        "renditions": [{
            "id": f"r{n}",
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "file_type": "video/mp4",
            "direct_url": f"https://videos.pexels.com/{n}.mp4",
        }],
    }


class BackgroundSelectionTierTests(unittest.TestCase):
    def test_legacy_category_rotation_cannot_displace_valid_retention_backup(self):
        primary = item(
            1,
            category="baking",
            tags=("baking",),
            quality=95,
            intensity="high",
            motion_type="continuous_process",
        )
        retention_backup = item(
            2,
            category="baking",
            tags=("baking",),
            quality=92,
            intensity="high",
            motion_type="continuous_process",
        )
        legacy_other_category = item(
            3,
            category="generic",
            tags=("relationship", "argument"),
            quality=99,
            intensity="low",
            motion_type="ambient",
        )
        decision = select_logical_backgrounds(
            {"assets": [primary, retention_backup, legacy_other_category]},
            {"visual_tags": ["relationship", "argument"]},
            [],
        )
        self.assertFalse(decision["expansion_required"])
        self.assertFalse(decision["used_legacy_topic_fallback"])
        self.assertEqual(
            {decision["primary"], decision["backup"]},
            {primary["id"], retention_backup["id"]},
        )


if __name__ == "__main__":
    unittest.main()
