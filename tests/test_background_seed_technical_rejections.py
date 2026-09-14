import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import background_seed as bs
import background_seed_rejections as bsr


def registry_asset(asset_id: str, category: str) -> dict:
    numeric = asset_id.split("-", 1)[1]
    return {
        "id": asset_id,
        "category": category,
        "duration_seconds": 75,
        "source_url": f"https://www.pexels.com/video/example-{numeric}/",
        "download_url": (
            f"https://videos.pexels.com/video-files/{numeric}/"
            f"{numeric}-hd_1080_1920_30fps.mp4"
        ),
    }


def pexels_video(number: int) -> dict:
    return {
        "id": number,
        "duration": 75,
        "url": f"https://www.pexels.com/video/example-{number}/",
        "video_files": [
            {
                "id": number * 10,
                "file_type": "video/mp4",
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "link": (
                    f"https://videos.pexels.com/video-files/{number}/"
                    f"{number}-hd_1080_1920_30fps.mp4"
                ),
            }
        ],
    }


class TechnicalRejectionPersistenceTests(unittest.TestCase):
    def _fixture(self, root: Path):
        registry_path = root / "backgrounds.json"
        rejection_path = root / "background-rejections.json"
        reviews_root = root / "reviews"
        approvals_root = root / "approvals"
        request_path = root / "bgreq-20260915-techreject.json"
        output_dir = root / "output"

        assets = []
        next_id = 1000
        for category in bs.CATEGORIES:
            count = 2 if category == "pov_movement" else 3
            for _ in range(count):
                next_id += 1
                assets.append(registry_asset(f"px-{next_id}", category))

        bs.write_json(registry_path, {"assets": assets})
        bs.write_json(rejection_path, {"rejected_ids": []})
        bs.write_json(
            request_path,
            {"target_per_category": 3, "max_candidates": 48},
        )
        return (
            registry_path,
            rejection_path,
            reviews_root,
            approvals_root,
            request_path,
            output_dir,
        )

    @staticmethod
    def _fake_contact_sheet(video_path, candidate, probe, target):
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        Path(target).write_bytes(b"jpg")

    @staticmethod
    def _fake_index(candidate_dir, target, count):
        if count:
            Path(target).write_bytes(b"index")

    def test_only_deterministic_physical_failures_are_permanent(self):
        self.assertTrue(
            bsr.is_permanent_technical_rejection(
                bs.SeedError(
                    "actual downloaded duration is shorter than 60 seconds"
                )
            )
        )
        self.assertTrue(
            bsr.is_permanent_technical_rejection(
                bs.SeedError(
                    "actual downloaded dimensions differ from selected rendition metadata"
                )
            )
        )
        self.assertFalse(
            bsr.is_permanent_technical_rejection(
                bs.SeedError("download failed after 3 attempts: timeout")
            )
        )
        self.assertFalse(
            bsr.is_permanent_technical_rejection(
                bs.SeedError("failed to extract review frame")
            )
        )

    def test_permanent_failure_is_persisted_and_backfilled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (
                registry_path,
                rejection_path,
                reviews_root,
                approvals_root,
                request_path,
                output_dir,
            ) = self._fixture(root)

            def search_fn(query, api_key, per_page, page):
                if query != "pov walking":
                    return []
                if page == 1:
                    return [pexels_video(901)]
                if page == 2:
                    return [pexels_video(902)]
                return []

            probe = {
                "width": 1080,
                "height": 1920,
                "fps": 30.0,
                "duration_seconds": 75.0,
            }
            with (
                patch.object(bs, "validate_media_tools"),
                patch.object(bs, "download_file"),
                patch.object(
                    bs,
                    "validate_physical",
                    side_effect=[
                        bs.SeedError(
                            "actual downloaded dimensions differ from selected rendition metadata"
                        ),
                        probe,
                    ],
                ),
                patch.object(
                    bs,
                    "make_contact_sheet",
                    side_effect=self._fake_contact_sheet,
                ),
                patch.object(bs, "make_index", side_effect=self._fake_index),
            ):
                manifest_path = bsr.discover_with_rejections(
                    request_path,
                    "secret",
                    output_dir,
                    registry_path,
                    reviews_root,
                    rejection_path,
                    approvals_root,
                    search_fn=search_fn,
                )

            self.assertEqual(
                bs.read_json(rejection_path),
                {"rejected_ids": ["px-901"]},
            )
            self.assertEqual(
                [item["id"] for item in bs.read_json(manifest_path)["candidates"]],
                ["px-902"],
            )

    def test_transient_failure_is_not_persisted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (
                registry_path,
                rejection_path,
                reviews_root,
                approvals_root,
                request_path,
                output_dir,
            ) = self._fixture(root)

            def search_fn(query, api_key, per_page, page):
                if query != "pov walking":
                    return []
                if page == 1:
                    return [pexels_video(911)]
                if page == 2:
                    return [pexels_video(912)]
                return []

            probe = {
                "width": 1080,
                "height": 1920,
                "fps": 30.0,
                "duration_seconds": 75.0,
            }
            with (
                patch.object(bs, "validate_media_tools"),
                patch.object(
                    bs,
                    "download_file",
                    side_effect=[
                        bs.SeedError("download failed after 3 attempts: timeout"),
                        None,
                    ],
                ),
                patch.object(bs, "validate_physical", return_value=probe),
                patch.object(
                    bs,
                    "make_contact_sheet",
                    side_effect=self._fake_contact_sheet,
                ),
                patch.object(bs, "make_index", side_effect=self._fake_index),
            ):
                bsr.discover_with_rejections(
                    request_path,
                    "secret",
                    output_dir,
                    registry_path,
                    reviews_root,
                    rejection_path,
                    approvals_root,
                    search_fn=search_fn,
                )

            self.assertEqual(
                bs.read_json(rejection_path),
                {"rejected_ids": []},
            )


if __name__ == "__main__":
    unittest.main()
