import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from background_policy import (
    MAX_SOURCE_PIXELS,
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
    def test_exact_portrait_and_standard_1080_sources_are_suitable(self):
        self.assertTrue(rendition_is_production_suitable(rendition("exact", 720, 1280)))
        self.assertTrue(rendition_is_production_suitable(rendition("portrait", 1080, 1920)))
        self.assertTrue(rendition_is_production_suitable(rendition("landscape", 1920, 1080)))

    def test_720p_landscape_is_too_small_for_bounded_portrait_crop(self):
        geometry = crop_fill_geometry(1280, 720)
        self.assertGreater(geometry["scale_factor"], 1.25)
        self.assertFalse(rendition_is_production_suitable(rendition("hd", 1280, 720)))

    def test_qhd_and_4k_are_rejected_even_though_they_are_large_enough(self):
        for width, height in ((2560, 1440), (3840, 2160), (2160, 3840)):
            self.assertGreater(width * height, MAX_SOURCE_PIXELS)
            self.assertFalse(rendition_is_production_suitable(rendition("uhd", width, height)))

    def test_exact_target_ranks_before_larger_sufficient_source(self):
        exact = rendition("exact", 720, 1280, 30, 4_000_000)
        larger = rendition("larger", 1080, 1920, 30, 3_000_000)
        self.assertLess(rendition_sort_key(exact), rendition_sort_key(larger))

    def test_policy_explicitly_forbids_uhd_downloads(self):
        policy = production_rendition_policy()
        self.assertFalse(policy["uhd_downloads_allowed"])
        self.assertEqual(policy["target_width"], 720)
        self.assertEqual(policy["target_height"], 1280)
        self.assertEqual(policy["max_source_pixels"], 1920 * 1080)


if __name__ == "__main__":
    unittest.main()
