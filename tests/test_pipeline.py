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
    return " ".join(["word"] * 220)


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

    def test_finalize_reuses_identical_immutable_request_without_reallocating_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft_path = root / "draft-testidempotent01.json"
            requests = root / "requests"
            failures = root / "failures"
            draft_path.write_text(
                json.dumps(draft_doc(winner(valid_narration()))), encoding="utf-8"
            )
            registry = {
                "assets": [
                    {
                        "id": name,
                        "category": "crafting",
                        "source_url": f"https://www.pexels.com/video/{name}",
                        "download_url": f"https://videos.pexels.com/{name}.mp4",
                        "duration_seconds": 60,
                    }
                    for name in ("a", "b", "c")
                ]
            }

            with patch.object(p, "REQS", requests), patch.object(
                p, "FAILS", failures
            ), patch.object(p, "registry", return_value=registry), patch.object(
                p, "allocate_publish_slots", return_value=["2030-01-01T00:00:00Z"]
            ):
                first = p.finalize(draft_path)

            with patch.object(p, "REQS", requests), patch.object(
                p, "FAILS", failures
            ), patch.object(p, "registry", return_value=registry), patch.object(
                p,
                "allocate_publish_slots",
                side_effect=AssertionError("existing request must not reallocate slots"),
            ) as allocate:
                second = p.finalize(draft_path)

            self.assertEqual(first, second)
            allocate.assert_not_called()


class PublicationSlotTests(unittest.TestCase):
    @staticmethod
    def write_reserved_item(root, content_id, publish_at):
        requests = root / "requests"
        requests.mkdir()
        (requests / "rq-test.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "content_id": content_id,
                            "publication": {"publish_at": publish_at},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return requests

    def test_upload_limit_abandonment_releases_request_only_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_id = "wd-" + "a" * 24
            request_id = "rq-" + "b" * 24
            publish_at = "2030-01-01T00:00:00Z"
            requests = root / "requests"
            requests.mkdir()
            (requests / (request_id + ".json")).write_text(
                json.dumps(
                    {
                        "request_version": 2,
                        "request_id": request_id,
                        "source_draft_id": "draft-test",
                        "items": [
                            {
                                "content_id": content_id,
                                "publication": {"publish_at": publish_at},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            abandonments = root / "abandonments"
            abandonments.mkdir()
            (abandonments / f"{content_id}.json").write_text(
                json.dumps(
                    {
                        "abandonment_version": 1,
                        "content_id": content_id,
                        "request_id": request_id,
                        "reason": "upload_limit_abandoned",
                    }
                ),
                encoding="utf-8",
            )
            results = root / "results"
            results.mkdir()
            executions = root / "executions"
            (executions / "evidence").mkdir(parents=True)

            with patch.object(p, "ABANDONMENTS", abandonments, create=True), patch.object(
                p, "RESULTS", results, create=True
            ), patch.object(p, "EXECS", executions, create=True):
                occupied = p.request_publish_slots(requests)

            self.assertEqual(occupied, set())

    def test_completed_explicit_cancellation_releases_local_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_id = "wd-" + "a" * 24
            video_id = "abcdefghijk"
            publish_at = "2030-01-01T00:00:00Z"
            requests = self.write_reserved_item(root, content_id, publish_at)
            results = root / "results"
            results.mkdir()
            (results / f"{content_id}.json").write_text(
                json.dumps(
                    {
                        "result_version": 2,
                        "content_id": content_id,
                        "execution_id": "ex-" + "b" * 24,
                        "status": "scheduled",
                        "youtube_video_id": video_id,
                        "visibility": "private",
                        "verified": True,
                        "publish_at": publish_at,
                    }
                ),
                encoding="utf-8",
            )
            cancellations = root / "slot-cancellations"
            cancellations.mkdir()
            (cancellations / f"{content_id}.json").write_text(
                json.dumps(
                    {
                        "cancellation_version": 1,
                        "content_id": content_id,
                        "youtube_video_id": video_id,
                        "reason": "deleted_from_youtube",
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(p, "CANCELLATIONS", cancellations, create=True), patch.object(
                p, "RESULTS", results, create=True
            ):
                occupied = p.request_publish_slots(requests)

            self.assertEqual(occupied, set())

    def test_cancellation_without_completed_result_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_id = "wd-" + "a" * 24
            requests = self.write_reserved_item(
                root, content_id, "2030-01-01T00:00:00Z"
            )
            results = root / "results"
            results.mkdir()
            cancellations = root / "slot-cancellations"
            cancellations.mkdir()
            (cancellations / f"{content_id}.json").write_text(
                json.dumps(
                    {
                        "cancellation_version": 1,
                        "content_id": content_id,
                        "youtube_video_id": "abcdefghijk",
                        "reason": "deleted_from_youtube",
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(p, "CANCELLATIONS", cancellations, create=True), patch.object(
                p, "RESULTS", results, create=True
            ), self.assertRaisesRegex(p.VError, "CANCELLATION_RESULT_MISSING"):
                p.request_publish_slots(requests)

    def test_cancellation_video_id_must_match_completed_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_id = "wd-" + "a" * 24
            publish_at = "2030-01-01T00:00:00Z"
            requests = self.write_reserved_item(root, content_id, publish_at)
            results = root / "results"
            results.mkdir()
            (results / f"{content_id}.json").write_text(
                json.dumps(
                    {
                        "result_version": 2,
                        "content_id": content_id,
                        "execution_id": "ex-" + "b" * 24,
                        "status": "scheduled",
                        "youtube_video_id": "abcdefghijk",
                        "visibility": "private",
                        "verified": True,
                        "publish_at": publish_at,
                    }
                ),
                encoding="utf-8",
            )
            cancellations = root / "slot-cancellations"
            cancellations.mkdir()
            (cancellations / f"{content_id}.json").write_text(
                json.dumps(
                    {
                        "cancellation_version": 1,
                        "content_id": content_id,
                        "youtube_video_id": "zzzzzzzzzzz",
                        "reason": "deleted_from_youtube",
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(p, "CANCELLATIONS", cancellations, create=True), patch.object(
                p, "RESULTS", results, create=True
            ), self.assertRaisesRegex(p.VError, "CANCELLATION_RESULT_MISMATCH"):
                p.request_publish_slots(requests)

    def test_remote_and_finalized_request_slots_are_both_reserved(self):
        now = p.datetime(2030, 1, 1, 7, 50, tzinfo=p.SGT)
        remote = {p.datetime(2030, 1, 1, 1, 0, tzinfo=p.timezone.utc)}
        finalized = {p.datetime(2030, 1, 1, 4, 0, tzinfo=p.timezone.utc)}

        with patch.object(p, "youtube_scheduled_slots", return_value=remote), patch.object(
            p, "request_publish_slots", return_value=finalized, create=True
        ):
            slots = p.allocate_publish_slots(1, now)

        self.assertEqual(slots, ["2030-01-01T07:00:00Z"])

    def test_finalize_workflow_serializes_slot_allocation_from_latest_main(self):
        workflow = (p.ROOT / ".github" / "workflows" / "finalize-draft.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("group: finalize-state-${{ github.ref }}", workflow)
        self.assertIn("git reset --hard origin/main", workflow)

    def test_context_workflow_enforces_unit_regressions(self):
        workflow = (p.ROOT / ".github" / "workflows" / "context.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("'tests/test_pipeline.py'", workflow)
        self.assertIn("python -m unittest discover -s tests", workflow)


class ResultRelationshipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cid = "wd-" + "a" * 24
        self.rid = "rq-" + "b" * 24
        self.eid = "ex-" + "c" * 24
        self.publish_at = "2030-01-01T00:00:00Z"
        self.video_id = "abcdefghijk"
        self.item = {
            "content_id": self.cid,
            "publication": {"publish_at": self.publish_at},
            "story": {
                "premise": "Premise",
                "category": "friends",
                "conflict": "Conflict",
                "twist": "Twist",
                "punchline": "Payoff",
            },
            "youtube": {"title": "Title"},
        }
        self.batch = {"request_version": 2, "request_id": self.rid, "items": [self.item]}
        request_path = self.root / "content/requests" / f"{self.rid}.json"
        request_path.parent.mkdir(parents=True)
        request_path.write_bytes(p.pretty(self.batch))
        self.execution = {
            "execution_version": 2,
            "execution_id": self.eid,
            "request_id": self.rid,
            "content_id": self.cid,
            "request_path": f"content/requests/{self.rid}.json",
            "request_source_sha": "d" * 40,
            "request_blob_sha": p.blob(request_path.read_bytes()),
            "item_blob_sha": p.blob(p.pretty(self.item)),
            "state": "prepared",
        }
        executions = self.root / "content/executions"
        executions.mkdir(parents=True)
        (executions / f"{self.eid}.json").write_bytes(p.pretty(self.execution))
        self.evidence_dir = executions / "evidence" / self.cid
        self.evidence_dir.mkdir(parents=True)
        self.result_path = self.root / f"{self.cid}.json"
        self.history = self.root / "data/history.json"
        self.history.parent.mkdir(parents=True)
        self.history.write_text("[]", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def write_upload(self, version=2, video_id=None, *, conflicting_intent=False):
        if version == 2:
            identity = {
                key: self.execution[key]
                for key in (
                    "execution_id",
                    "content_id",
                    "request_id",
                    "request_path",
                    "request_source_sha",
                    "request_blob_sha",
                    "item_blob_sha",
                )
            }
        else:
            identity = {
                "content_id": self.cid,
                "request_path": f"content/requests/{self.cid}.json",
                "request_blob_sha": self.execution["item_blob_sha"],
                "source_commit_sha": self.execution["request_source_sha"],
            }
        shared = {
            "expected_channel_id": "channel",
            "upload_body": {"status": {"privacyStatus": "private"}},
        }
        if version == 2:
            intent = {
                "evidence_version": 2,
                "record_type": "intent",
                **identity,
                **shared,
            }
            if conflicting_intent:
                intent["expected_channel_id"] = "different-channel"
            (self.evidence_dir / "intent.json").write_bytes(p.pretty(intent))
        upload = {
            "evidence_version": version,
            "record_type": "upload",
            **identity,
            **shared,
            "youtube_video_id": video_id or self.video_id,
        }
        (self.evidence_dir / "upload.json").write_bytes(p.pretty(upload))

    def write_result(self, *, publish_at=None, video_id=None):
        result = {
            "result_version": 2,
            "content_id": self.cid,
            "execution_id": self.eid,
            "status": "scheduled",
            "youtube_video_id": video_id or self.video_id,
            "visibility": "private",
            "verified": True,
            "publish_at": publish_at or self.publish_at,
        }
        self.result_path.write_bytes(p.pretty(result))

    def ingest(self):
        with patch.object(p, "ROOT", self.root), patch.object(
            p, "EXECS", self.root / "content/executions"
        ), patch.object(p, "HIST", self.history), patch.object(
            p, "validate_batch", return_value=self.batch
        ), patch.object(p, "build_context"):
            p.ingest(self.result_path)

    def test_ingest_rejects_publish_time_mismatch(self):
        self.write_upload()
        self.write_result(publish_at="2030-01-01T00:10:00Z")
        with self.assertRaisesRegex(p.VError, "RESULT_PUBLISH_AT_MISMATCH"):
            self.ingest()

    def test_ingest_rejects_video_id_mismatch(self):
        self.write_upload(video_id="zzzzzzzzzzz")
        self.write_result()
        with self.assertRaisesRegex(p.VError, "RESULT_UPLOAD_MISMATCH"):
            self.ingest()

    def test_ingest_accepts_complete_v2_evidence(self):
        self.write_upload(version=2)
        self.write_result()
        self.ingest()
        self.assertEqual(self.cid, json.loads(self.history.read_text())[0]["content_id"])

    def test_ingest_accepts_exact_legacy_v1_alias(self):
        self.write_upload(version=1)
        self.write_result()
        self.ingest()
        self.assertEqual(self.cid, json.loads(self.history.read_text())[0]["content_id"])

    def test_ingest_rejects_conflicting_v2_intent_and_upload(self):
        self.write_upload(version=2, conflicting_intent=True)
        self.write_result()
        with self.assertRaisesRegex(p.VError, "EVIDENCE_RELATIONSHIP_MISMATCH"):
            self.ingest()

    def test_ingest_rejects_malformed_v2_intent(self):
        self.write_upload(version=2)
        (self.evidence_dir / "intent.json").write_text("{", encoding="utf-8")
        self.write_result()
        with self.assertRaisesRegex(p.VError, "INTENT_EVIDENCE_INVALID"):
            self.ingest()


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
