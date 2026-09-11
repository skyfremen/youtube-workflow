import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from media.background_policy import (
    MAX_SOURCE_PIXELS,
    MAX_CROP_FILL_UPSCALE,
    crop_fill_geometry,
    production_rendition_policy,
    rendition_is_production_suitable,
    rendition_sort_key,
)


def rendition(name, width, height, fps=30, size=None):
    value = {
        "id": name, "width": width, "height": height, "fps": fps,
        "file_type": "video/mp4", "direct_url": f"https://example.test/{name}.mp4",
    }
    if size:
        value["file_size_bytes"] = size
    return value


class BackgroundPolicyTests(unittest.TestCase):
    def test_native_vertical_and_high_resolution_vertical_are_suitable(self):
        self.assertTrue(rendition_is_production_suitable(rendition("native", 1080, 1920)))
        self.assertTrue(rendition_is_production_suitable(rendition("large", 2160, 3840)))
        self.assertFalse(rendition_is_production_suitable(rendition("weak", 540, 960)))

    def test_landscape_is_measured_after_vertical_crop(self):
        hd = crop_fill_geometry(1920, 1080)
        self.assertAlmostEqual(hd["effective_crop_width"], 607.5, places=1)
        self.assertFalse(rendition_is_production_suitable(rendition("hd", 1920, 1080)))
        uhd = crop_fill_geometry(3840, 2160)
        self.assertAlmostEqual(uhd["effective_crop_width"], 1215.0, places=1)
        self.assertTrue(rendition_is_production_suitable(rendition("uhd", 3840, 2160)))

    def test_smallest_sufficient_native_vertical_ranks_first(self):
        native = rendition("native", 1080, 1920, 30, 4_000_000)
        larger = rendition("larger", 2160, 3840, 30, 12_000_000)
        self.assertLess(rendition_sort_key(native), rendition_sort_key(larger))

    def test_policy_allows_uhd_only_when_post_crop_quality_requires_it(self):
        policy = production_rendition_policy()
        self.assertTrue(policy["uhd_downloads_allowed_when_required_after_crop"])
        self.assertEqual(policy["target_width"], 1080)
        self.assertEqual(policy["target_height"], 1920)
        self.assertEqual(policy["max_source_pixels"], 3840 * 2160)
        self.assertEqual(policy["max_crop_fill_upscale"], MAX_CROP_FILL_UPSCALE)


if __name__ == "__main__":
    unittest.main()
