"""Immutable, resumable background-replenishment state for both planners.

The files validated here are deterministic transport/state.  ChatGPT/Work creates
visual decisions after inspecting exact-source evidence; this module never infers
semantic suitability.  Current state is derived from append-only discovery
requests, review decisions, readiness manifests, and post-ingestion readiness
events so an interrupted planner can resume the same logical invocation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from media.background_selector_base import HIGH_RETENTION_CATEGORIES
from media.media_readiness import REQUIRED_CATEGORY_MINIMUMS, audit_registry


MAX_REPLENISH_ATTEMPTS = 5
LEGACY_REVIEW_DECISION_SCHEMA_VERSION = 1
REVIEW_DECISION_SCHEMA_VERSION = 2
READINESS_EVENT_SCHEMA_VERSION = 1
DISCOVERY_REQUEST_SCHEMA_VERSION = 3
SOURCE_MANIFEST_SCHEMA_VERSION = 2
REVIEW_DECISION_REASON_CODES = {
    "APPROVED",
    "SEMANTIC_CATEGORY_MISMATCH",
    "VISUAL_QUALITY_TOO_LOW",
    "CAPTION_READABILITY_TOO_LOW",
    "STATIC_OR_LOW_MOTION",
    "WATERMARK",
    "EMBEDDED_TEXT",
    "UNSAFE_CONTENT",
    "INSUFFICIENT_VISUAL_EVIDENCE",
    "OTHER_VISUAL_REJECTION",
}
REPLENISHMENT_ROOT = Path(__file__).resolve().parents[1] / "content" / "background-sourcing"
DECISIONS_ROOT = REPLENISHMENT_ROOT / "review-decisions"
EVENTS_ROOT = REPLENISHMENT_ROOT / "replenishment-events"
DISCOVERY_CATEGORIES = tuple(REQUIRED_CATEGORY_MINIMUMS)

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{7,96}")
_SHA_RE = re.compile(r"[0-9a-f]{40}")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_PEXELS_PAGE_RE = re.compile(r"https://(?:www\.)?pexels\.com/video/.+")


def _exact_fields(data, expected, label):
    if not isinstance(data, dict) or set(data) != set(expected):
        return [f"{label} must contain exactly {', '.join(sorted(expected))}"]
    return []


def _valid_timestamp(value):
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return True
    except (TypeError, ValueError):
        return False


def validate_planner_invocation(data):
    errors = _exact_fields(
        data,
        {
            "planner_invocation_id",
            "planning_profile",
            "planning_mode",
            "singapore_date",
            "initial_rules_source_sha",
        },
        "planner_invocation",
    )
    if errors:
        return errors
    if not re.fullmatch(r"pi-[A-Za-z0-9-]{8,96}", str(data["planner_invocation_id"])):
        errors.append("planner_invocation_id must match pi-[A-Za-z0-9-]{8,96}")
    if data["planning_profile"] not in {"daily", "adhoc"}:
        errors.append("planning_profile must be daily or adhoc")
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", str(data["planning_mode"])):
        errors.append("planning_mode must be a lowercase controlled value")
    if not _DATE_RE.fullmatch(str(data["singapore_date"])):
        errors.append("singapore_date must be YYYY-MM-DD")
    if not _SHA_RE.fullmatch(str(data["initial_rules_source_sha"])):
        errors.append("initial_rules_source_sha must be a lowercase 40-character SHA")
    return errors


def _validate_evidence(data):
    errors = _exact_fields(
        data,
        {
            "review_index_path",
            "workflow_run_id",
            "artifact_id",
            "evidence_manifest_sha256",
        },
        "evidence",
    )
    if errors:
        return errors
    if not re.fullmatch(
        r"youtube-shorts-bot/content/background-sourcing/review-evidence/[A-Za-z0-9._/-]+\.json",
        str(data["review_index_path"]),
    ):
        errors.append("evidence.review_index_path is invalid")
    for field in ("workflow_run_id", "artifact_id"):
        value = data[field]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"evidence.{field} must be a positive integer")
    if not re.fullmatch(r"[0-9a-f]{64}", str(data["evidence_manifest_sha256"])):
        errors.append("evidence.evidence_manifest_sha256 must be a SHA-256 digest")
    return errors


def _validate_approved_candidate(data, provider_id, source_page, reviewed_category):
    expected = {
        "logical_id",
        "provider_asset_id",
        "source_page",
        "title",
        "visual_tags",
        "motion_type",
        "motion_intensity",
        "loopability_score",
        "visual_satisfaction_score",
        "caption_readability_score",
        "verified_preview",
        "required_by_content_ids",
        "reviewed_category",
    }
    errors = _exact_fields(data, expected, "approved_candidate")
    if errors:
        return errors
    if str(data["provider_asset_id"]) != provider_id:
        errors.append("approved_candidate.provider_asset_id must match the decision")
    if data["logical_id"] != f"satisfying-px-{provider_id}":
        errors.append("approved_candidate.logical_id must be deterministic")
    if data["source_page"] != source_page:
        errors.append("approved_candidate.source_page must match the reviewed source")
    if data["reviewed_category"] != reviewed_category:
        errors.append("approved_candidate.reviewed_category must match the decision")
    if data["verified_preview"] is not True:
        errors.append("approved_candidate.verified_preview must be true")
    if not isinstance(data["visual_tags"], list) or not data["visual_tags"]:
        errors.append("approved_candidate.visual_tags must be non-empty")
    if data["motion_intensity"] not in {"low", "medium", "high"}:
        errors.append("approved_candidate.motion_intensity is invalid")
    for field in (
        "loopability_score",
        "visual_satisfaction_score",
        "caption_readability_score",
    ):
        value = data[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
            errors.append(f"approved_candidate.{field} must be between 0 and 100")
    required_by = data["required_by_content_ids"]
    if not isinstance(required_by, list) or not required_by or any(not str(x).strip() for x in required_by):
        errors.append("approved_candidate.required_by_content_ids must be non-empty")
    return errors


def _decision_id(request_id, provider_id):
    return f"rd-{str(request_id)[3:]}-{provider_id}"


def validate_review_decision(data):
    """Validate one immutable per-attempt review document.

    Schema v1 remains readable because it is already immutable repository history.
    New schema-v2 documents bind the same batch shape to the frozen planner
    invocation and exact review-evidence index, and carry ingestion metadata only
    for visually approved category matches.
    """
    version = data.get("schema_version") if isinstance(data, dict) else None
    common = {"schema_version", "replenishment_session_id", "request_id", "attempt", "decisions"}
    expected = common if version == LEGACY_REVIEW_DECISION_SCHEMA_VERSION else common | {
        "planner_invocation", "evidence", "reviewed_at"
    }
    errors = _exact_fields(data, expected, "review decision document")
    if errors:
        return errors
    if version not in {LEGACY_REVIEW_DECISION_SCHEMA_VERSION, REVIEW_DECISION_SCHEMA_VERSION}:
        return ["review decision schema_version must be 1 or 2"]
    if not re.fullmatch(r"rs-[A-Za-z0-9-]{8,96}", str(data["replenishment_session_id"])):
        errors.append("replenishment_session_id is invalid")
    if not re.fullmatch(r"dr-[A-Za-z0-9-]{8,96}", str(data["request_id"])):
        errors.append("request_id is invalid")
    attempt = data["attempt"]
    if isinstance(attempt, bool) or not isinstance(attempt, int) or not 1 <= attempt <= MAX_REPLENISH_ATTEMPTS:
        errors.append(f"attempt must be 1-{MAX_REPLENISH_ATTEMPTS}")
    if version == REVIEW_DECISION_SCHEMA_VERSION:
        errors.extend(validate_planner_invocation(data["planner_invocation"]))
        errors.extend(_validate_evidence(data["evidence"]))
        if not _valid_timestamp(data["reviewed_at"]):
            errors.append("reviewed_at must be an ISO-8601 timestamp")

    decisions = data["decisions"]
    if not isinstance(decisions, list) or not decisions:
        errors.append("decisions must be a non-empty list")
        return errors
    legacy_fields = {
        "provider_asset_id", "decision", "discovery_category", "reviewed_category",
        "category_match", "reason_code",
    }
    current_fields = legacy_fields | {"source_page", "reason_summary", "approved_candidate"}
    seen = set()
    valid_categories = HIGH_RETENTION_CATEGORIES - {"licensed_gameplay"}
    for index, decision in enumerate(decisions):
        label = f"decision {index}"
        item_errors = _exact_fields(
            decision,
            legacy_fields if version == LEGACY_REVIEW_DECISION_SCHEMA_VERSION else current_fields,
            label,
        )
        if item_errors:
            errors.extend(item_errors)
            continue
        provider_id = str(decision["provider_asset_id"])
        if not provider_id.isdigit():
            errors.append(f"{label}: provider_asset_id must be numeric")
        if provider_id in seen:
            errors.append(f"{label}: duplicate provider_asset_id")
        seen.add(provider_id)
        discovery_category = decision["discovery_category"]
        reviewed_category = decision["reviewed_category"]
        if discovery_category not in valid_categories:
            errors.append(f"{label}: discovery_category is invalid")
        if reviewed_category is not None and reviewed_category not in valid_categories:
            errors.append(f"{label}: reviewed_category is invalid")
        if not isinstance(decision["category_match"], bool):
            errors.append(f"{label}: category_match must be boolean")
        elif decision["category_match"] != (reviewed_category == discovery_category):
            errors.append(f"{label}: category_match must equal reviewed_category == discovery_category")
        if decision["decision"] not in {"approve", "reject"}:
            errors.append(f"{label}: decision must be approve or reject")
        if decision["reason_code"] not in REVIEW_DECISION_REASON_CODES:
            errors.append(f"{label}: reason_code is invalid")

        if version == LEGACY_REVIEW_DECISION_SCHEMA_VERSION:
            if decision["decision"] == "approve" and (
                decision["category_match"] is not True
                or reviewed_category != discovery_category
                or decision["reason_code"] != "APPROVED"
            ):
                errors.append(f"{label}: approved candidate must be a confirmed category match")
            continue

        source_page = str(decision["source_page"])
        if not _PEXELS_PAGE_RE.fullmatch(source_page):
            errors.append(f"{label}: source_page must be a Pexels video page")
        if not str(decision["reason_summary"]).strip() or len(str(decision["reason_summary"])) > 500:
            errors.append(f"{label}: reason_summary must contain 1-500 characters")
        if decision["decision"] == "approve":
            if decision["reason_code"] != "APPROVED" or decision["category_match"] is not True:
                errors.append(f"{label}: approval requires APPROVED and a category match")
            if decision["approved_candidate"] is None:
                errors.append(f"{label}: approval requires approved_candidate metadata")
            else:
                errors.extend(
                    f"{label}: {item}" for item in _validate_approved_candidate(
                        decision["approved_candidate"], provider_id, source_page, reviewed_category
                    )
                )
        else:
            if decision["reason_code"] == "APPROVED" or decision["approved_candidate"] is not None:
                errors.append(f"{label}: rejection cannot contain approval state")
            if decision["reason_code"] == "SEMANTIC_CATEGORY_MISMATCH" and decision["category_match"] is not False:
                errors.append(f"{label}: semantic mismatch requires category_match=false")
    return errors


def iter_decisions(document):
    """Yield normalized decisions without rewriting historical schema-v1 files."""
    for item in document.get("decisions", []):
        yield {
            **item,
            "decision_id": _decision_id(document.get("request_id"), str(item.get("provider_asset_id"))),
            "replenishment_session_id": document.get("replenishment_session_id"),
            "planner_invocation": document.get("planner_invocation"),
            "discovery_request_id": document.get("request_id"),
            "attempt": document.get("attempt"),
            "evidence": document.get("evidence"),
            "reviewed_at": document.get("reviewed_at"),
        }


def validate_readiness_event(data):
    expected = {
        "schema_version",
        "event_id",
        "replenishment_session_id",
        "planner_invocation",
        "attempt",
        "discovery_request_id",
        "readiness_manifest_path",
        "ingest_summary",
        "media_readiness",
        "continuation_phase",
        "recorded_at",
    }
    errors = _exact_fields(data, expected, "readiness event")
    if errors:
        return errors
    if data["schema_version"] != READINESS_EVENT_SCHEMA_VERSION:
        errors.append(f"readiness event schema_version must be {READINESS_EVENT_SCHEMA_VERSION}")
    if not re.fullmatch(r"re-[A-Za-z0-9-]{8,96}", str(data["event_id"])):
        errors.append("event_id is invalid")
    if not re.fullmatch(r"rs-[A-Za-z0-9-]{8,96}", str(data["replenishment_session_id"])):
        errors.append("replenishment_session_id is invalid")
    errors.extend(validate_planner_invocation(data["planner_invocation"]))
    attempt = data["attempt"]
    if isinstance(attempt, bool) or not isinstance(attempt, int) or not 1 <= attempt <= MAX_REPLENISH_ATTEMPTS:
        errors.append(f"attempt must be 1-{MAX_REPLENISH_ATTEMPTS}")
    readiness = data["media_readiness"]
    if not isinstance(readiness, dict) or readiness.get("status") not in {"PASS", "REPLENISH"}:
        errors.append("media_readiness must contain PASS or REPLENISH status")
    elif readiness.get("ready") is not (readiness.get("status") == "PASS"):
        errors.append("media_readiness.ready must agree with status")
    expected_phase = "READY_TO_RESUME" if isinstance(readiness, dict) and readiness.get("status") == "PASS" else (
        "EXHAUSTED" if attempt == MAX_REPLENISH_ATTEMPTS else "NEED_DISCOVERY"
    )
    if data["continuation_phase"] != expected_phase:
        errors.append(f"continuation_phase must be {expected_phase}")
    if not _valid_timestamp(data["recorded_at"]):
        errors.append("recorded_at must be an ISO-8601 timestamp")
    return errors


def validate_manifest_against_decisions(manifest, decisions):
    """Bind every schema-v2 ingest candidate to one immutable visual approval."""
    if manifest.get("schema_version") != SOURCE_MANIFEST_SCHEMA_VERSION:
        return []
    errors = _exact_fields(
        manifest,
        {
            "schema_version",
            "plan_date",
            "provider",
            "replenishment_session_id",
            "planner_invocation",
            "attempt",
            "discovery_request_id",
            "review_decision_ids",
            "candidates",
        },
        "schema-v2 readiness manifest",
    )
    if errors:
        return errors
    errors.extend(validate_planner_invocation(manifest["planner_invocation"]))
    if manifest["plan_date"] != manifest["planner_invocation"].get("singapore_date"):
        errors.append("manifest plan_date must equal planner_invocation.singapore_date")
    if manifest["provider"] != "Pexels":
        errors.append("manifest provider must be Pexels")
    attempt = manifest["attempt"]
    if isinstance(attempt, bool) or not isinstance(attempt, int) or not 1 <= attempt <= MAX_REPLENISH_ATTEMPTS:
        errors.append(f"manifest attempt must be 1-{MAX_REPLENISH_ATTEMPTS}")
    expected_ids = manifest["review_decision_ids"]
    if not isinstance(expected_ids, list) or not expected_ids or len(set(expected_ids)) != len(expected_ids):
        errors.append("review_decision_ids must be a unique non-empty list")
        return errors
    by_id = {}
    for document in decisions:
        decision_errors = validate_review_decision(document)
        if decision_errors:
            errors.extend(f"decision document {document.get('request_id')}: {item}" for item in decision_errors)
            continue
        if document.get("schema_version") != REVIEW_DECISION_SCHEMA_VERSION:
            continue
        for decision in iter_decisions(document):
            decision_id = decision["decision_id"]
            if decision_id in by_id:
                errors.append(f"duplicate immutable decision_id collision: {decision_id}")
            by_id[decision_id] = decision
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append("schema-v2 readiness manifest candidates must be non-empty")
        return errors
    candidate_decision_ids = []
    for index, candidate in enumerate(candidates):
        decision_id = candidate.get("review_decision_id") if isinstance(candidate, dict) else None
        candidate_decision_ids.append(decision_id)
        decision = by_id.get(decision_id)
        if not decision:
            errors.append(f"candidate {index}: review decision does not exist")
            continue
        if decision["decision"] != "approve" or decision["category_match"] is not True:
            errors.append(f"candidate {index}: review decision is not an approved category match")
        if decision["replenishment_session_id"] != manifest["replenishment_session_id"]:
            errors.append(f"candidate {index}: decision session does not match manifest")
        if decision["planner_invocation"] != manifest["planner_invocation"]:
            errors.append(f"candidate {index}: decision planner invocation does not match manifest")
        if decision["attempt"] != attempt or decision["discovery_request_id"] != manifest["discovery_request_id"]:
            errors.append(f"candidate {index}: decision attempt/request does not match manifest")
        comparable = dict(candidate)
        comparable.pop("review_decision_id", None)
        if comparable != decision["approved_candidate"]:
            errors.append(f"candidate {index}: metadata differs from immutable approved decision")
    if candidate_decision_ids != expected_ids:
        errors.append("review_decision_ids must exactly match candidate order")
    return errors


def load_documents(paths, validator, label):
    documents = []
    for path in sorted(map(Path, paths)):
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validator(data)
        if errors:
            raise ValueError(f"Invalid {label} {path}:\n- " + "\n- ".join(errors))
        documents.append((path, data))
    return documents


def derive_session_state(
    session_id,
    discovery_requests=(),
    discovery_results=(),
    review_evidence_indexes=(),
    review_decisions=(),
    readiness_manifests=(),
    readiness_events=(),
    active_provider_asset_ids=(),
):
    requests = [x for x in discovery_requests if x.get("replenishment_session_id") == session_id]
    decision_documents = [x for x in review_decisions if x.get("replenishment_session_id") == session_id]
    events = [x for x in readiness_events if x.get("replenishment_session_id") == session_id]
    manifests = [x for x in readiness_manifests if x.get("replenishment_session_id") == session_id]
    if not requests:
        raise ValueError(f"Unknown replenishment session: {session_id}")

    invocation = requests[0].get("planner_invocation")
    if validate_planner_invocation(invocation):
        raise ValueError("Session discovery request has invalid planner_invocation")
    current_decision_documents = [
        doc for doc in decision_documents if doc.get("schema_version") == REVIEW_DECISION_SCHEMA_VERSION
    ]
    all_docs = [*requests, *current_decision_documents, *events, *manifests]
    if any(doc.get("planner_invocation") != invocation for doc in all_docs):
        raise ValueError("All replenishment documents must preserve the same planner invocation")

    by_attempt = {}
    for request in requests:
        attempt = request.get("attempt")
        if attempt in by_attempt:
            raise ValueError(f"Duplicate discovery request collision for attempt {attempt}")
        by_attempt[attempt] = request
    attempts = sorted(by_attempt)
    if attempts != list(range(1, max(attempts) + 1)):
        raise ValueError("Replenishment attempts must be contiguous and start at 1")
    if attempts[-1] > MAX_REPLENISH_ATTEMPTS:
        raise ValueError("Replenishment attempt exceeds configured maximum")

    result_by_request = {x.get("request_id"): x for x in discovery_results}
    evidence_by_request = {}
    for index in review_evidence_indexes:
        evidence_by_request.setdefault(index.get("request_id"), []).append(index)
    decision_keys = set()
    decisions = []
    for document in decision_documents:
        errors = validate_review_decision(document)
        if errors:
            raise ValueError("Invalid review decision:\n- " + "\n- ".join(errors))
        if document.get("schema_version") != REVIEW_DECISION_SCHEMA_VERSION:
            raise ValueError("A resumable schema-v3 session requires schema-v2 evidence-bound decisions")
        request = by_attempt.get(document["attempt"])
        if not request or request.get("request_id") != document["request_id"]:
            raise ValueError("Review decision document does not bind to its session discovery request")
        evidence = document["evidence"]
        expected_index_path = (
            "youtube-shorts-bot/content/background-sourcing/review-evidence/"
            f"{document['request_id']}-run-{evidence['workflow_run_id']}.json"
        )
        matching_index = next(
            (
                item for item in evidence_by_request.get(document["request_id"], [])
                if item.get("workflow_run_id") == evidence["workflow_run_id"]
                and item.get("artifact_id") == evidence["artifact_id"]
                and item.get("evidence_manifest_sha256") == evidence["evidence_manifest_sha256"]
            ),
            None,
        )
        if evidence["review_index_path"] != expected_index_path or matching_index is None:
            raise ValueError("Review decision evidence does not bind to an immutable review index")
        for decision in iter_decisions(document):
            decisions.append(decision)
            provider_id = str(decision["provider_asset_id"])
            if provider_id in decision_keys:
                raise ValueError(f"Immutable duplicate review decision collision for provider {provider_id}")
            decision_keys.add(provider_id)
            result = result_by_request.get(decision["discovery_request_id"])
            candidates = result.get("candidates", []) if isinstance(result, dict) else []
            source = next(
                (item for item in candidates if str(item.get("provider_asset_id") or "") == provider_id),
                None,
            )
            if source is None:
                raise ValueError("Review decision provider does not exist in its immutable discovery result")
            if source.get("discovery_category") != decision["discovery_category"]:
                raise ValueError("Review decision discovery_category differs from discovery provenance")
            if source.get("source_page") != decision["source_page"]:
                raise ValueError("Review decision source_page differs from discovery provenance")

    event_attempts = set()
    for event in events:
        errors = validate_readiness_event(event)
        if errors:
            raise ValueError("Invalid readiness event:\n- " + "\n- ".join(errors))
        if event["attempt"] in event_attempts:
            raise ValueError(f"Immutable readiness-event collision for attempt {event['attempt']}")
        event_attempts.add(event["attempt"])

    evidence_requests = set(evidence_by_request)
    reviewed = sorted(decision_keys)
    approved = sorted(str(x["provider_asset_id"]) for x in decisions if x["decision"] == "approve")
    rejected = sorted(str(x["provider_asset_id"]) for x in decisions if x["decision"] == "reject")
    discovered = sorted({
        str(item.get("provider_asset_id"))
        for result in discovery_results
        if result.get("replenishment_session_id") == session_id
        for item in result.get("candidates", [])
        if str(item.get("provider_asset_id") or "").isdigit()
    })
    latest_attempt = attempts[-1]
    latest_request = by_attempt[latest_attempt]
    latest_result = result_by_request.get(latest_request["request_id"])
    latest_event = max(events, key=lambda x: x["attempt"], default=None)
    manifest_attempts = {x.get("attempt") for x in manifests}

    if latest_event and latest_event["media_readiness"]["status"] == "PASS":
        phase = "READY_TO_RESUME"
    elif latest_event and latest_event["attempt"] == latest_attempt:
        phase = "EXHAUSTED" if latest_attempt >= MAX_REPLENISH_ATTEMPTS else "NEED_DISCOVERY"
    elif latest_attempt in manifest_attempts:
        phase = "WAITING_INGESTION"
    elif latest_result is None:
        phase = "WAITING_DISCOVERY"
    elif latest_request["request_id"] not in evidence_requests:
        phase = "WAITING_EVIDENCE"
    else:
        candidate_ids = {
            str(x.get("provider_asset_id"))
            for x in latest_result.get("candidates", [])
            if str(x.get("provider_asset_id") or "").isdigit()
        }
        undecided = candidate_ids - decision_keys
        latest_approved = {
            str(x["provider_asset_id"])
            for x in decisions
            if x["attempt"] == latest_attempt and x["decision"] == "approve"
        }
        if undecided:
            phase = "NEEDS_VISUAL_REVIEW"
        elif latest_approved:
            phase = "NEEDS_INGESTION"
        else:
            phase = "EXHAUSTED" if latest_attempt >= MAX_REPLENISH_ATTEMPTS else "NEED_DISCOVERY"

    rejection_counts = Counter(x["reason_code"] for x in decisions if x["decision"] == "reject")
    latest_readiness = latest_event.get("media_readiness") if latest_event else {
        "status": "REPLENISH",
        "category_deficits": latest_request.get("category_deficits", {}),
        "required_new_assets_at_least": latest_request.get("required_new_assets_at_least", 0),
    }
    return {
        "schema_version": 1,
        "replenishment_session_id": session_id,
        "planner_invocation": invocation,
        "attempt": latest_attempt,
        "max_attempts": MAX_REPLENISH_ATTEMPTS,
        "continuation_phase": phase,
        "readiness_passed": phase == "READY_TO_RESUME",
        "resume_original_planner": phase == "READY_TO_RESUME",
        "latest_media_readiness": latest_readiness,
        "discovered_provider_asset_ids": discovered,
        "reviewed_provider_asset_ids": reviewed,
        "approved_provider_asset_ids": approved,
        "rejected_provider_asset_ids": rejected,
        "excluded_provider_asset_ids": sorted(set(discovered) | set(reviewed) | set(map(str, active_provider_asset_ids))),
        "rejection_reason_summary": dict(sorted(rejection_counts.items())),
        "diagnostic": build_exhaustion_diagnostic(latest_readiness, latest_attempt, decisions, discovered)
        if phase == "EXHAUSTED" else None,
    }


def build_exhaustion_diagnostic(readiness, attempt, decisions, exhausted_provider_ids):
    return {
        "error_code": "E_MEDIA_REPLENISH_EXHAUSTED",
        "remaining_total_deficit": int(readiness.get("required_new_assets_at_least") or 0),
        "remaining_category_deficits": readiness.get("category_deficits") or {},
        "attempt_count": attempt,
        "candidates_reviewed": len(decisions),
        "candidates_approved": sum(x.get("decision") == "approve" for x in decisions),
        "candidates_rejected": sum(x.get("decision") == "reject" for x in decisions),
        "rejection_reason_summary": dict(sorted(Counter(
            x.get("reason_code") for x in decisions if x.get("decision") == "reject"
        ).items())),
        "provider_ids_exhausted_or_excluded": sorted(set(map(str, exhausted_provider_ids))),
    }


def build_next_discovery_request(
    readiness,
    session_id,
    planner_invocation,
    attempt,
    excluded_provider_asset_ids=(),
):
    """Create deterministic schema-v3 input for the next infrastructure round."""
    if readiness.get("status") != "REPLENISH":
        raise ValueError("A discovery request may be created only from REPLENISH readiness")
    if not re.fullmatch(r"rs-[A-Za-z0-9-]{8,96}", str(session_id)):
        raise ValueError("replenishment_session_id is invalid")
    errors = validate_planner_invocation(planner_invocation)
    if errors:
        raise ValueError("Invalid planner invocation: " + "; ".join(errors))
    if isinstance(attempt, bool) or not isinstance(attempt, int) or not 1 <= attempt <= MAX_REPLENISH_ATTEMPTS:
        raise ValueError(f"attempt must be 1-{MAX_REPLENISH_ATTEMPTS}")
    raw_deficits = readiness.get("category_deficits")
    if not isinstance(raw_deficits, dict):
        raise ValueError("readiness.category_deficits is required")
    deficits = {}
    for category in DISCOVERY_CATEGORIES:
        value = raw_deficits.get(category, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"category deficit for {category} must be a non-negative integer")
        deficits[category] = value
    target_categories = [category for category in DISCOVERY_CATEGORIES if deficits[category] > 0]
    required = readiness.get("required_new_assets_at_least")
    if isinstance(required, bool) or not isinstance(required, int) or required < 1:
        raise ValueError("readiness.required_new_assets_at_least must be a positive integer")
    excluded = sorted(set(map(str, excluded_provider_asset_ids)), key=lambda x: (len(x), x))
    if any(not value.isdigit() for value in excluded):
        raise ValueError("excluded provider asset IDs must be numeric")
    reserve_count = max(6, required * 3, len(target_categories) * 3)
    return {
        "schema_version": DISCOVERY_REQUEST_SCHEMA_VERSION,
        "plan_date": planner_invocation["singapore_date"],
        "request_id": f"dr-{session_id[3:]}-a{attempt:02d}",
        "max_candidates": min(48, reserve_count),
        "target_categories": target_categories or None,
        "category_deficits": deficits,
        "required_new_assets_at_least": required,
        "exclude_provider_asset_ids": excluded,
        "replenishment_session_id": session_id,
        "planner_invocation": planner_invocation,
        "attempt": attempt,
    }


def build_readiness_event(manifest, ingest_summary, registry, recorded_at=None):
    if manifest.get("schema_version") != SOURCE_MANIFEST_SCHEMA_VERSION:
        raise ValueError("readiness events are created only for schema-v2 replenishment manifests")
    readiness = audit_registry(registry)
    attempt = manifest["attempt"]
    phase = "READY_TO_RESUME" if readiness["status"] == "PASS" else (
        "EXHAUSTED" if attempt == MAX_REPLENISH_ATTEMPTS else "NEED_DISCOVERY"
    )
    session_id = manifest["replenishment_session_id"]
    return {
        "schema_version": READINESS_EVENT_SCHEMA_VERSION,
        "event_id": f"re-{session_id[3:]}-a{attempt:02d}",
        "replenishment_session_id": session_id,
        "planner_invocation": manifest["planner_invocation"],
        "attempt": attempt,
        "discovery_request_id": manifest["discovery_request_id"],
        "readiness_manifest_path": manifest["readiness_manifest_path"],
        "ingest_summary": ingest_summary,
        "media_readiness": readiness,
        "continuation_phase": phase,
        "recorded_at": recorded_at or datetime.now(timezone.utc).isoformat(),
    }


def load_session_state(root, session_id):
    """Load one session from canonical repository paths and derive its next phase."""
    root = Path(root)
    sourcing = root / "content" / "background-sourcing"

    def read_many(pattern):
        documents = []
        for path in sorted(sourcing.glob(pattern)):
            try:
                documents.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"Cannot read immutable replenishment state {path}: {exc}") from exc
        return documents

    registry_path = root / "media-library" / "backgrounds.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    active_provider_ids = [
        str(asset.get("provider_asset_id"))
        for asset in registry.get("assets", [])
        if asset.get("status") == "active"
        and asset.get("verified") is True
        and str(asset.get("provider_asset_id") or "").isdigit()
    ]
    return derive_session_state(
        session_id,
        discovery_requests=read_many("discovery-requests/*.json"),
        discovery_results=read_many("discovery-results/*.json"),
        review_evidence_indexes=read_many("review-evidence/*.json"),
        review_decisions=read_many("review-decisions/*.json"),
        readiness_manifests=read_many("readiness/*.json"),
        readiness_events=read_many(f"replenishment-events/{session_id}/*.json"),
        active_provider_asset_ids=active_provider_ids,
    )


def find_compatible_session(root, planner_invocation):
    """Return the sole session for an invocation, including READY_TO_RESUME state."""
    errors = validate_planner_invocation(planner_invocation)
    if errors:
        raise ValueError("Invalid planner invocation: " + "; ".join(errors))
    requests_dir = Path(root) / "content" / "background-sourcing" / "discovery-requests"
    session_ids = set()
    for path in sorted(requests_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("planner_invocation") == planner_invocation and data.get("replenishment_session_id"):
            session_ids.add(data["replenishment_session_id"])
    if len(session_ids) > 1:
        raise ValueError("Planner invocation is bound to multiple replenishment sessions")
    if not session_ids:
        return None
    return load_session_state(root, next(iter(session_ids)))


def _write_immutable(path, data, validator):
    errors = validator(data)
    if errors:
        raise ValueError("Invalid immutable document:\n- " + "\n- ".join(errors))
    path = Path(path)
    encoded = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError(f"Immutable document collision: {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    return True


def main():
    parser = argparse.ArgumentParser(description="Validate and derive immutable replenishment state")
    sub = parser.add_subparsers(dest="command", required=True)
    decision = sub.add_parser("validate-decision")
    decision.add_argument("--decision", required=True)
    state = sub.add_parser("state")
    state.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    state.add_argument("--session-id", required=True)
    event = sub.add_parser("record-readiness-event")
    event.add_argument("--manifest", required=True)
    event.add_argument("--ingest-result", required=True)
    event.add_argument("--registry", required=True)
    event.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.command == "validate-decision":
        data = json.loads(Path(args.decision).read_text(encoding="utf-8"))
        errors = validate_review_decision(data)
        if errors:
            raise SystemExit("Invalid review decision:\n- " + "\n- ".join(errors))
        print(json.dumps({"status": "PASS", "request_id": data["request_id"]}))
        return
    if args.command == "state":
        print(json.dumps(load_session_state(args.root, args.session_id), indent=2, sort_keys=True))
        return

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    manifest["readiness_manifest_path"] = str(args.manifest)
    ingest = json.loads(Path(args.ingest_result).read_text(encoding="utf-8"))
    registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    readiness_event = build_readiness_event(manifest, ingest, registry)
    _write_immutable(Path(args.output), readiness_event, validate_readiness_event)
    print(json.dumps(readiness_event, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
