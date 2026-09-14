import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import background_seed as bs


SOURCE = "https://www.pexels.com/video/example-123/"
MEDIA = "https://videos.pexels.com/video-files/123/123-hd_1080_1920_30fps.mp4"


def asset(asset_id="px-123", category="pov_movement", **overrides):
    value = {
        "id": asset_id,
        "category": category,
        "duration_seconds": 75,
        "source_url": SOURCE,
        "download_url": MEDIA,
    }
    value.update(overrides)
    return value


def rendition(width, height, fps=30, link=MEDIA, file_id=1):
    return {
        "id": file_id,
        "file_type": "video/mp4",
        "width": width,
        "height": height,
        "fps": fps,
        "link": link,
    }


def video(video_id=123, duration=75, files=None):
    return {
        "id": video_id,
        "duration": duration,
        "url": f"https://www.pexels.com/video/example-{video_id}/",
        "video_files": files or [rendition(1080, 1920)],
    }


class RegistryTests(unittest.TestCase):
    def test_empty_registry_valid(self):
        self.assertEqual(bs.validate_registry({"assets": []}), {"assets": []})

    def test_exact_five_fields_valid(self):
        bs.validate_registry({"assets": [asset()]})

    def test_unknown_field_rejected(self):
        with self.assertRaises(bs.SeedError):
            bs.validate_registry({"assets": [asset(extra=True)]})

    def test_unknown_category_rejected(self):
        with self.assertRaises(bs.SeedError):
            bs.validate_registry({"assets": [asset(category="other")]})

    def test_short_duration_rejected(self):
        with self.assertRaises(bs.SeedError):
            bs.validate_registry({"assets": [asset(duration_seconds=59)]})

    def test_duplicate_id_rejected(self):
        with self.assertRaises(bs.SeedError):
            bs.validate_registry({"assets": [asset(), asset()]})

    def test_invalid_pexels_source_rejected(self):
        with self.assertRaises(bs.SeedError):
            bs.validate_registry({"assets": [asset(source_url="https://example.com/video/123")]})

    def test_invalid_download_host_rejected(self):
        with self.assertRaises(bs.SeedError):
            bs.validate_registry({"assets": [asset(download_url="https://evil.example/video.mp4")]})


class RenditionTests(unittest.TestCase):
    def test_no_suitable_rendition(self):
        choice = bs.select_rendition({"video_files": [rendition(1920, 1080), rendition(2560, 1440)]})
        self.assertIsNone(choice)

    def test_exact_1080_portrait_beats_4k(self):
        choice = bs.select_rendition({"video_files": [
            rendition(2160, 3840, file_id=2, link="https://videos.pexels.com/big.mp4"),
            rendition(1080, 1920, file_id=1),
        ]})
        self.assertEqual((choice["width"], choice["height"]), (1080, 1920))

    def test_4k_landscape_selected_when_smaller_crops_fail(self):
        choice = bs.select_rendition({"video_files": [
            rendition(1920, 1080, file_id=1),
            rendition(2560, 1440, file_id=2, link="https://videos.pexels.com/1440.mp4"),
            rendition(3840, 2160, file_id=3, link="https://videos.pexels.com/2160.mp4"),
        ]})
        self.assertEqual((choice["width"], choice["height"]), (3840, 2160))

    def test_60fps_not_chosen_when_suitable_30fps_exists(self):
        choice = bs.select_rendition({"video_files": [
            rendition(1080, 1920, fps=60, file_id=1),
            rendition(1440, 2560, fps=30, file_id=2, link="https://videos.pexels.com/30fps.mp4"),
        ]})
        self.assertEqual(choice["fps"], 30)

    def test_physical_probe_mismatch_rejected(self):
        candidate = bs._candidate_from_video(video(), "pov_movement")
        with patch.object(bs, "ffprobe", return_value={
            "width": 720, "height": 1280, "fps": 30.0, "duration_seconds": 75.0
        }):
            with self.assertRaises(bs.SeedError):
                bs.validate_physical(candidate, Path("unused.mp4"))


class DiscoveryTests(unittest.TestCase):
    def test_duplicate_discovery_id_skipped(self):
        registry = {"assets": [asset("px-1")]}
        request = {"target_per_category": 3, "max_candidates": 4}

        def search_fn(query, key, per_page):
            return [video(1), video(2)]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            found = bs.collect_metadata_candidates(
                registry,
                request,
                "secret",
                reviews_root=root / "reviews",
                approvals_root=root / "approvals",
                search_fn=search_fn,
            )
        ids = [item["id"] for item in found]
        self.assertNotIn("px-1", ids)
        self.assertEqual(len(ids), len(set(ids)))


class PromotionTests(unittest.TestCase):
    def _fixture(self, root: Path):
        registry_path = root / "backgrounds.json"
        registry_path.write_text('{"assets": []}\n', encoding="utf-8")
        reviews = root / "reviews"
        review_id = "bgreq-20260915-001"
        manifest = {
            "review_id": review_id,
            "request": {"target_per_category": 6, "max_candidates": 12},
            "candidates": [{
                **asset("px-321", "food_process"),
                "width": 1080,
                "height": 1920,
                "fps": 30.0,
            }],
        }
        bs.write_json(reviews / review_id / "manifest.json", manifest)
        approval = root / f"{review_id}.json"
        bs.write_json(approval, {"review_id": review_id, "approved_ids": ["px-321"]})
        return registry_path, reviews, approval, review_id

    def test_approval_id_not_in_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry_path, reviews, approval, review_id = self._fixture(root)
            bs.write_json(approval, {"review_id": review_id, "approved_ids": ["px-999"]})
            with self.assertRaises(bs.SeedError):
                bs.promote(approval, registry_path, reviews)

    def test_same_approval_twice_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry_path, reviews, approval, _ = self._fixture(root)
            self.assertEqual(bs.promote(approval, registry_path, reviews), 1)
            self.assertEqual(bs.promote(approval, registry_path, reviews), 0)
            saved = bs.read_json(registry_path)
            self.assertEqual(len(saved["assets"]), 1)

    def test_promotion_copies_only_final_five_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry_path, reviews, approval, _ = self._fixture(root)
            bs.promote(approval, registry_path, reviews)
            saved = bs.read_json(registry_path)
            self.assertEqual(set(saved["assets"][0]), bs.FINAL_ASSET_FIELDS)


if __name__ == "__main__":
    unittest.main()
