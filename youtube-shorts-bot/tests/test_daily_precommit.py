import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from common.workflow_common import CONTENT_ID_RE
from media.media_readiness import MIN_SELECTABLE_ASSETS
from planning import daily_precommit, ranked_promotion
from planning.planner_contract import DAILY_PUBLICATION, build_contract
from planning.planning_config import TITLE_WEIGHTS
from validation.validate_content import SCHEMA_VERSION


BOT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    BOT_ROOT
    / "content"
    / "planning-pools"
    / "adhoc"
    / "ap-20260913-scheduled-a04.json"
)
RULES_SHA = "1" * 40
PLAN_DATE = "2099-01-01"
CATEGORY = "satisfying_process"


def _upgrade_request_v7(request, index):
    request["schema_version"] = SCHEMA_VERSION
    request["content_id"] = f"wd-20990101T000000-daily-c{index:05d}"
    request["publication"] = copy.deepcopy(DAILY_PUBLICATION)
    request["planning"]["plan_date"] = PLAN_DATE
    request["visual"] = {
        "background_mode": "concatenated_fit_to_short",
        "background_primary_sequence": [
            {
                "background_id": f"satisfying-{asset:03d}",
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": 80.0,
            }
            for asset in (1, 2, 3)
        ],
        "background_backup_sequence": [
            {
                "background_id": f"satisfying-{asset:03d}",
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": 80.0,
            }
            for asset in (4, 5, 6)
        ],
    }


def _candidate(template, index):
    request = copy.deepcopy(template)
    _upgrade_request_v7(request, index)
    return {
        "rank": index,
        "candidate_id": f"daily-c{index:02d}",
        "background_category": CATEGORY,
        "request": request,
    }


def valid_pool(target=24, mode="normal_next_day"):
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    template = fixture["ranked_candidates"][0]["request"]
    ranked = [_candidate(template, index) for index in range(1, target + 1)]
    slots = ranked_promotion._canonical_normal_slots(PLAN_DATE)
    if target != 24 or mode != "normal_next_day":
        slots = slots[:target]
    return {
        "schema_version": ranked_promotion.POOL_SCHEMA_VERSION,
        "pool_type": "daily",
        "pool_id": "dp-20990101-a01",
        "plan_date": PLAN_DATE,
        "planning_mode": mode,
        "target_count": target,
        "publication_slots": slots,
        "planning_execution": {
            "editorial_selection_owner": "chatgpt",
            "planning_method": "chatgpt_ranked_pool",
            "rules_source_sha": RULES_SHA,
            "ranked_candidate_ids": [f"daily-c{index:02d}" for index in range(1, target + 1)],
        },
        "ranked_candidates": ranked,
    }


def _selected_asset(asset_id, category=CATEGORY, *, verified=True):
    return {
        "id": asset_id,
        "status": "active",
        "verified": verified,
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
        "duration_seconds": 300.0,
        "renditions": [
            {
                "id": f"r-{asset_id}",
                "width": 1080,
                "height": 1920,
                "fps": 30.0,
                "file_type": "video/mp4",
                "direct_url": f"https://videos.pexels.com/{asset_id}.mp4",
            }
        ],
    }


def selected_registry():
    # Deliberately below the repository-wide maintenance threshold.
    return {
        "schema_version": 3,
        "assets": [
            _selected_asset(f"satisfying-{index:03d}") for index in range(1, 7)
        ],
    }


def validate(pool, registry=None, now_utc=None):
    raw = (json.dumps(pool, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return daily_precommit.validate_draft(
        pool,
        RULES_SHA,
        raw_bytes=raw,
        registry=registry or selected_registry(),
        check_checkout_head=False,
        check_uniqueness=False,
        now_utc=now_utc,
    )


class DailyPrecommitTests(unittest.TestCase):
    def test_contract_snapshot_uses_simplified_live_config(self):
        contract = build_contract()
        self.assertEqual(contract["title_score_components"], list(TITLE_WEIGHTS))
        self.assertEqual(contract["content_id_pattern"], CONTENT_ID_RE.pattern)
        self.assertEqual(contract["daily_pool_size"], 24)
        self.assertEqual(contract["daily_normal_target"], 24)
        self.assertEqual(contract["daily_publication_template"], DAILY_PUBLICATION)
        self.assertFalse(contract["media_readiness"]["required_before_daily"])
        self.assertFalse(contract["media_readiness"]["automatic_replenishment_enabled"])
        self.assertEqual(contract["request_schema_version"], SCHEMA_VERSION)

    def test_normal_day_requires_twenty_four_of_twenty_four(self):
        registry = selected_registry()
        self.assertLess(len(registry["assets"]), MIN_SELECTABLE_ASSETS)
        result = validate(valid_pool(), registry)
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(result["commit_allowed"])
        self.assertEqual(result["expected_candidates"], 24)
        self.assertEqual(result["valid_candidates"], 24)
        self.assertEqual(result["failed_candidates"], 0)
        self.assertTrue(result["draft_sha256"])

    def test_twenty_three_candidates_fail_for_normal_day(self):
        pool = valid_pool()
        pool["ranked_candidates"] = pool["ranked_candidates"][:-1]
        pool["planning_execution"]["ranked_candidate_ids"] = pool["planning_execution"]["ranked_candidate_ids"][:-1]
        result = validate(pool)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("exactly 24" in item for item in result["pool_errors"]))

    def test_twenty_five_candidates_fail_for_normal_day(self):
        pool = valid_pool()
        template = pool["ranked_candidates"][0]["request"]
        extra = _candidate(template, 25)
        pool["ranked_candidates"].append(extra)
        pool["planning_execution"]["ranked_candidate_ids"].append("daily-c25")
        result = validate(pool)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("exactly 24" in item for item in result["pool_errors"]))

    def test_catch_up_candidate_count_equals_target_count(self):
        pool = valid_pool(target=3, mode="same_day_catch_up")
        result = validate(
            pool,
            now_utc=datetime(2098, 12, 31, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["expected_candidates"], 3)
        self.assertEqual(result["valid_candidates"], 3)

    def test_mixed_background_category_fails(self):
        registry = selected_registry()
        registry["assets"][0]["retention_category"] = "cooking"
        result = validate(valid_pool(), registry)
        self.assertEqual(result["status"], "FAIL")
        joined = "\n".join(result["candidate_results"][0]["errors"])
        self.assertIn("candidate.background_category", joined)

    def test_invalid_selected_asset_fails(self):
        registry = selected_registry()
        registry["assets"][0]["verified"] = False
        result = validate(valid_pool(), registry)
        self.assertEqual(result["status"], "FAIL")
        joined = "\n".join(result["candidate_results"][0]["errors"])
        self.assertIn("must be verified", joined)

    def test_validation_does_not_mutate_ai_authored_pool(self):
        pool = valid_pool()
        original = copy.deepcopy(pool)
        validate(pool)
        self.assertEqual(pool, original)

    def test_daily_prompt_requires_one_checkpoint_and_twenty_four_candidates(self):
        prompt = (BOT_ROOT / "planning" / "DAILY_PLANNER_PROMPT.md").read_text(
            encoding="utf-8"
        )
        lower = prompt.lower()
        self.assertIn("connector_checkpoint.py", prompt)
        self.assertIn("--profile daily", prompt)
        self.assertIn("24/24", prompt)
        self.assertIn("draft_sha256", prompt)
        self.assertIn("rules_source_sha", prompt)
        self.assertIn("automatic planner replenishment is **disabled**", lower)
        self.assertNotIn("all 36 candidates", lower)
        self.assertNotIn("first-24", lower)
        self.assertNotIn("$(git rev-parse HEAD)", prompt)


if __name__ == "__main__":
    unittest.main()
