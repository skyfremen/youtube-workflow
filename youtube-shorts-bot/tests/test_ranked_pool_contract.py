import copy
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from media.media_readiness import MIN_SELECTABLE_ASSETS, REQUIRED_CATEGORY_MINIMUMS
from planning import planner_core, ranked_promotion
from test_request_schema import valid_request
from validation import validate_content_v5 as legacy_v5
from validation.validate_content import (
    validate_background_registry_contract,
    validate_request_data,
)


CATEGORY = "satisfying_process"


def v5_request():
    data = valid_request()
    data["schema_version"] = 5
    data["visual"]["background_primary_treatment"] = {
        "segment_start_seconds": 0.0,
        "segment_duration_seconds": 12.0,
        "playback_rate": 1.25,
    }
    data["visual"]["background_backup_treatment"] = {
        "segment_start_seconds": 0.0,
        "segment_duration_seconds": 12.0,
        "playback_rate": 1.25,
    }
    return data


def _ready_asset(asset_id, category, counter):
    return {
        "id": asset_id,
        "status": "active",
        "verified": True,
        "commercial_use": True,
        "has_watermark": False,
        "has_embedded_text": False,
        "retention_category": category,
        "orientation": "vertical",
        "motion_type": "continuous-process",
        "motion_intensity": "high",
        "visual_satisfaction_score": 100,
        "loopability_score": 100,
        "caption_readability_score": 100,
        "duration_seconds": 16.0,
        "renditions": [{
            "id": f"test-r-{counter:03d}",
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "file_type": "video/mp4",
            "direct_url": f"https://videos.pexels.com/test-{counter:03d}.mp4",
        }],
    }


def ready_registry():
    assets = []
    counter = 0
    for category, minimum in REQUIRED_CATEGORY_MINIMUMS.items():
        for _ in range(minimum):
            counter += 1
            asset_id = (
                "satisfying-001" if counter == 1
                else "satisfying-002" if counter == 2
                else f"test-ready-{counter:03d}"
            )
            assets.append(_ready_asset(asset_id, category, counter))
    while len(assets) < MIN_SELECTABLE_ASSETS:
        counter += 1
        assets.append(_ready_asset(f"test-ready-{counter:03d}", "satisfying_process", counter))
    return {"schema_version": 3, "assets": assets}


def ranked_items(count, *, current=False):
    items = []
    for rank in range(1, count + 1):
        request = v5_request()
        request["content_id"] = f"wd-20990910T000000-ranked-{rank:02d}-a1b2c3"
        item = {
            "rank": rank,
            "candidate_id": f"candidate-{rank:02d}",
            "request": request,
        }
        if current:
            item["background_category"] = CATEGORY
        items.append(item)
    return items


def historical_daily_pool(*, mode="normal_next_day", target=24, slots=None):
    if slots is None:
        slots = ranked_promotion._canonical_normal_slots("2099-09-10")
    items = ranked_items(ranked_promotion.LEGACY_DAILY_POOL_SIZE)
    return {
        "schema_version": ranked_promotion.LEGACY_POOL_SCHEMA_VERSION,
        "pool_type": "daily",
        "pool_id": "dp-20990910-a01",
        "plan_date": "2099-09-10",
        "planning_mode": mode,
        "target_count": target,
        "publication_slots": slots,
        "planning_execution": {
            "editorial_selection_owner": "chatgpt",
            "planning_method": "chatgpt_ranked_pool",
            "rules_source_sha": "0" * 40,
            "ranked_candidate_ids": [item["candidate_id"] for item in items],
        },
        "ranked_candidates": items,
    }


class RankedPoolContractTests(unittest.TestCase):
    def test_current_and_historical_pool_sizes_are_explicit(self):
        self.assertEqual(ranked_promotion.DAILY_POOL_SIZE, 24)
        self.assertEqual(ranked_promotion.ADHOC_POOL_SIZE, 1)
        self.assertEqual(ranked_promotion.NORMAL_DAILY_TARGET, 24)
        self.assertEqual(ranked_promotion.LEGACY_DAILY_POOL_SIZE, 36)
        self.assertEqual(ranked_promotion.LEGACY_ADHOC_POOL_SIZE, 5)

    def test_daily_pool_path_supports_immutable_retry_attempts(self):
        first = "youtube-shorts-bot/content/planning-pools/daily/2099-09-10/dp-20990910-a01.json"
        second = "youtube-shorts-bot/content/planning-pools/daily/2099-09-10/dp-20990910-a02.json"
        self.assertIsNotNone(ranked_promotion.DAILY_POOL_RE.fullmatch(first))
        self.assertIsNotNone(ranked_promotion.DAILY_POOL_RE.fullmatch(second))
        self.assertNotEqual(first, second)

    def test_current_candidate_validator_requires_24_and_preserves_order(self):
        items = ranked_items(24, current=True)
        candidates, ids = ranked_promotion._validate_ranked_candidates(
            {"ranked_candidates": items}, 24, require_background_category=True
        )
        self.assertEqual(candidates, items)
        self.assertEqual(ids, [f"candidate-{rank:02d}" for rank in range(1, 25)])

    def test_current_candidate_validator_rejects_wrong_size_or_rank_gap(self):
        with self.assertRaises(ranked_promotion.PromotionError):
            ranked_promotion._validate_ranked_candidates(
                {"ranked_candidates": ranked_items(23, current=True)},
                24,
                require_background_category=True,
            )
        broken = ranked_items(1, current=True)
        broken[0]["rank"] = 2
        with self.assertRaises(ranked_promotion.PromotionError):
            ranked_promotion._validate_ranked_candidates(
                {"ranked_candidates": broken}, 1, require_background_category=True
            )

    def test_historical_schema1_daily_pool_keeps_36_candidate_compatibility(self):
        pool = historical_daily_pool()
        with mock.patch.object(ranked_promotion, "_validate_execution"), mock.patch.object(
            ranked_promotion, "_validate_exact_pool_commit"
        ):
            result = ranked_promotion._validate_daily_pool(
                pool,
                "youtube-shorts-bot/content/planning-pools/daily/2099-09-10/dp-20990910-a01.json",
                "1" * 40,
            )
        self.assertEqual(result[0], ranked_promotion.LEGACY_POOL_SCHEMA_VERSION)
        self.assertEqual(len(result[-2]), 36)

    def test_catch_up_slots_are_rechecked_at_historical_promotion_time(self):
        pool = historical_daily_pool(
            mode="same_day_catch_up",
            target=1,
            slots=["2099-09-09T17:00:00Z"],
        )
        with mock.patch.object(ranked_promotion, "_validate_execution"), mock.patch.object(
            ranked_promotion, "_validate_exact_pool_commit"
        ):
            with self.assertRaisesRegex(ranked_promotion.PromotionError, "30 minutes"):
                ranked_promotion._validate_daily_pool(
                    pool,
                    "youtube-shorts-bot/content/planning-pools/daily/2099-09-10/dp-20990910-a01.json",
                    "1" * 40,
                    now_utc=datetime(2099, 9, 9, 16, 40, tzinfo=timezone.utc),
                )

    def test_historical_v5_hard_registry_validation_accepts_safe_defaults(self):
        errors = validate_background_registry_contract(v5_request(), registry=ready_registry())
        self.assertEqual(errors, [])

    def test_historical_v5_readiness_semantics_are_preserved(self):
        empty_registry = {"schema_version": 3, "assets": []}
        errors = validate_request_data(
            v5_request(), enforce_registry=True, registry=empty_registry
        )
        self.assertTrue(any("media readiness requires replenishment" in error for error in errors))

    def test_v5_hard_registry_validation_rejects_unknown_asset(self):
        data = v5_request()
        data["visual"]["background_primary_id"] = "missing-background"
        errors = validate_request_data(data, enforce_registry=True)
        self.assertTrue(any("unknown background asset" in error for error in errors))

    def test_v5_hard_registry_validation_rejects_treatment_past_asset_end(self):
        data = v5_request()
        data["visual"]["background_primary_treatment"] = {
            "segment_start_seconds": 15.0,
            "segment_duration_seconds": 12.0,
            "playback_rate": 1.25,
        }
        errors = validate_request_data(data, enforce_registry=True, registry=ready_registry())
        self.assertTrue(any("exceeds background" in error for error in errors))

    def test_v5_treatment_rejects_non_finite_numbers(self):
        treatment = {
            "segment_start_seconds": float("nan"),
            "segment_duration_seconds": 12.0,
            "playback_rate": float("inf"),
        }
        errors = legacy_v5.validate_background_treatment(treatment)
        self.assertGreaterEqual(sum("must be finite" in error for error in errors), 2)

    def test_scheduled_adhoc_uniqueness_remains_historical_compatibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot_root = Path(tmp)
            request_dir = bot_root / "content" / "requests"
            request_dir.mkdir(parents=True)
            existing = request_dir / "wd-20260912T010000-adhoc-existing.json"
            existing.write_text("{}\n", encoding="utf-8")
            with mock.patch.object(planner_core, "BOT_ROOT", bot_root):
                with self.assertRaisesRegex(
                    ranked_promotion.PromotionError, "already exists"
                ):
                    ranked_promotion.verify_scheduled_adhoc_uniqueness(
                        "2026-09-12", "wd-20260912T010000-adhoc-new"
                    )

    def test_validation_never_mutates_ai_authored_request(self):
        data = v5_request()
        original = copy.deepcopy(data)
        validate_request_data(data, enforce_registry=True)
        self.assertEqual(data, original)


if __name__ == "__main__":
    unittest.main()
