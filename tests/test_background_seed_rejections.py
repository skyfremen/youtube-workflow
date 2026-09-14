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

    def test_discover_temporarily_injects_permanent_rejections(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rejection_path = root / "background-rejections.json"
            bs.write_json(rejection_path, {"rejected_ids": ["px-99"]})
            observed = {}
            original_pending = bs.pending_review_ids

            def fake_discover(request_path, api_key, output_dir, registry_path, reviews_root):
                observed["excluded"] = bs.pending_review_ids(root / "reviews", root / "approvals")
                return root / "manifest.json"

            with patch.object(bs, "pending_review_ids", return_value={"px-77"}) as pending_mock:
                patched_pending = bs.pending_review_ids
                with patch.object(bs, "discover", side_effect=fake_discover):
                    bsr.discover_with_rejections(
                        root / "request.json",
                        "secret",
                        root / "output",
                        root / "backgrounds.json",
                        root / "reviews",
                        rejection_path,
                    )
                self.assertIs(bs.pending_review_ids, patched_pending)
                pending_mock.assert_called()

            self.assertEqual(observed["excluded"], {"px-77", "px-99"})
            self.assertIs(bs.pending_review_ids, original_pending)


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
