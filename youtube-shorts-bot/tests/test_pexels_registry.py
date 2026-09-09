import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import pexels_registry


class PexelsRegistryTests(unittest.TestCase):
    def video(self):
        return {
            "id": 424242, "width": 1080, "height": 1920, "duration": 12,
            "url": "https://www.pexels.com/video/sample-424242/",
            "user": {"name": "Creator"},
            "video_files": [
                {"id": 11, "width": 540, "height": 960, "fps": 30,
                 "file_type": "video/mp4", "quality": "sd", "link": "https://videos.pexels.com/sd.mp4"},
                {"id": 12, "width": 1080, "height": 1920, "fps": 30,
                 "file_type": "video/mp4", "quality": "hd", "link": "https://videos.pexels.com/hd.mp4"},
            ],
        }

    def metadata(self):
        return {
            "title": "Satisfying fluid loop", "visual_tags": ["fluid", "loop"],
            "motion_type": "loop", "motion_intensity": "medium",
            "loopability_score": 95, "visual_satisfaction_score": 94,
            "caption_readability_score": 92, "verified_preview": True,
        }

    def test_api_renditions_are_normalized(self):
        items = pexels_registry.renditions_from_video(self.video())
        self.assertEqual([item["id"] for item in items], ["11", "12"])
        self.assertEqual(items[1]["direct_url"], "https://videos.pexels.com/hd.mp4")

    def test_registration_requires_visual_verification(self):
        metadata = self.metadata()
        metadata["verified_preview"] = False
        with self.assertRaises(ValueError):
            pexels_registry.register_video("424242", metadata, "/unused")

    def test_registration_assigns_next_stable_id_and_renditions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backgrounds.json"
            path.write_text(json.dumps({
                "schema_version": 3,
                "assets": [{"id": "satisfying-030", "source": "Other", "source_page": "https://example.com"}],
            }), encoding="utf-8")
            with mock.patch.object(pexels_registry, "api_get", return_value=self.video()):
                added = pexels_registry.register_video("424242", self.metadata(), path)
            stored = json.loads(path.read_text())
            self.assertEqual(added["id"], "satisfying-031")
            self.assertEqual(stored["assets"][-1]["provider_asset_id"], "424242")
            self.assertEqual(len(stored["assets"][-1]["renditions"]), 2)


if __name__ == "__main__":
    unittest.main()
