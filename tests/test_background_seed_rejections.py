import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import background_seed as bs
import background_seed_rejections as bsr


SOURCE = "https://www.pexels.com/video/example-123/"
MEDIA = "https://videos.pexels.com/video-files/123/123-hd_1080_1920_30fps.mp4"


def review_candidate(asset_id: str, category: str = "food_process") -> dict:
    return {
        "id": asset_id,
        "category": category,
        "duration_seconds": 75,
        "source_url": SOURCE,
        "download_url": MEDIA,
        "width": 1080,
        "height": 1920,
        "fps": 30.0,
    }


def registry_asset(asset_id: str, category: str) -> dict:
    numeric = asset_id.split("-", 1)[1]
    return {
        "id": asset_id,
        "category": category,
        "duration_seconds": 75,
        "source_url": f"https://www.pexels.com/video/example-{numeric}/",
        "download_url": f"https://videos.pexels.com/video-files/{numeric}/{numeric}-hd_1080_1920_30fps.mp4",
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
                "link": f"https://videos.pexels.com/video-files/{number}/{number}-hd_1080_1920_30fps.mp4",
            }
        ],
    }


class RejectionValidationTests(unittest.TestCase):
    def test_rejection_registry_accepts_valid_ids(self):
        data = {"rejected_ids": ["px-1", "px-2"]}
        self.assertEqual(bsr.validate_rejections(data), data)

    def test_rejection_registry_rejects_duplicate_ids(self):
        with self.assertRaises(bs.SeedError):
            bsr.validate_rejections({"rejected_ids": ["px-1", "px-1"]})

    def test_rejection_registry_rejects_invalid_id(self):
        with self.assertRaises(bs.SeedError):
            bsr.validate_rejections({"rejected_ids": ["bad-id"]})

    def test_approved_and_rejected_overlap_is_rejected(self):
        registry = {"assets": [{
            "id": "px-1",
            "category": "pov_movement",
            "duration_seconds": 75,
            "source_url": SOURCE,
            "download_url": MEDIA,
        }]}
        with self.assertRaises(bs.SeedError):
            bsr.validate_rejections({"rejected_ids": ["px-1"]}, registry)


class DiscoveryExclusionTests(unittest.TestCase):
    def test_permanent_rejections_are_added_to_discovery_exclusions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rejection_path = root / "background-rejections.json"
            bs.write_json(rejection_path, {"rejected_ids": ["px-99"]})

            def pending_fn(reviews_root, approvals_root):
                return {"px-77"}

            excluded = bsr.excluded_review_ids(
                root / "reviews",
                root / "approvals",
                rejection_path,
                pending_fn=pending_fn,
            )
            self.assertEqual(excluded, {"px-77", "px-99"})


class DiscoveryBackfillTests(unittest.TestCase):
    def _fixture(self, root: Path, max_candidates: int = 48):
        registry_path = root / "backgrounds.json"
        rejection_path = root / "background-rejections.json"
        reviews_root = root / "reviews"
        approvals_root = root / "approvals"
        request_path = root / "bgreq-20260915-backfill.json"
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
            {"target_per_category": 3, "max_candidates": max_candidates},
        )
        return registry_path, rejection_path, reviews_root, approvals_root, request_path, output_dir

    @staticmethod
    def _fake_download(url, target):
        Path(target).write_bytes(b"x" * 10000)

    @staticmethod
    def _fake_contact_sheet(video_path, candidate, probe, target):
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        Path(target).write_bytes(b"jpg")

    @staticmethod
    def _fake_index(candidate_dir, target, count):
        if count:
            Path(target).write_bytes(b"index")

    def test_discovery_backfills_after_technical_failure_and_uses_next_page(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry_path, rejection_path, reviews_root, approvals_root, request_path, output_dir = self._fixture(root)
            pages = []

            def search_fn(query, api_key, per_page, page):
                if query != "pov walking":
                    return []
                pages.append(page)
                if page == 1:
                    return [pexels_video(101)]
                if page == 2:
                    return [pexels_video(102)]
                return []

            probe = {"width": 1080, "height": 1920, "fps": 30.0, "duration_seconds": 75.0}
            with (
                patch.object(bs, "validate_media_tools"),
                patch.object(bs, "download_file", side_effect=self._fake_download),
                patch.object(
                    bs,
                    "validate_physical",
                    side_effect=[bs.SeedError("first candidate failed"), probe],
                ) as validate_mock,
                patch.object(bs, "make_contact_sheet", side_effect=self._fake_contact_sheet),
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

            manifest = bs.read_json(manifest_path)
            self.assertEqual([item["id"] for item in manifest["candidates"]], ["px-102"])
            self.assertEqual(validate_mock.call_count, 2)
            self.assertEqual(pages[:2], [1, 2])

    def test_discovery_stops_once_inventory_shortage_is_filled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry_path, rejection_path, reviews_root, approvals_root, request_path, output_dir = self._fixture(root)

            def search_fn(query, api_key, per_page, page):
                if query == "pov walking" and page == 1:
                    return [pexels_video(201), pexels_video(202)]
                return []

            probe = {"width": 1080, "height": 1920, "fps": 30.0, "duration_seconds": 75.0}
            with (
                patch.object(bs, "validate_media_tools"),
                patch.object(bs, "download_file", side_effect=self._fake_download),
                patch.object(bs, "validate_physical", return_value=probe) as validate_mock,
                patch.object(bs, "make_contact_sheet", side_effect=self._fake_contact_sheet),
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

            manifest = bs.read_json(manifest_path)
            self.assertEqual(len(manifest["candidates"]), 1)
            self.assertEqual(manifest["candidates"][0]["id"], "px-201")
            self.assertEqual(validate_mock.call_count, 1)

    def test_permanently_rejected_candidate_is_skipped_during_backfill(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry_path, rejection_path, reviews_root, approvals_root, request_path, output_dir = self._fixture(root)
            bs.write_json(rejection_path, {"rejected_ids": ["px-301"]})

            def search_fn(query, api_key, per_page, page):
                if query == "pov walking" and page == 1:
                    return [pexels_video(301), pexels_video(302)]
                return []

            probe = {"width": 1080, "height": 1920, "fps": 30.0, "duration_seconds": 75.0}
            with (
                patch.object(bs, "validate_media_tools"),
                patch.object(bs, "download_file", side_effect=self._fake_download),
                patch.object(bs, "validate_physical", return_value=probe) as validate_mock,
                patch.object(bs, "make_contact_sheet", side_effect=self._fake_contact_sheet),
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

            manifest = bs.read_json(manifest_path)
            self.assertEqual([item["id"] for item in manifest["candidates"]], ["px-302"])
            self.assertEqual(validate_mock.call_count, 1)


class PromotionRejectionTests(unittest.TestCase):
    def _fixture(self, root: Path):
        registry_path = root / "backgrounds.json"
        rejection_path = root / "background-rejections.json"
        reviews_root = root / "reviews"
        review_id = "bgreq-20260915-002"
        approval_path = root / f"{review_id}.json"

        bs.write_json(registry_path, {"assets": []})
        bs.write_json(rejection_path, {"rejected_ids": []})
        bs.write_json(
            reviews_root / review_id / "manifest.json",
            {
                "review_id": review_id,
                "request": {"target_per_category": 3, "max_candidates": 6},
                "candidates": [
                    review_candidate("px-321"),
                    review_candidate("px-654", "crafting"),
                ],
            },
        )
        bs.write_json(approval_path, {"review_id": review_id, "approved_ids": ["px-321"]})
        return registry_path, rejection_path, reviews_root, approval_path

    def test_non_approved_review_candidates_are_persisted_as_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry_path, rejection_path, reviews_root, approval_path = self._fixture(root)
            added, rejected_added = bsr.promote_with_rejections(
                approval_path,
                registry_path,
                reviews_root,
                rejection_path,
            )
            self.assertEqual((added, rejected_added), (1, 1))
            self.assertEqual(bs.read_json(rejection_path), {"rejected_ids": ["px-654"]})
            self.assertEqual([item["id"] for item in bs.read_json(registry_path)["assets"]], ["px-321"])

    def test_promotion_rerun_is_idempotent_for_rejections(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry_path, rejection_path, reviews_root, approval_path = self._fixture(root)
            bsr.promote_with_rejections(approval_path, registry_path, reviews_root, rejection_path)
            added, rejected_added = bsr.promote_with_rejections(
                approval_path,
                registry_path,
                reviews_root,
                rejection_path,
            )
            self.assertEqual((added, rejected_added), (0, 0))
            self.assertEqual(bs.read_json(rejection_path), {"rejected_ids": ["px-654"]})

    def test_permanently_rejected_candidate_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry_path, rejection_path, reviews_root, approval_path = self._fixture(root)
            bs.write_json(rejection_path, {"rejected_ids": ["px-321"]})
            with self.assertRaises(bs.SeedError):
                bsr.promote_with_rejections(
                    approval_path,
                    registry_path,
                    reviews_root,
                    rejection_path,
                )


if __name__ == "__main__":
    unittest.main()
