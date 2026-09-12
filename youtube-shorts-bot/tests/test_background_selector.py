import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from media.background_selector import (
    audit_ai_selection,
    derive_category_history,
    derive_usage_history,
    rank_assets,
    retention_category,
    select_logical_backgrounds,
)


def asset(
    n,
    tags=("fluid", "calm"),
    quality=90,
    *,
    category=None,
    intensity="medium",
    motion_type="loop",
    orientation="vertical",
):
    value = {
        "id": f"satisfying-{n:03}", "status": "active", "verified": True,
        "title": f"Fluid asset {n}", "visual_tags": list(tags),
        "motion_type": motion_type, "motion_intensity": intensity, "orientation": orientation,
        "loopability_score": quality, "visual_satisfaction_score": quality,
        "caption_readability_score": quality,
        "source": "Pexels", "source_page": f"https://www.pexels.com/video/{1000+n}/",
        "license": "Pexels License", "commercial_use": True,
        "renditions": [{
            "id": f"r{n}", "width": 1080, "height": 1920, "fps": 30,
            "file_type": "video/mp4", "direct_url": f"https://videos.pexels.com/{n}.mp4",
        }],
    }
    if category:
        value["retention_category"] = category
    return value


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
    def test_high_retention_candidate_beats_literal_but_weaker_generic_candidate(self):
        literal = asset(1, tags=("relationship", "argument"), quality=96, category="generic")
        literal["title"] = "Relationship argument"
        literal["motion_type"] = "ambient"
        literal["motion_intensity"] = "low"
        engaging = asset(
            2,
            tags=("baking", "cake", "decorating"),
            quality=92,
            category="baking",
            intensity="high",
            motion_type="continuous_process",
        )
        requirements = {"visual_tags": ["relationship", "argument"]}
        ranked = rank_assets({"assets": [literal, engaging]}, requirements, [])
        self.assertEqual(ranked[0]["id"], engaging["id"])
        self.assertGreater(ranked[0]["retention_score"], ranked[1]["retention_score"])

    def test_topic_relevance_is_a_boost_not_an_eligibility_requirement(self):
        unrelated = asset(
            1,
            tags=("baking", "dough"),
            quality=94,
            category="baking",
            intensity="high",
            motion_type="continuous_process",
        )
        second = asset(
            2,
            tags=("pottery", "crafting"),
            quality=92,
            category="crafting",
            intensity="high",
            motion_type="continuous_process",
        )
        requirements = {"visual_tags": ["relationship", "argument"]}
        decision = select_logical_backgrounds({"assets": [unrelated, second]}, requirements, [])
        self.assertFalse(decision["expansion_required"])
        first = next(x for x in decision["ranked_candidates"] if x["id"] == unrelated["id"])
        self.assertLess(first["semantic_score"], 0.45)
        self.assertTrue(first["strong_match"])

    def test_recent_hard_avoid_beats_excellent_match(self):
        recent = asset(1, quality=99, category="baking", intensity="high")
        fresh = asset(2, quality=90, category="crafting", intensity="high")
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

    def test_category_rotation_is_soft_and_uses_private_receipts(self):
        baking = asset(1, tags=("baking",), quality=93, category="baking", intensity="high")
        craft = asset(2, tags=("crafting",), quality=91, category="crafting", intensity="high")
        history = [receipt(0, baking["id"]), receipt(1, baking["id"]), receipt(2, baking["id"])]
        ranked = rank_assets({"assets": [baking, craft]}, {}, history)
        self.assertEqual(ranked[0]["id"], craft["id"])
        derived = derive_category_history({"assets": [baking, craft]}, history)
        self.assertEqual(derived["counts"]["baking"], 3)

    def test_category_rotation_does_not_force_bad_candidate(self):
        first = asset(1, quality=94, category="baking", intensity="high")
        second = asset(2, quality=92, category="baking", intensity="high")
        weak_other = asset(3, quality=55, category="cleaning", intensity="low")
        decision = select_logical_backgrounds({"assets": [first, second, weak_other]}, {}, [])
        self.assertFalse(decision["expansion_required"])
        self.assertEqual({decision["primary"], decision["backup"]}, {first["id"], second["id"]})

    def test_planned_batch_use_penalizes_duplicate_without_persisting_state(self):
        first = asset(1, quality=93, category="baking", intensity="high")
        second = asset(2, quality=92, category="crafting", intensity="high")
        ranked = rank_assets(
            {"assets": [first, second]},
            {},
            [],
            planned_asset_ids=[first["id"]],
            planned_categories=["baking"],
        )
        self.assertEqual(ranked[0]["id"], second["id"])
        selected_first = next(x for x in ranked if x["id"] == first["id"])
        self.assertGreater(selected_first["planned_asset_penalty"], 0)

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

    def test_scheduled_planning_receipts_count_toward_recency(self):
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

    def test_ai_selection_allows_low_topic_fit_when_retention_is_strong(self):
        first = asset(1, tags=("baking",), quality=92, category="baking", intensity="high")
        second = asset(2, tags=("cooking",), quality=91, category="cooking", intensity="high")
        requirements = {"visual_tags": ["relationship", "argument"]}
        audit = audit_ai_selection(
            {"assets": [first, second]}, first["id"], second["id"], [], requirements
        )
        self.assertTrue(audit["passed"])
        self.assertLess(audit["primary"]["semantic_score"], 0.45)
        self.assertGreaterEqual(audit["primary"]["retention_score"], 0.72)

    def test_ai_selection_rejects_recent_or_oversized_only_asset(self):
        recent = asset(1)
        oversized = asset(2)
        oversized["renditions"] = [{
            "id": "oversized", "width": 7680, "height": 4320, "fps": 30,
            "file_type": "video/mp4", "direct_url": "https://videos.pexels.com/4k.mp4",
        }]
        audit = audit_ai_selection(
            {"assets": [recent, oversized]}, recent["id"], oversized["id"],
            [receipt(0, recent["id"], scheduled=True)], REQ,
        )
        self.assertFalse(audit["passed"])
        self.assertTrue(any("last 10 Shorts" in message for message in audit["errors"]))
        self.assertTrue(any("1080x1920" in message for message in audit["errors"]))

    def test_older_entries_without_retention_metadata_are_inferred_lazily(self):
        old = asset(1, tags=("cake", "decorating"), quality=90)
        old.pop("retention_category", None)
        self.assertEqual(retention_category(old), "baking")
        ranked = rank_assets({"assets": [old]}, {}, [])
        self.assertEqual(ranked[0]["retention_category"], "baking")

    def test_unlicensed_social_gameplay_never_enters_eligible_pool(self):
        gameplay = asset(1, quality=99, category="licensed_gameplay", intensity="high")
        gameplay["source"] = "YouTube"
        gameplay["source_page"] = "https://www.youtube.com/watch?v=creator-video"
        registry = {"license_reference": "https://www.pexels.com/license/", "assets": [gameplay, asset(2)]}
        ranked = rank_assets(registry, {}, [])
        self.assertNotIn(gameplay["id"], {item["id"] for item in ranked})


if __name__ == "__main__":
    unittest.main()
