import copy
import json
import unittest
from pathlib import Path

from common.workflow_common import CONTENT_ID_RE
from media.media_readiness import MIN_SELECTABLE_ASSETS, REQUIRED_CATEGORY_MINIMUMS
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


def _upgrade_request_v7(request):
    request["schema_version"] = SCHEMA_VERSION
    request["visual"] = {
        "background_mode": "concatenated_fit_to_short",
        "background_primary_sequence": [
            {"background_id": f"satisfying-{index:03d}", "segment_start_seconds": 0.0, "segment_duration_seconds": 80.0}
            for index in (1, 2, 3)
        ],
        "background_backup_sequence": [
            {"background_id": f"satisfying-{index:03d}", "segment_start_seconds": 0.0, "segment_duration_seconds": 80.0}
            for index in (4, 5, 6)
        ],
    }


def valid_pool():
    pool = json.loads(FIXTURE.read_text(encoding="utf-8"))
    pool["planning_execution"]["rules_source_sha"] = RULES_SHA
    for candidate in pool["ranked_candidates"]:
        _upgrade_request_v7(candidate["request"])
    return pool


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
        "duration_seconds": 300.0,
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
    fixture_ids = [f"satisfying-{index:03d}" for index in range(1, 7)]
    for category, minimum in REQUIRED_CATEGORY_MINIMUMS.items():
        for _ in range(minimum):
            counter += 1
            asset_id = (
                fixture_ids[counter - 1]
                if counter <= len(fixture_ids)
                else f"test-ready-{counter:03d}"
            )
            assets.append(_ready_asset(asset_id, category, counter))
    while len(assets) < MIN_SELECTABLE_ASSETS:
        counter += 1
        assets.append(_ready_asset(f"test-ready-{counter:03d}", "satisfying_process", counter))
    return {"schema_version": 3, "assets": assets}


def validate(pool):
    raw = (json.dumps(pool, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return adhoc_precommit.validate_draft(
        pool,
        RULES_SHA,
        raw_bytes=raw,
        registry=ready_registry(),
        check_checkout_head=False,
        check_uniqueness=False,
    )


class AdhocPrecommitTests(unittest.TestCase):
    def test_contract_snapshot_uses_live_config(self):
        contract = build_contract()
        self.assertEqual(contract["title_score_components"], list(TITLE_WEIGHTS))
        self.assertEqual(contract["content_id_pattern"], CONTENT_ID_RE.pattern)
        self.assertTrue(contract["media_readiness"]["required_before_adhoc"])
        self.assertEqual(contract["request_schema_version"], SCHEMA_VERSION)

    def test_known_good_pool_requires_five_of_five(self):
        result = validate(valid_pool())
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(result["commit_allowed"])
        self.assertEqual(result["valid_candidates"], 5)
        self.assertEqual(result["failed_candidates"], 0)
        self.assertTrue(result["draft_sha256"])

    def test_short_random_suffix_is_rejected_before_commit(self):
        pool = valid_pool()
        pool["ranked_candidates"][0]["request"]["content_id"] = (
            "wd-20260913T010000-adhoc-c01"
        )
        result = validate(pool)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["commit_allowed"])
        self.assertEqual(result["valid_candidates"], 4)
        errors = result["candidate_results"][0]["errors"]
        self.assertTrue(any("canonical pattern" in error for error in errors))

    def test_wrong_title_component_key_reports_exact_drift(self):
        pool = valid_pool()
        titles = pool["ranked_candidates"][0]["request"]["planning"]["title_candidates"]
        for title in titles:
            components = title["score_components"]
            value = components.pop("truthful_reflection")
            components["truthfulness"] = value

        result = validate(pool)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["commit_allowed"])
        self.assertEqual(result["valid_candidates"], 4)
        errors = result["candidate_results"][0]["errors"]
        joined = "\n".join(errors)
        self.assertIn("missing=['truthful_reflection']", joined)
        self.assertIn("unexpected=['truthfulness']", joined)

    def test_validation_does_not_mutate_ai_authored_pool(self):
        pool = valid_pool()
        original = copy.deepcopy(pool)
        validate(pool)
        self.assertEqual(pool, original)


if __name__ == "__main__":
    unittest.main()
