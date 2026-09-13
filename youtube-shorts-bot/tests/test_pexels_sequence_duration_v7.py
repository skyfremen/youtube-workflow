import unittest

from media import pexels_registry


class PexelsSequenceDurationV7Tests(unittest.TestCase):
    def metadata(self):
        return {
            "title": "Long satisfying process",
            "visual_tags": ["process", "satisfying"],
            "motion_type": "continuous_process",
            "motion_intensity": "medium",
            "loopability_score": 90,
            "visual_satisfaction_score": 92,
            "caption_readability_score": 91,
            "verified_preview": True,
        }

    def video(self, duration):
        return {
            "id": 12345,
            "width": 1080,
            "height": 1920,
            "duration": duration,
            "url": "https://www.pexels.com/video/sample-12345/",
            "user": {"name": "Creator"},
            "video_files": [{
                "id": 1,
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "file_type": "video/mp4",
                "quality": "hd",
                "link": "https://videos.pexels.com/sample.mp4",
            }],
        }

    def test_typical_90_second_pexels_clip_is_accepted(self):
        asset = pexels_registry._build_asset(
            "satisfying-px-12345", "12345", self.metadata(), self.video(90), "2099-01-01T00:00:00+00:00"
        )
        self.assertEqual(asset["duration_seconds"], 90.0)

    def test_sub_60_second_clip_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "atomic sequence-clip minimum 60s"):
            pexels_registry._build_asset(
                "satisfying-px-12345", "12345", self.metadata(), self.video(59), "2099-01-01T00:00:00+00:00"
            )


if __name__ == "__main__":
    unittest.main()
