import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media import pexels_discovery as discovery


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent


def _video(video_id, duration=90):
    return {
        "id": video_id,
        "duration": duration,
        "width": 1080,
        "height": 1920,
        "url": f"https://www.pexels.com/video/example-{video_id}/",
        "image": f"https://images.pexels.com/videos/{video_id}/preview.jpg",
        "user": {"name": "Tester"},
        "video_files": [
            {
                "id": video_id * 10,
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "file_type": "video/mp4",
                "quality": "hd",
                "link": f"https://videos.pexels.com/video-files/{video_id}/preview.mp4",
            }
        ],
    }


class ReplenishmentContinuationV2Tests(unittest.TestCase):
    def test_machine_contract_requires_bounded_durable_continuation(self):
        manifest = json.loads(
            (BOT_ROOT / "planning" / "PLANNER_MATERIALIZATION.json").read_text(
                encoding="utf-8"
            )
        )
        continuation = manifest["background_replenishment_continuation"]
        self.assertEqual(continuation["state"], "recoverable_intermediate")
        self.assertEqual(continuation["discovery_request_schema_version"], 2)
        self.assertEqual(continuation["review_decision_schema_version"], 1)
        self.assertEqual(
            continuation["session_identity_field"], "replenishment_session_id"
        )
        self.assertEqual(continuation["max_attempts"], 5)
        self.assertTrue(continuation["durable_review_exclusion"]["enabled"])
        self.assertEqual(
            continuation["terminal_exhausted_code"],
            "E_MEDIA_REPLENISH_EXHAUSTED",
        )

    def test_shared_prompt_does_not_stop_after_one_rejection(self):
        shared = (REPO_ROOT / "docs" / "private" / "PLANNER_PROMPT.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("review-decisions/<request_id>.json", shared)
        self.assertIn("authoritative session memory", shared)
        self.assertIn("automatically unions all provider IDs already reviewed", shared)
        self.assertIn("attempt < 5", shared)
        self.assertIn("E_MEDIA_REPLENISH_EXHAUSTED", shared)

    def test_same_session_reviewed_provider_is_excluded_without_request_memory(self):
        with tempfile.TemporaryDirectory() as temporary:
            decisions = Path(temporary)
            (decisions / "dr-old.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "replenishment_session_id": "rs-20260914-manual-0230",
                        "request_id": "dr-20260914-manual-0230-a02",
                        "attempt": 2,
                        "decisions": [
                            {
                                "provider_asset_id": "401",
                                "decision": "reject",
                                "discovery_category": "cleaning",
                                "reviewed_category": None,
                                "category_match": False,
                                "reason_code": "SEMANTIC_CATEGORY_MISMATCH",
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            request = {
                "schema_version": 2,
                "plan_date": "2026-09-14",
                "request_id": "dr-20260914-manual-0230-a03",
                "max_candidates": 3,
                "target_categories": ["cleaning"],
                "exclude_provider_asset_ids": [],
                "replenishment_session_id": "rs-20260914-manual-0230",
                "attempt": 3,
            }
            payload = {"videos": [_video(401), _video(402)]}
            with patch.object(discovery, "api_get", return_value=payload):
                report = discovery.build_report(
                    request,
                    key="test",
                    review_decisions_dir=decisions,
                )

        self.assertIn("401", report["durably_reviewed_provider_asset_ids"])
        self.assertIn("401", report["effective_excluded_provider_asset_ids"])
        self.assertEqual(
            [item["provider_asset_id"] for item in report["candidates"]],
            ["402"],
        )

    def test_review_memory_is_scoped_to_session(self):
        with tempfile.TemporaryDirectory() as temporary:
            decisions = Path(temporary)
            (decisions / "dr-old.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "replenishment_session_id": "rs-20260914-manual-0230",
                        "request_id": "dr-20260914-manual-0230-a02",
                        "attempt": 2,
                        "decisions": [
                            {
                                "provider_asset_id": "501",
                                "decision": "reject",
                                "discovery_category": "cleaning",
                                "reviewed_category": None,
                                "category_match": False,
                                "reason_code": "SEMANTIC_CATEGORY_MISMATCH",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                discovery._load_reviewed_provider_ids(
                    "rs-20260914-manual-0230", decisions
                ),
                {"501"},
            )
            self.assertEqual(
                discovery._load_reviewed_provider_ids(
                    "rs-20260914-manual-0999", decisions
                ),
                set(),
            )


if __name__ == "__main__":
    unittest.main()
