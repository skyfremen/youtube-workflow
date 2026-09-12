import copy
import json
import unittest
from pathlib import Path

from common.workflow_common import CONTENT_ID_RE
from media.media_readiness import REQUIRED_CATEGORY_MINIMUMS
from media.validate_media_library import load_registry
from planning import daily_precommit, ranked_promotion
from planning.planner_contract import DAILY_PUBLICATION, build_contract
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
PLAN_DATE = "2099-01-01"


def valid_pool():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    template = fixture["ranked_candidates"][0]["request"]
    ranked = []
    for index in range(1, ranked_promotion.DAILY_POOL_SIZE + 1):
        request = copy.deepcopy(template)
        request["content_id"] = f"wd-20990101T000000-daily-c{index:05d}"
        request["publication"] = copy.deepcopy(DAILY_PUBLICATION)
        request["planning"]["plan_date"] = PLAN_DATE
        ranked.append({
            "rank": index,
            "candidate_id": f"daily-c{index:02d}",
            "request": request,
        })
    return {
        "schema_version": ranked_promotion.POOL_SCHEMA_VERSION,
        "pool_type": "daily",
        "pool_id": "dp-20990101-a01",
        "plan_date": PLAN_DATE,
        "planning_mode": "normal_next_day",
        "target_count": ranked_promotion.NORMAL_DAILY_TARGET,
        "publication_slots": ranked_promotion._canonical_normal_slots(PLAN_DATE),
        "planning_execution": {
            "editorial_selection_owner": "chatgpt",
            "planning_method": "chatgpt_ranked_pool",
            "rules_source_sha": RULES_SHA,
            "ranked_candidate_ids": [f"daily-c{index:02d}" for index in range(1, 37)],
        },
        "ranked_candidates": ranked,
    }


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
    return daily_precommit.validate_draft(
        pool,
        RULES_SHA,
        raw_bytes=raw,
        registry=ready_registry(),
        check_checkout_head=False,
        check_uniqueness=False,
    )


class DailyPrecommitTests(unittest.TestCase):
    def test_contract_snapshot_uses_live_daily_config(self):
        contract = build_contract()
        self.assertEqual(contract["title_score_components"], list(TITLE_WEIGHTS))
        self.assertEqual(contract["content_id_pattern"], CONTENT_ID_RE.pattern)
        self.assertEqual(contract["daily_pool_size"], ranked_promotion.DAILY_POOL_SIZE)
        self.assertEqual(contract["daily_normal_target"], ranked_promotion.NORMAL_DAILY_TARGET)
        self.assertEqual(contract["daily_publication_template"], DAILY_PUBLICATION)
        self.assertTrue(contract["media_readiness"]["required_before_daily"])

    def test_known_good_pool_requires_thirty_six_of_thirty_six(self):
        result = validate(valid_pool())
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(result["commit_allowed"])
        self.assertEqual(result["valid_candidates"], 36)
        self.assertEqual(result["failed_candidates"], 0)
        self.assertTrue(result["draft_sha256"])

    def test_short_random_suffix_is_rejected_before_commit(self):
        pool = valid_pool()
        pool["ranked_candidates"][0]["request"]["content_id"] = (
            "wd-20990101T000000-daily-c01"
        )
        result = validate(pool)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["commit_allowed"])
        self.assertEqual(result["valid_candidates"], 35)
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
        self.assertEqual(result["valid_candidates"], 35)
        joined = "\n".join(result["candidate_results"][0]["errors"])
        self.assertIn("missing=['truthful_reflection']", joined)
        self.assertIn("unexpected=['truthfulness']", joined)

    def test_validation_does_not_mutate_ai_authored_pool(self):
        pool = valid_pool()
        original = copy.deepcopy(pool)
        validate(pool)
        self.assertEqual(pool, original)

    def test_daily_prompt_requires_executable_precommit_gate(self):
        prompt = (BOT_ROOT / "planning" / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("planning.daily_precommit", prompt)
        self.assertIn("36/36", prompt)
        self.assertIn("draft_sha256", prompt)
        self.assertIn("Do not substitute", prompt)
        self.assertIn("media.media_readiness", prompt)


if __name__ == "__main__":
    unittest.main()
