import copy
import json
import unittest
from pathlib import Path

from common.workflow_common import CONTENT_ID_RE
from media.media_readiness import REQUIRED_CATEGORY_MINIMUMS
from media.validate_media_library import load_registry
from planning import adhoc_precommit
from planning.planner_contract import build_contract
from planning.planning_config import TITLE_WEIGHTS


BOT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    BOT_ROOT
    / "content"
    / "planning-pools"
    / "adhoc"
    / "ap-20260913-scheduled-a04.json"
)
RULES_SHA = "1" * 40


def valid_pool():
    pool = json.loads(FIXTURE.read_text(encoding="utf-8"))
    pool["planning_execution"]["rules_source_sha"] = RULES_SHA
    return pool


def ready_registry():
    registry = copy.deepcopy(load_registry())
    counter = 0
    for category, minimum in REQUIRED_CATEGORY_MINIMUMS.items():
        for _ in range(minimum):
            counter += 1
            registry["assets"].append({
                "id": f"test-ready-{counter:03d}",
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
                "renditions": [{
                    "id": f"test-r-{counter:03d}",
                    "width": 1080,
                    "height": 1920,
                    "fps": 30.0,
                    "file_type": "video/mp4",
                    "direct_url": f"https://videos.pexels.com/test-{counter:03d}.mp4",
                }],
            })
    return registry


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

    def test_known_good_pool_requires_five_of_five(self):
        result = validate(valid_pool())
        self.assertEqual(result["status"], "PASS")
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
