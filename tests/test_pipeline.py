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
        "narration": narration,
        "title": title,
        "description": "A small lie turns into a much bigger problem.",
        "lead_gender": "female",
        "story_tone": "natural",
        "payoff": "word",
        "emoji_cues": ["shock", "evidence", "panic", "victory"],
        "background_category": "crafting",
        "trend_aware": False,
        "trend_topic": None,
    }
    value.update(overrides)
    return value


def valid_narration():
    return " ".join(["word"] * 400)


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
        raw = {
            "winners": [
                winner("too short", title="First short story"),
                winner(valid_narration(), title="Valid story"),
                winner("also too short", title="Third short story"),
            ]
        }
        draft = p.normalize_draft(raw)
        violations = p.collect_draft_violations(draft)
        short = [v for v in violations if v["error_code"] == "NARRATION_TOO_SHORT"]

        self.assertEqual([v["winner_index"] for v in short], [0, 2])
        self.assertEqual(short[0]["winner_title"], "First short story")
        self.assertEqual(short[0]["field"], "winners[0].narration")
        self.assertEqual(short[1]["field"], "winners[2].narration")

    def test_valid_draft_has_no_creative_violations(self):
        draft = p.normalize_draft({"winners": [winner(valid_narration())]})
        self.assertEqual(p.collect_draft_violations(draft), [])

    def test_missing_text_and_long_title_are_reported_with_winner_index(self):
        draft = p.normalize_draft(
            {
                "winners": [
                    winner(valid_narration(), title="x" * 101, conflict=""),
                ]
            }
        )
        violations = p.collect_draft_violations(draft)
        by_code = {v["error_code"]: v for v in violations}

        self.assertEqual(by_code["MISSING_TEXT"]["field"], "winners[0].conflict")
        self.assertEqual(by_code["TITLE_TOO_LONG"]["field"], "winners[0].title")
        self.assertEqual(by_code["TITLE_TOO_LONG"]["observed_value"], 101)

    def test_trend_metadata_validation_reports_bad_combinations(self):
        raw = {
            "winners": [
                winner(valid_narration(), trend_aware=True, trend_topic=None),
                winner(valid_narration(), trend_aware=False, trend_topic="GTA 6"),
                winner(valid_narration(), trend_aware="true", trend_topic="GTA 6"),
            ]
        }
        violations = p.collect_draft_violations(p.normalize_draft(raw))
        by_index = {}
        for violation in violations:
            by_index.setdefault(violation["winner_index"], []).append(violation["error_code"])

        self.assertIn("TREND_TOPIC_REQUIRED", by_index[0])
        self.assertIn("TREND_TOPIC_FORBIDDEN", by_index[1])
        self.assertIn("INVALID_TREND_AWARE", by_index[2])

    def test_trend_metadata_propagates_and_legacy_request_remains_valid(self):
        draft = p.normalize_draft(
            {
                "winners": [
                    winner(
                        valid_narration(),
                        trend_aware=True,
                        trend_topic="GTA 6",
                    )
                ]
            }
        )
        with patch.object(p, "bg_contract", return_value=valid_background_contract()):
            item = p.make_item(
                "draft-testtrend01",
                0,
                draft["winners"][0],
                {},
                "2030-01-01T00:00:00Z",
            )

        self.assertTrue(item["story"]["trend_aware"])
        self.assertEqual(item["story"]["trend_topic"], "GTA 6")
        p.validate_item(item, None)

        legacy = json.loads(json.dumps(item))
        legacy["story"].pop("trend_aware")
        legacy["story"].pop("trend_topic")
        p.validate_item(legacy, None)

    def test_finalize_fails_before_youtube_slot_allocation_and_persists_all_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft_path = root / "draft-testaggregate01.json"
            failure_dir = root / "failures"
            draft_path.write_text(
                json.dumps(
                    {
                        "winners": [
                            winner("too short", title="First short story"),
                            winner("also too short", title="Second short story"),
                        ]
                    }
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


if __name__ == "__main__":
    unittest.main()
