import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from validate_media_library import validate_registry_data, validate_request_backgrounds
from test_request_schema import valid_request


def registry():
    def asset(n):
        return {
            "id": f"satisfying-{n:03}",
            "type": "video",
            "title": f"Asset {n}",
            "source": "Pexels",
            "source_page": f"https://www.pexels.com/video/{1000+n}/",
            "direct_url": f"https://www.pexels.com/download/video/{1000+n}/",
            "creator": None,
            "license": "Pexels License",
            "commercial_use": True,
            "attribution_required": False,
            "verified": True,
            "last_verified_at": "2026-09-09T00:00:00+08:00",
            "status": "active",
            "orientation": "unknown",
            "visual_tags": ["satisfying", "motion"],
            "motion_type": "continuous",
            "motion_intensity": "medium",
            "loopability_score": 90,
            "visual_satisfaction_score": 90,
            "caption_readability_score": 90,
            "has_embedded_text": False,
            "has_watermark": False,
        }
    return {"schema_version": 2, "assets": [asset(1), asset(2)]}


class MediaRegistryTests(unittest.TestCase):
    def test_registry_valid(self):
        self.assertEqual(validate_registry_data(registry()), [])

    def test_usage_state_is_forbidden(self):
        data = registry()
        data["assets"][0]["usage_count"] = 1
        self.assertTrue(any("usage history" in x for x in validate_registry_data(data)))

    def test_request_ids_resolve(self):
        primary, backup = validate_request_backgrounds(valid_request(), registry())
        self.assertEqual(primary["id"], "satisfying-001")
        self.assertEqual(backup["id"], "satisfying-002")


if __name__ == "__main__":
    unittest.main()
