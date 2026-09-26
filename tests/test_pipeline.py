import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline as p


def winner(narration, title="A Valid Story Title", **overrides):
    value = {
        "premise": "A friend hides an embarrassing mistake.",
        "category": "friends",
        "conflict": "The mistake keeps causing problems.",
        "twist": "The narrator finds the receipts.",
        "hook": "My friend thought nobody would notice.",
        "hook_type": "discovery",
        "narration": narration,
        "title": title,
        "description": "A small lie turns into a much bigger problem.",
        "lead_gender": "female",
        "story_tone": "natural",
        "payoff": "word",
        "like_cta": "LIKE IF YOU SAW THAT COMING",
        "emoji_cues": ["shock", "evidence", "panic", "victory"],
        "background_category": "crafting",
        "trend_aware": False,
        "trend_topic": None,
    }
    value.update(overrides)
    return value


def valid_narration():
    return " ".join(["word"] * 280)


def draft_doc(*winners):
    return {"winner_count": len(winners), "winners": list(winners)}


def valid_background_contract():
    return {
        "mode": "concatenated_fit_to_short",
        "segments": [
            {
                "background_id": "a",
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": 60.0,
            },
            {
                "background_id": "b",
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": 60.0,
            },
            {
                "background_id": "c",
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": 60.0,
            },
        ],
    }


class DraftValidationTests(unittest.TestCase):
    def test_collects_multiple_short_winners_in_one_pass(self):
        raw = draft_doc(
                winner("too short", title="First short story"),
                winner(valid_narration(), title="Valid story"),
                winner("also too short", title="Third short story"),
        )
        draft = p.normalize_draft(raw)
        violations = p.collect_draft_violations(draft)
        short = [v for v in violations if v["error_code"] == "NARRATION_TOO_SHORT"]

        self.assertEqual([v["winner_index"] for v in short], [0, 2])
        self.assertEqual(short[0]["winner_title"], "First short story")
        self.assertEqual(short[0]["field"], "winners[0].narration")
        self.assertEqual(short[1]["field"], "winners[2].narration")

    def test_valid_draft_has_no_creative_violations(self):
        normalized = p.normalize_draft(draft_doc(winner(valid_narration())))
        self.assertEqual(p.collect_draft_violations(normalized), [])

    def test_missing_text_and_long_title_are_reported_with_winner_index(self):
        draft = p.normalize_draft(
            draft_doc(winner(valid_narration(), title="x" * 101, conflict=""))
        )
        violations = p.collect_draft_violations(draft)
        by_code = {v["error_code"]: v for v in violations}

        self.assertEqual(by_code["MISSING_TEXT"]["field"], "winners[0].conflict")
        self.assertEqual(by_code["TITLE_TOO_LONG"]["field"], "winners[0].title")
        self.assertEqual(by_code["TITLE_TOO_LONG"]["observed_value"], 101)

    def test_hook_type_validation_reports_invalid_value(self):
        raw = draft_doc(winner(valid_narration(), hook_type="mystery"))
        violations = p.collect_draft_violations(p.normalize_draft(raw))
        self.assertEqual(
            [v["error_code"] for v in violations if v["winner_index"] == 0],
            ["INVALID_HOOK_TYPE"],
        )

    def test_trend_metadata_validation_reports_bad_combinations(self):
        raw = draft_doc(
                winner(valid_narration(), trend_aware=True, trend_topic=None),
                winner(valid_narration(), trend_aware=False, trend_topic="GTA 6"),
                winner(valid_narration(), trend_aware="true", trend_topic="GTA 6"),
        )
        violations = p.collect_draft_violations(p.normalize_draft(raw))
        by_index = {}
        for violation in violations:
            by_index.setdefault(violation["winner_index"], []).append(violation["error_code"])

        self.assertIn("TREND_TOPIC_REQUIRED", by_index[0])
        self.assertIn("TREND_TOPIC_FORBIDDEN", by_index[1])
        self.assertIn("INVALID_TREND_AWARE", by_index[2])

    def test_hook_type_and_trend_metadata_propagate_and_legacy_request_remains_valid(self):
        normalized = p.normalize_draft(
            draft_doc(
                    winner(
                        valid_narration(),
                        hook_type="money_stakes",
                        trend_aware=True,
                        trend_topic="GTA 6",
                    )
            )
        )
        with patch.object(p, "bg_contract", return_value=valid_background_contract()):
            item = p.make_item(
                "draft-testtrend01",
                0,
                normalized["winners"][0],
                {},
                "2030-01-01T00:00:00Z",
            )

        self.assertEqual(item["story"]["hook_type"], "money_stakes")
        self.assertTrue(item["story"]["trend_aware"])
        self.assertEqual(item["story"]["trend_topic"], "GTA 6")
        self.assertEqual(item["story"]["like_cta"], "LIKE IF YOU SAW THAT COMING")
        p.validate_item(item, None)

        no_hook = json.loads(json.dumps(item))
        no_hook["story"].pop("hook_type")
        p.validate_item(no_hook, None)

        legacy = json.loads(json.dumps(item))
        legacy["story"].pop("hook_type")
        legacy["story"].pop("trend_aware")
        legacy["story"].pop("trend_topic")
        legacy["story"].pop("like_cta")
        p.validate_item(legacy, None)

    def test_finalize_fails_before_youtube_slot_allocation_and_persists_all_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft_path = root / "draft-testaggregate01.json"
            failure_dir = root / "failures"
            draft_path.write_text(
                json.dumps(
                    draft_doc(
                            winner("too short", title="First short story"),
                            winner("also too short", title="Second short story"),
                    )
                ),
                encoding="utf-8",
            )

            with patch.object(p, "FAILS", failure_dir), patch.object(
                p, "registry", return_value={"assets": []}
            ), patch.object(p, "allocate_publish_slots") as allocate:
                with self.assertRaises(p.DraftValidationError):
                    p.finalize(draft_path)

            allocate.assert_not_called()
            payload = json.loads(
                (failure_dir / "draft-testaggregate01.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["error_code"], "DRAFT_VALIDATION_FAILED")
            self.assertTrue(payload["repairable"])
            self.assertEqual(len(payload["violations"]), 2)
            self.assertEqual(
                [v["winner_index"] for v in payload["violations"]], [0, 1]
            )

    def test_ordinary_failure_payload_stays_backward_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            failure_dir = Path(tmp)
            error = p.VError(
                "YOUTUBE_AUTH_MISSING",
                "RUNTIME_AUTH_A",
                "missing",
                "configured YouTube OAuth credential",
                False,
            )
            with patch.object(p, "FAILS", failure_dir):
                p.fail("draft-testordinary01", error)

            payload = json.loads(
                (failure_dir / "draft-testordinary01.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("violations", payload)
            self.assertEqual(payload["field"], "RUNTIME_AUTH_A")
            self.assertFalse(payload["repairable"])


class PlannerAnalyticsContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.history = self.root / "history.json"
        self.backgrounds = self.root / "backgrounds.json"
        self.context = self.root / "context.json"
        self.analytics = self.root / "planner-analytics.json"
        self.history.write_text("[]", encoding="utf-8")
        self.backgrounds.write_text(
            json.dumps(
                {
                    "assets": [
                        {
                            "id": f"bg-{index}",
                            "category": "crafting",
                            "source_url": f"https://www.pexels.com/video/{index}",
                            "download_url": f"https://videos.pexels.com/video-{index}.mp4",
                            "duration_seconds": 60,
                        }
                        for index in range(3)
                    ]
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def build(self):
        with patch.object(p, "HIST", self.history), patch.object(
            p, "BG", self.backgrounds
        ), patch.object(p, "CTX", self.context), patch.object(
            p, "PLANNER_ANALYTICS", self.analytics
        ):
            return p.build_context()

    @staticmethod
    def projection():
        return {
            "analytics_version": 3,
            "generated_at": "2026-09-01T00:00:00Z",
            "learning": {
                "stage": "early_learning",
                "analytics_weight": "medium",
                "minimum_pattern_sample": 8,
            },
            "creative_signals": {"supported_patterns": [], "weak_patterns": []},
            "distribution_signals": {
                "strong_publish_windows_sgt": [],
                "weak_publish_windows_sgt": [],
            },
            "audience_signals": {
                "dominant_countries": [],
                "dominant_traffic_sources": [],
            },
        }

    def test_context_builds_without_analytics_file(self):
        result = self.build()
        self.assertNotIn("analytics_summary", result)
        self.assertEqual(result["context_version"], 3)

    def test_context_embeds_valid_projection_unchanged_even_when_stale(self):
        projection = self.projection()
        self.analytics.write_text(json.dumps(projection), encoding="utf-8")
        result = self.build()
        self.assertEqual(result["analytics_summary"], projection)

    def test_malformed_projection_is_non_blocking(self):
        self.analytics.write_text("{not-json", encoding="utf-8")
        result = self.build()
        self.assertNotIn("analytics_summary", result)

    def test_raw_shaped_projection_is_rejected(self):
        projection = self.projection()
        projection["videos"] = [{"youtube_video_id": "secret-raw-row"}]
        self.analytics.write_text(json.dumps(projection), encoding="utf-8")
        result = self.build()
        self.assertNotIn("analytics_summary", result)
        self.assertNotIn("secret-raw-row", self.context.read_text(encoding="utf-8"))

    def test_oversized_projection_is_rejected(self):
        projection = self.projection()
        projection["warnings"] = ["x" * 20000]
        self.analytics.write_text(json.dumps(projection), encoding="utf-8")
        result = self.build()
        self.assertNotIn("analytics_summary", result)


if __name__ == "__main__":
    unittest.main()
