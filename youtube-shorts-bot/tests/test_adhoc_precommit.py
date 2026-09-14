import copy
import json
import unittest
from pathlib import Path

from common.workflow_common import CONTENT_ID_RE
from media.media_readiness import MIN_SELECTABLE_ASSETS
from planning import adhoc_precommit
from planning.planner_contract import build_contract
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
CATEGORY = "satisfying_process"


def _upgrade_request_v7(request):
    request["schema_version"] = SCHEMA_VERSION
    request["content_id"] = "wd-20260914T094900-adhoc-manual-abc123"
    request["visual"] = {
        "background_mode": "concatenated_fit_to_short",
        "background_primary_sequence": [
            {
                "background_id": f"satisfying-{index:03d}",
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": 80.0,
            }
            for index in (1, 2, 3)
        ],
        "background_backup_sequence": [
            {
                "background_id": f"satisfying-{index:03d}",
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": 80.0,
            }
            for index in (4, 5, 6)
        ],
    }


def valid_pool():
    historical = json.loads(FIXTURE.read_text(encoding="utf-8"))
    item = copy.deepcopy(historical["ranked_candidates"][0])
    item["rank"] = 1
    item["candidate_id"] = "adhoc-c01"
    item["background_category"] = CATEGORY
    _upgrade_request_v7(item["request"])
    return {
        "schema_version": 2,
        "pool_type": "adhoc",
        "pool_id": "ap-20260914-manual-a01",
        "planning_mode": "manual_on_demand",
        "singapore_date": "2026-09-14",
        "target_count": 1,
        "planning_execution": {
            "editorial_selection_owner": "chatgpt",
            "planning_method": "chatgpt_ranked_pool",
            "rules_source_sha": RULES_SHA,
            "ranked_candidate_ids": ["adhoc-c01"],
        },
        "ranked_candidates": [item],
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
    # Deliberately only six assets: far below the global maintenance minimum.
    return {
        "schema_version": 3,
        "assets": [
            _selected_asset(f"satisfying-{index:03d}") for index in range(1, 7)
        ],
    }


def validate(pool, registry=None):
    raw = (json.dumps(pool, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return adhoc_precommit.validate_draft(
        pool,
        RULES_SHA,
        raw_bytes=raw,
        registry=registry or selected_registry(),
        check_checkout_head=False,
        check_uniqueness=False,
    )


class AdhocPrecommitTests(unittest.TestCase):
    def test_contract_snapshot_uses_simplified_live_config(self):
        contract = build_contract()
        self.assertEqual(contract["title_score_components"], list(TITLE_WEIGHTS))
        self.assertEqual(contract["content_id_pattern"], CONTENT_ID_RE.pattern)
        self.assertEqual(contract["adhoc_pool_size"], 1)
        self.assertEqual(contract["adhoc_planning_modes"], ["manual_on_demand"])
        self.assertFalse(contract["media_readiness"]["required_before_adhoc"])
        self.assertFalse(contract["media_readiness"]["automatic_replenishment_enabled"])
        self.assertTrue(contract["selected_background_validation"]["required"])
        self.assertTrue(contract["selected_background_validation"]["same_category_primary_backup"])
        self.assertEqual(contract["request_schema_version"], SCHEMA_VERSION)

    def test_one_candidate_passes_without_global_media_readiness(self):
        registry = selected_registry()
        self.assertLess(len(registry["assets"]), MIN_SELECTABLE_ASSETS)
        result = validate(valid_pool(), registry)
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(result["commit_allowed"])
        self.assertEqual(result["expected_candidates"], 1)
        self.assertEqual(result["valid_candidates"], 1)
        self.assertEqual(result["failed_candidates"], 0)
        self.assertTrue(result["draft_sha256"])

    def test_zero_candidates_fail(self):
        pool = valid_pool()
        pool["ranked_candidates"] = []
        pool["planning_execution"]["ranked_candidate_ids"] = []
        result = validate(pool)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["commit_allowed"])
        self.assertTrue(any("exactly 1" in item for item in result["pool_errors"]))

    def test_two_candidates_fail(self):
        pool = valid_pool()
        second = copy.deepcopy(pool["ranked_candidates"][0])
        second["rank"] = 2
        second["candidate_id"] = "adhoc-c02"
        second["request"]["content_id"] = "wd-20260914T095000-adhoc-manual-def456"
        pool["ranked_candidates"].append(second)
        pool["planning_execution"]["ranked_candidate_ids"].append("adhoc-c02")
        result = validate(pool)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("exactly 1" in item for item in result["pool_errors"]))

    def test_scheduled_daily_is_rejected_for_new_planning(self):
        pool = valid_pool()
        pool["planning_mode"] = "scheduled_daily"
        result = validate(pool)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("manual_on_demand" in item for item in result["pool_errors"]))

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


if __name__ == "__main__":
    unittest.main()
