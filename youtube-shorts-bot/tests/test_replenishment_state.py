import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from media import pexels_discovery, pexels_registry, pexels_resilient_ingest
from media.media_readiness import MIN_SELECTABLE_ASSETS, REQUIRED_CATEGORY_MINIMUMS
from media.replenishment_state import (
    MAX_REPLENISH_ATTEMPTS,
    build_next_discovery_request,
    build_readiness_event,
    derive_session_state,
    find_compatible_session,
    validate_manifest_against_decisions,
    validate_readiness_event,
    validate_review_decision,
)


SESSION = "rs-20260914-adhoc-abcdef01"
SHA = "a" * 40


def invocation():
    return {
        "planner_invocation_id": "pi-20260914-adhoc-abcdef01",
        "planning_profile": "adhoc",
        "planning_mode": "manual_on_demand",
        "singapore_date": "2026-09-14",
        "initial_rules_source_sha": SHA,
    }


def readiness(cleaning=1):
    deficits = {category: 0 for category in REQUIRED_CATEGORY_MINIMUMS}
    deficits["cleaning"] = cleaning
    return {
        "status": "REPLENISH",
        "category_deficits": deficits,
        "required_new_assets_at_least": max(1, cleaning),
    }


def request(attempt=1, excluded=()):
    return build_next_discovery_request(
        readiness(), SESSION, invocation(), attempt, excluded
    )


def approved_candidate(provider_id="123"):
    return {
        "logical_id": f"satisfying-px-{provider_id}",
        "provider_asset_id": provider_id,
        "source_page": f"https://www.pexels.com/video/example-{provider_id}/",
        "title": "Visually reviewed pressure washing",
        "visual_tags": ["cleaning", "pressure-washing"],
        "motion_type": "continuous-process",
        "motion_intensity": "high",
        "loopability_score": 90,
        "visual_satisfaction_score": 92,
        "caption_readability_score": 91,
        "verified_preview": True,
        "required_by_content_ids": ["wd-test-content"],
        "reviewed_category": "cleaning",
    }


def decision(provider_id="123", result="approve", attempt=1):
    approved = approved_candidate(provider_id) if result == "approve" else None
    return {
        "schema_version": 2,
        "replenishment_session_id": SESSION,
        "planner_invocation": invocation(),
        "request_id": f"dr-{SESSION[3:]}-a{attempt:02d}",
        "attempt": attempt,
        "evidence": {
            "review_index_path": (
                "youtube-shorts-bot/content/background-sourcing/review-evidence/"
                f"dr-{SESSION[3:]}-a{attempt:02d}-run-123.json"
            ),
            "workflow_run_id": 123,
            "artifact_id": 456,
            "evidence_manifest_sha256": "b" * 64,
        },
        "reviewed_at": "2026-09-14T03:00:00+08:00",
        "decisions": [{
            "provider_asset_id": provider_id,
            "source_page": f"https://www.pexels.com/video/example-{provider_id}/",
            "discovery_category": "cleaning",
            "reviewed_category": "cleaning" if result == "approve" else "pov_movement",
            "category_match": result == "approve",
            "decision": result,
            "reason_code": "APPROVED" if result == "approve" else "SEMANTIC_CATEGORY_MISMATCH",
            "reason_summary": "Exact-source contact sheet reviewed.",
            "approved_candidate": approved,
        }],
    }


def result(provider_id="123", attempt=1):
    return {
        "request_id": f"dr-{SESSION[3:]}-a{attempt:02d}",
        "replenishment_session_id": SESSION,
        "candidates": [{
            "provider_asset_id": provider_id,
            "source_page": f"https://www.pexels.com/video/example-{provider_id}/",
            "discovery_category": "cleaning",
        }],
    }


def evidence(attempt=1):
    request_id = f"dr-{SESSION[3:]}-a{attempt:02d}"
    return {
        "request_id": request_id,
        "workflow_run_id": 123,
        "artifact_id": 456,
        "evidence_manifest_sha256": "b" * 64,
    }


def event(status="PASS", attempt=1):
    phase = "READY_TO_RESUME" if status == "PASS" else (
        "EXHAUSTED" if attempt == MAX_REPLENISH_ATTEMPTS else "NEED_DISCOVERY"
    )
    return {
        "schema_version": 1,
        "event_id": f"re-{SESSION[3:]}-a{attempt:02d}",
        "replenishment_session_id": SESSION,
        "planner_invocation": invocation(),
        "attempt": attempt,
        "discovery_request_id": f"dr-{SESSION[3:]}-a{attempt:02d}",
        "readiness_manifest_path": (
            "youtube-shorts-bot/content/background-sourcing/readiness/"
            f"{SESSION}-a{attempt:02d}.json"
        ),
        "ingest_summary": {"accepted_count": 1},
        "media_readiness": readiness(0) | {
            "status": status,
            "ready": status == "PASS",
        },
        "continuation_phase": phase,
        "recorded_at": "2026-09-14T03:10:00+08:00",
    }


def _ready_asset(number, category):
    return {
        "id": f"satisfying-existing-{number}",
        "type": "video",
        "title": f"Existing {category} process {number}",
        "source": "Pexels",
        "source_page": f"https://www.pexels.com/video/existing-{1000 + number}/",
        "direct_url": f"https://videos.pexels.com/existing-{number}.mp4",
        "provider_asset_id": str(1000 + number),
        "creator": "Tester",
        "license": "Pexels License",
        "commercial_use": True,
        "attribution_required": False,
        "verified": True,
        "status": "active",
        "orientation": "vertical",
        "retention_category": category,
        "visual_tags": [category, "continuous"],
        "motion_type": "continuous-process",
        "motion_intensity": "high",
        "loopability_score": 95,
        "visual_satisfaction_score": 95,
        "caption_readability_score": 95,
        "has_embedded_text": False,
        "has_watermark": False,
        "duration_seconds": 90.0,
        "renditions": [{
            "id": str(9000 + number),
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "file_type": "video/mp4",
            "direct_url": f"https://videos.pexels.com/existing-{number}.mp4",
        }],
    }


class ReplenishmentStateTests(unittest.TestCase):
    def test_targeted_request_carries_stable_invocation_deficits_and_exclusions(self):
        doc = request(excluded=["99", "123", "99"])
        self.assertEqual(doc["schema_version"], 3)
        self.assertEqual(doc["target_categories"], ["cleaning"])
        self.assertEqual(doc["category_deficits"]["cleaning"], 1)
        self.assertEqual(doc["exclude_provider_asset_ids"], ["99", "123"])
        self.assertEqual(doc["planner_invocation"], invocation())
        self.assertEqual(pexels_discovery._load_request_dict(doc), doc)

    def test_attempt_specific_query_strategies_materially_change(self):
        rounds = [
            pexels_discovery.queries_for_attempt("cleaning", value)
            for value in range(1, 6)
        ]
        self.assertEqual(len(set(rounds)), 5)
        self.assertTrue(
            all(rounds[index] != rounds[index + 1] for index in range(4))
        )

    def test_rejected_provider_is_excluded_and_session_needs_next_attempt(self):
        state = derive_session_state(
            SESSION,
            discovery_requests=[request()],
            discovery_results=[result()],
            review_evidence_indexes=[evidence()],
            review_decisions=[decision(result="reject")],
            active_provider_asset_ids=["777"],
        )
        self.assertEqual(state["continuation_phase"], "NEED_DISCOVERY")
        self.assertEqual(state["rejected_provider_asset_ids"], ["123"])
        self.assertEqual(state["excluded_provider_asset_ids"], ["123", "777"])

    def test_undecided_review_evidence_is_resumable_without_new_request(self):
        state = derive_session_state(
            SESSION,
            discovery_requests=[request()],
            discovery_results=[result()],
            review_evidence_indexes=[evidence()],
        )
        self.assertEqual(state["continuation_phase"], "NEEDS_VISUAL_REVIEW")
        self.assertEqual(state["attempt"], 1)

    def test_empty_completed_discovery_round_advances_instead_of_stopping(self):
        empty_result = result()
        empty_result["candidates"] = []
        state = derive_session_state(
            SESSION,
            discovery_requests=[request()],
            discovery_results=[empty_result],
            review_evidence_indexes=[evidence()],
        )
        self.assertEqual(state["continuation_phase"], "NEED_DISCOVERY")
        self.assertEqual(state["attempt"], 1)

    def test_later_execution_finds_unfinished_compatible_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            sourcing = tmp_path / "content" / "background-sourcing"
            requests = sourcing / "discovery-requests"
            requests.mkdir(parents=True)
            (requests / "attempt.json").write_text(
                json.dumps(request()), encoding="utf-8"
            )
            registry = tmp_path / "media-library" / "backgrounds.json"
            registry.parent.mkdir()
            registry.write_text(
                json.dumps({"schema_version": 3, "assets": []}),
                encoding="utf-8",
            )

            state = find_compatible_session(tmp_path, invocation())

            self.assertEqual(state["replenishment_session_id"], SESSION)
            self.assertEqual(state["continuation_phase"], "WAITING_DISCOVERY")

    def test_legacy_session_is_history_not_resumable_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            requests = (
                tmp_path / "content" / "background-sourcing" / "discovery-requests"
            )
            requests.mkdir(parents=True)
            legacy_request = {
                "schema_version": 2,
                "plan_date": "2026-09-14",
                "request_id": "dr-20260914-manual-library10-a03",
                "max_candidates": 48,
                "target_categories": ["cleaning"],
                "exclude_provider_asset_ids": [],
                "replenishment_session_id": "rs-20260914-manual-library10",
                "attempt": 3,
            }
            (requests / "legacy.json").write_text(
                json.dumps(legacy_request), encoding="utf-8"
            )
            registry = tmp_path / "media-library" / "backgrounds.json"
            registry.parent.mkdir()
            registry.write_text(
                json.dumps({"schema_version": 3, "assets": []}),
                encoding="utf-8",
            )

            self.assertIsNone(find_compatible_session(tmp_path, invocation()))

    def test_completed_session_resumes_original_planner_and_is_not_restarted(self):
        state = derive_session_state(
            SESSION,
            discovery_requests=[request()],
            readiness_events=[event("PASS")],
        )
        self.assertEqual(state["continuation_phase"], "READY_TO_RESUME")
        self.assertTrue(state["resume_original_planner"])
        self.assertEqual(state["planner_invocation"], invocation())

    def test_attempt_five_replenish_is_bounded_exhaustion_with_diagnostic(self):
        requests = [request(attempt=value) for value in range(1, 6)]
        state = derive_session_state(
            SESSION,
            discovery_requests=requests,
            readiness_events=[event("REPLENISH", 5)],
        )
        self.assertEqual(state["continuation_phase"], "EXHAUSTED")
        self.assertEqual(
            state["diagnostic"]["error_code"], "E_MEDIA_REPLENISH_EXHAUSTED"
        )
        self.assertEqual(state["diagnostic"]["attempt_count"], 5)

    def test_duplicate_immutable_review_decision_collision_fails(self):
        with self.assertRaisesRegex(
            ValueError, "[Dd]uplicate review decision collision"
        ):
            derive_session_state(
                SESSION,
                discovery_requests=[request()],
                discovery_results=[result()],
                review_evidence_indexes=[evidence()],
                review_decisions=[decision(), copy.deepcopy(decision())],
            )

    def test_category_mismatch_cannot_be_approved(self):
        doc = decision()
        doc["decisions"][0]["reviewed_category"] = "pov_movement"
        doc["decisions"][0]["category_match"] = False
        self.assertTrue(
            any(
                "approval requires APPROVED and a category match" in item
                for item in validate_review_decision(doc)
            )
        )

    def test_manifest_must_match_immutable_approved_decision(self):
        approved = decision()
        decision_id = f"rd-{approved['request_id'][3:]}-123"
        candidate = dict(
            approved["decisions"][0]["approved_candidate"],
            review_decision_id=decision_id,
        )
        manifest = {
            "schema_version": 2,
            "plan_date": "2026-09-14",
            "provider": "Pexels",
            "replenishment_session_id": SESSION,
            "planner_invocation": invocation(),
            "attempt": 1,
            "discovery_request_id": request()["request_id"],
            "review_decision_ids": [decision_id],
            "candidates": [candidate],
        }
        self.assertEqual(
            validate_manifest_against_decisions(manifest, [approved]), []
        )
        manifest["candidates"][0]["reviewed_category"] = "pov_movement"
        self.assertTrue(
            any(
                "metadata differs" in item
                for item in validate_manifest_against_decisions(
                    manifest, [approved]
                )
            )
        )

    def test_invalid_readiness_event_attempt_above_maximum_fails_closed(self):
        doc = event("REPLENISH", 5)
        doc["attempt"] = 6
        self.assertTrue(
            any(
                "attempt must be 1-5" in item
                for item in validate_readiness_event(doc)
            )
        )

    def test_acceptance_reject_then_approve_ingest_pass_and_resume_same_adhoc(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            categories = []
            for category, minimum in REQUIRED_CATEGORY_MINIMUMS.items():
                categories.extend(
                    [category]
                    * (minimum - (1 if category == "cleaning" else 0))
                )
            categories.extend(
                ["satisfying_process"]
                * (MIN_SELECTABLE_ASSETS - 1 - len(categories))
            )
            registry = {
                "schema_version": 3,
                "assets": [
                    _ready_asset(index, category)
                    for index, category in enumerate(categories, 1)
                ],
            }
            registry_path = tmp_path / "backgrounds.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            reject = decision("123", "reject", 1)
            approve = decision("456", "approve", 2)
            request1 = request(1)
            result1 = result("123", 1)
            state1 = derive_session_state(
                SESSION,
                discovery_requests=[request1],
                discovery_results=[result1],
                review_evidence_indexes=[evidence(1)],
                review_decisions=[reject],
            )
            self.assertEqual(state1["continuation_phase"], "NEED_DISCOVERY")
            request2 = build_next_discovery_request(
                readiness(),
                SESSION,
                invocation(),
                2,
                state1["excluded_provider_asset_ids"],
            )
            self.assertIn("123", request2["exclude_provider_asset_ids"])
            self.assertNotEqual(
                pexels_discovery.queries_for_attempt("cleaning", 1),
                pexels_discovery.queries_for_attempt("cleaning", 2),
            )

            decision_id = f"rd-{approve['request_id'][3:]}-456"
            candidate = dict(
                approve["decisions"][0]["approved_candidate"],
                review_decision_id=decision_id,
            )
            manifest = {
                "schema_version": 2,
                "plan_date": "2026-09-14",
                "provider": "Pexels",
                "replenishment_session_id": SESSION,
                "planner_invocation": invocation(),
                "attempt": 2,
                "discovery_request_id": request2["request_id"],
                "review_decision_ids": [decision_id],
                "candidates": [candidate],
            }
            manifest_path = tmp_path / "readiness.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            decisions_root = tmp_path / "decisions"
            decisions_root.mkdir(parents=True)
            (decisions_root / "approve.json").write_text(
                json.dumps(approve), encoding="utf-8"
            )
            video = {
                "id": 456,
                "width": 1080,
                "height": 1920,
                "duration": 90,
                "url": "https://www.pexels.com/video/example-456/",
                "user": {"name": "Tester"},
                "video_files": [{
                    "id": 4560,
                    "width": 1080,
                    "height": 1920,
                    "fps": 30,
                    "file_type": "video/mp4",
                    "quality": "hd",
                    "link": "https://videos.pexels.com/456.mp4",
                }],
            }
            with mock.patch.object(
                pexels_registry,
                "api_get",
                side_effect=lambda *args, **kwargs: video,
            ):
                ingest = pexels_resilient_ingest.ingest_resilient(
                    manifest_path,
                    registry_path,
                    review_decisions_root=decisions_root,
                )

            self.assertEqual(ingest["accepted_count"], 1)
            persisted = json.loads(registry_path.read_text(encoding="utf-8"))
            event_manifest = dict(
                manifest, readiness_manifest_path=str(manifest_path)
            )
            readiness_event = build_readiness_event(
                event_manifest,
                ingest,
                persisted,
                recorded_at="2026-09-14T03:10:00+08:00",
            )
            self.assertEqual(
                readiness_event["media_readiness"]["status"], "PASS"
            )
            state2 = derive_session_state(
                SESSION,
                discovery_requests=[request1, request2],
                discovery_results=[result1, result("456", 2)],
                review_evidence_indexes=[evidence(1), evidence(2)],
                review_decisions=[reject, approve],
                readiness_manifests=[manifest],
                readiness_events=[readiness_event],
            )
            self.assertEqual(
                state2["continuation_phase"], "READY_TO_RESUME"
            )
            self.assertTrue(state2["resume_original_planner"])
            self.assertEqual(state2["planner_invocation"], invocation())


if __name__ == "__main__":
    unittest.main()
