import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from background_selector import (
    audit_ai_selection,
    derive_usage_history,
    rank_assets,
    select_logical_backgrounds,
)


def asset(n, tags=("fluid", "calm"), quality=90):
    return {
        "id": f"satisfying-{n:03}", "status": "active", "verified": True,
        "title": f"Fluid asset {n}", "visual_tags": list(tags),
        "motion_type": "loop", "motion_intensity": "medium", "orientation": "vertical",
        "loopability_score": quality, "visual_satisfaction_score": quality,
        "caption_readability_score": quality,
        "renditions": [{
            "id": f"r{n}", "width": 1080, "height": 1920, "fps": 30,
            "file_type": "video/mp4", "direct_url": f"https://videos.pexels.com/{n}.mp4",
        }],
    }


def receipt(n, asset_id, *, passed=True, scheduled=False, published=False):
    created = datetime(2026, 9, 9, tzinfo=timezone.utc) - timedelta(minutes=n)
    if scheduled:
        return {
            "content_id": f"wd-test-{n}", "receipt_created_at": created.isoformat(),
            "verification_state": "verified_scheduled_published" if published else "verified_scheduled",
            "publication_mode": "scheduled", "privacy_status": "public" if published else "private",
            "publish_at": "2026-09-09T16:00:00Z", "publish_at_absent": False,
            "verification": {"passed": passed}, "background_asset_id": asset_id,
        }
    return {
        "content_id": f"wd-test-{n}", "receipt_created_at": created.isoformat(),
        "verification_state": "verified_private" if passed else "failed",
        "privacy_status": "private", "publish_at_absent": True,
        "verification": {"passed": passed}, "background_asset_id": asset_id,
    }


REQ = {"visual_tags": ["fluid", "calm"], "motion_type": "loop", "motion_intensity": "medium"}


class BackgroundSelectorTests(unittest.TestCase):
    def test_recent_hard_avoid_beats_excellent_match(self):
        recent = asset(1, quality=99)
        fresh = asset(2, quality=90)
        ranked = rank_assets({"assets": [recent, fresh]}, REQ, [receipt(0, recent["id"])])
        self.assertEqual(ranked[0]["id"], fresh["id"])
        self.assertTrue(next(x for x in ranked if x["id"] == recent["id"])["hard_avoided"])

    def test_recency_penalty_applies_through_30_successes(self):
        assets = [asset(1), asset(2)]
        receipts = [receipt(i, "satisfying-999") for i in range(25)]
        receipts[24]["background_asset_id"] = "satisfying-001"
        ranked = rank_assets({"assets": assets}, REQ, receipts)
        old = next(x for x in ranked if x["id"] == "satisfying-001")
        self.assertEqual(old["shorts_ago"], 24)
        self.assertGreater(old["recency_penalty"], 0)
        self.assertEqual(ranked[0]["id"], "satisfying-002")

    def test_never_used_preferred_when_fit_is_strong(self):
        assets = [asset(1), asset(2)]
        receipts = [receipt(i, "satisfying-999") for i in range(40)]
        receipts[-1]["background_asset_id"] = "satisfying-001"
        ranked = rank_assets({"assets": assets}, REQ, receipts)
        self.assertEqual(ranked[0]["id"], "satisfying-002")
        self.assertTrue(ranked[0]["never_used"])

    def test_relevance_protects_against_unused_poor_match(self):
        strong = asset(1)
        poor = asset(2, tags=("traffic", "crowd"), quality=99)
        poor["title"] = "Busy traffic crowd"
        receipts = [receipt(i, "satisfying-999") for i in range(40)]
        receipts[-1]["background_asset_id"] = strong["id"]
        ranked = rank_assets({"assets": [poor, strong]}, REQ, receipts)
        self.assertEqual(ranked[0]["id"], strong["id"])
        self.assertFalse(next(x for x in ranked if x["id"] == poor["id"])["strong_match"])

    def test_expansion_when_fresh_strong_pool_is_too_small(self):
        registry = {"assets": [asset(1), asset(2)]}
        decision = select_logical_backgrounds(
            registry, REQ, [receipt(0, "satisfying-001"), receipt(1, "satisfying-002")]
        )
        self.assertTrue(decision["expansion_required"])
        self.assertIsNone(decision["primary"])

    def test_failed_render_does_not_count_as_usage(self):
        records = [receipt(0, "satisfying-001", passed=False), receipt(1, "satisfying-002")]
        history = derive_usage_history(records)
        self.assertNotIn("satisfying-001", history)
        self.assertEqual(history["satisfying-002"]["shorts_ago"], 0)

    def test_scheduled_growth_receipts_count_toward_recency(self):
        records = [
            receipt(0, "satisfying-001", scheduled=True),
            receipt(1, "satisfying-002", scheduled=True, published=True),
        ]
        history = derive_usage_history(records)
        self.assertEqual(history["satisfying-001"]["shorts_ago"], 0)
        self.assertEqual(history["satisfying-002"]["shorts_ago"], 1)

    def test_new_requests_exclude_assets_without_production_rendition(self):
        ready = asset(1)
        generic_only = asset(2)
        generic_only["renditions"] = []
        decision = select_logical_backgrounds({"assets": [ready, generic_only]}, REQ, [])
        self.assertTrue(decision["expansion_required"])
        generic_rank = next(x for x in decision["ranked_candidates"] if x["id"] == generic_only["id"])
        self.assertFalse(generic_rank["rendition_ready"])
        self.assertFalse(generic_rank["strong_match"])

    def test_ai_selection_is_semantic_owner_but_mechanical_safety_is_hard(self):
        first, second = asset(1, tags=("traffic",), quality=92), asset(2, tags=("cooking",), quality=91)
        audit = audit_ai_selection({"assets": [first, second]}, first["id"], second["id"], [], REQ)
        self.assertTrue(audit["passed"])
        # Sparse tags may score poorly; the AI's semantic judgment is still allowed
        # provided quality, cache identity, recency and rendition safety pass.
        self.assertLess(audit["primary"]["semantic_score"], 0.45)

    def test_ai_selection_rejects_recent_or_oversized_only_asset(self):
        recent = asset(1)
        oversized = asset(2)
        oversized["renditions"] = [{
            "id": "4k", "width": 3840, "height": 2160, "fps": 30,
            "file_type": "video/mp4", "direct_url": "https://videos.pexels.com/4k.mp4",
        }]
        audit = audit_ai_selection(
            {"assets": [recent, oversized]}, recent["id"], oversized["id"],
            [receipt(0, recent["id"], scheduled=True)], REQ,
        )
        self.assertFalse(audit["passed"])
        self.assertTrue(any("last 10 Shorts" in message for message in audit["errors"]))
        self.assertTrue(any("<=1080p" in message for message in audit["errors"]))


if __name__ == "__main__":
    unittest.main()
