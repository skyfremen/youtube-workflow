"""Fail-closed Work/ChatGPT adapter for canonical Wacky Dramas planning.

ChatGPT / Work owns editorial winner selection. This module owns deterministic
filtering, scoring, normalization, diversity validation, scheduling support and
execution provenance. Legacy ``final-select`` remains available only for recovery
compatibility with historical planning artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from analytics.analytics_learning import score_candidate
from planning.planning_config import (
    DAILY_PUBLISH_COUNT,
    DIVERSITY_LIMITS,
    EXPLORATION_FRACTION,
    RAW_CANDIDATE_COUNT,
    SEMIFINALIST_TARGET,
)
from planning.planning_engine import (
    PlanningError,
    analytics_weight,
    editorial_score,
    evaluate,
    filter_candidates,
    hourly_slots,
    order_for_schedule,
    score_semifinalist,
    similarity,
)

CONTRACT_VERSION = 2
ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_FILES = (
    Path(__file__).resolve(),
    Path(__file__).with_name("planning_engine.py"),
    Path(__file__).with_name("planning_config.py"),
    Path(__file__).resolve().parents[1] / "analytics" / "analytics_learning.py",
)


def _json_digest(value):
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def implementation_digest():
    digest = hashlib.sha256()
    for path in IMPLEMENTATION_FILES:
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def source_sha():
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PlanningError("cannot resolve checked-out source SHA") from exc
    if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha.lower()):
        raise PlanningError("checked-out source SHA is not a full Git commit SHA")
    return sha.lower()


def _require_list(payload, key):
    value = payload.get(key)
    if not isinstance(value, list):
        raise PlanningError(f"{key} must be a JSON array")
    return value


def _raw_filter(payload):
    raw_candidates = _require_list(payload, "raw_candidates")
    recent = payload.get("recent", [])
    if not isinstance(recent, list):
        raise PlanningError("recent must be a JSON array")
    if len(raw_candidates) < RAW_CANDIDATE_COUNT:
        raise PlanningError(
            f"raw candidate count {len(raw_candidates)} is below required {RAW_CANDIDATE_COUNT}"
        )
    qualified, rejected = filter_candidates(raw_candidates, recent=recent)
    return {
        "raw_premises_generated": len(raw_candidates),
        "hard_rejected": len(rejected),
        "qualified": len(qualified),
        "qualified_candidates": qualified,
        "rejected": [
            {
                "candidate_id": item["candidate"].get("candidate_id"),
                "reason": item["reason"],
            }
            for item in rejected
        ],
    }


def _apply_analytics(semifinalists, model):
    if not isinstance(model, dict):
        raise PlanningError("analytics_model must be an object when provided")
    evidence_count = int(model.get("analytics_evidence_count") or 0)
    enriched = []
    for candidate in semifinalists:
        item = dict(candidate)
        scored = score_candidate(item, model)
        if scored is None:
            item.pop("analytics_metrics", None)
        else:
            item["analytics_metrics"] = {
                "historical_attribute_fit": scored["historical_attribute_fit"]
            }
        enriched.append(item)
    return enriched, evidence_count


def _prepare_semifinalists(payload):
    raw_candidates = _require_list(payload, "raw_candidates")
    semifinalists = _require_list(payload, "semifinalists")
    recent = payload.get("recent", [])
    if not isinstance(recent, list):
        raise PlanningError("recent must be a JSON array")
    if len(raw_candidates) < RAW_CANDIDATE_COUNT:
        raise PlanningError(
            f"raw candidate count {len(raw_candidates)} is below required {RAW_CANDIDATE_COUNT}"
        )

    qualified, rejected = filter_candidates(raw_candidates, recent=recent)
    qualified_ids = {item["candidate_id"] for item in qualified}
    semifinalists = [item for item in semifinalists if item.get("candidate_id") in qualified_ids]
    if len(semifinalists) > SEMIFINALIST_TARGET:
        semifinalists = sorted(semifinalists, key=editorial_score, reverse=True)[:SEMIFINALIST_TARGET]

    model = payload.get("analytics_model")
    if model is not None:
        semifinalists, evidence_count = _apply_analytics(semifinalists, model)
        supplied = payload.get("analytics_evidence_count")
        if supplied is not None and int(supplied) != evidence_count:
            raise PlanningError(
                "analytics_evidence_count does not match analytics_model provenance"
            )
    else:
        evidence_count = int(payload.get("analytics_evidence_count") or 0)
        if evidence_count > 0:
            raise PlanningError(
                "positive analytics_evidence_count requires analytics_model so canonical analytics scoring executes"
            )
        semifinalists = [dict(candidate) for candidate in semifinalists]
        for candidate in semifinalists:
            candidate.pop("analytics_metrics", None)

    return raw_candidates, semifinalists, recent, rejected, evidence_count


def _candidate_evaluation(payload):
    raw_candidates, semifinalists, _recent, rejected, evidence_count = _prepare_semifinalists(payload)
    weight = analytics_weight(evidence_count)
    evaluated, semifinal_rejected = [], []
    for candidate in semifinalists:
        try:
            evaluated.append(score_semifinalist(candidate, weight))
        except PlanningError as exc:
            semifinal_rejected.append({
                "candidate_id": candidate.get("candidate_id"),
                "reason": str(exc),
            })
    evaluated.sort(key=lambda item: item["final_score"], reverse=True)
    return {
        "raw_premises_generated": len(raw_candidates),
        "hard_rejected": len(rejected),
        "semifinalists": len(semifinalists),
        "semifinal_rejected": semifinal_rejected,
        "analytics_weight": weight,
        "evaluated_candidates": evaluated,
    }


def _validate_selection(payload):
    evaluated = _require_list(payload, "evaluated_candidates")
    selected_ids = _require_list(payload, "selected_candidate_ids")
    plan_date = payload.get("plan_date")
    if not isinstance(plan_date, str) or not plan_date.strip():
        raise PlanningError("plan_date must be a non-empty ISO date string")
    if not selected_ids:
        raise PlanningError("ChatGPT must select at least one candidate")
    if len(selected_ids) != len(set(selected_ids)):
        raise PlanningError("selected_candidate_ids contains duplicates")

    requested_limit = int(payload.get("selection_limit") or DAILY_PUBLISH_COUNT)
    if requested_limit < 1 or requested_limit > DAILY_PUBLISH_COUNT:
        raise PlanningError("selection_limit is outside canonical bounds")
    if len(selected_ids) > requested_limit:
        raise PlanningError("ChatGPT selected more candidates than the allowed limit")

    by_id = {item.get("candidate_id"): item for item in evaluated if item.get("candidate_id")}
    missing = [candidate_id for candidate_id in selected_ids if candidate_id not in by_id]
    if missing:
        raise PlanningError(
            "ChatGPT selection contains candidates that did not pass deterministic evaluation: "
            + ", ".join(missing)
        )

    selected = [dict(by_id[candidate_id]) for candidate_id in selected_ids]
    counts = {key: Counter() for key in DIVERSITY_LIMITS}
    for index, candidate in enumerate(selected):
        values = {
            "category": candidate.get("category"),
            "conflict": candidate.get("conflict"),
            "title_style": candidate.get("selected_title_style"),
        }
        for key, value in values.items():
            if value and counts[key][value] >= DIVERSITY_LIMITS[key]:
                raise PlanningError(
                    f"ChatGPT selection violates {key} diversity limit for {value}"
                )
        for prior in selected[:index]:
            sim = similarity(candidate, prior)
            if sim >= payload.get("near_duplicate_threshold", 0.0) and payload.get("near_duplicate_threshold") is not None:
                # Explicit threshold is supported only for tests/debugging; normal callers omit it.
                raise PlanningError("ChatGPT selection contains a near-duplicate pair")
        for key, value in values.items():
            if value:
                counts[key][value] += 1

    # Use the canonical similarity threshold without duplicating its numeric value.
    from planning.planning_config import NEAR_DUPLICATE_THRESHOLD
    for index, candidate in enumerate(selected):
        for prior in selected[:index]:
            sim = similarity(candidate, prior)
            if sim >= NEAR_DUPLICATE_THRESHOLD:
                raise PlanningError(
                    f"ChatGPT selection contains near-duplicates: {prior.get('candidate_id')} / {candidate.get('candidate_id')}"
                )

    if len(selected) == DAILY_PUBLISH_COUNT:
        explore_target = round(DAILY_PUBLISH_COUNT * EXPLORATION_FRACTION)
        explore_count = sum(item.get("selection_class") == "explore" for item in selected)
        if explore_count < explore_target:
            raise PlanningError(
                f"full Daily selection requires at least {explore_target} explore candidates"
            )

    ordered = order_for_schedule(selected)
    for candidate, slot in zip(ordered, hourly_slots(plan_date)):
        candidate["publication"] = slot
        candidate["selection_class"] = candidate.get("selection_class", "exploit")

    return {
        "plan_date": plan_date,
        "selection_owner": "chatgpt",
        "selected_candidate_ids": selected_ids,
        "validated_selected": ordered,
        "final_selected": len(ordered),
        "exploit_selections": sum(item.get("selection_class") != "explore" for item in ordered),
        "explore_selections": sum(item.get("selection_class") == "explore" for item in ordered),
    }


def _final_select(payload):
    """Legacy deterministic winner selection for historical recovery compatibility only."""
    raw_candidates, semifinalists, recent, _rejected, evidence_count = _prepare_semifinalists(payload)
    plan_date = payload.get("plan_date")
    if not isinstance(plan_date, str) or not plan_date.strip():
        raise PlanningError("plan_date must be a non-empty ISO date string")
    return evaluate(
        raw_candidates,
        semifinalists,
        plan_date,
        analytics_video_count=evidence_count,
        recent=recent,
    )


def execute(stage, payload):
    if not isinstance(payload, dict):
        raise PlanningError("planner input root must be a JSON object")
    if stage == "raw-filter":
        result = _raw_filter(payload)
        entry_points = ["planning.planning_engine.filter_candidates"]
    elif stage == "candidate-evaluation":
        result = _candidate_evaluation(payload)
        entry_points = [
            "analytics.analytics_learning.score_candidate",
            "planning.planning_engine.filter_candidates",
            "planning.planning_engine.score_semifinalist",
        ]
    elif stage == "validate-selection":
        result = _validate_selection(payload)
        entry_points = [
            "planning.planning_engine.similarity",
            "planning.planning_engine.order_for_schedule",
            "planning.planning_engine.hourly_slots",
        ]
    elif stage == "final-select":
        result = _final_select(payload)
        entry_points = [
            "analytics.analytics_learning.score_candidate",
            "planning.planning_engine.evaluate",
        ]
    else:
        raise PlanningError(f"unsupported planning stage: {stage}")

    return {
        "execution": {
            "contract_version": CONTRACT_VERSION,
            "stage": stage,
            "source_sha": source_sha(),
            "implementation_sha256": implementation_digest(),
            "input_sha256": _json_digest(payload),
            "entry_points": entry_points,
        },
        "result": result,
    }


def _load_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanningError(f"cannot read planner input: {exc}") from exc
    return data


def _write_atomic(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)


def main():
    parser = argparse.ArgumentParser(
        description="Execute deterministic Wacky Dramas planning support for ChatGPT/Work."
    )
    parser.add_argument(
        "--stage",
        choices=("raw-filter", "candidate-evaluation", "validate-selection", "final-select"),
        required=True,
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    output.unlink(missing_ok=True)
    try:
        envelope = execute(args.stage, _load_json(args.input))
        _write_atomic(output, envelope)
    except (PlanningError, TypeError, ValueError, OSError) as exc:
        output.unlink(missing_ok=True)
        raise SystemExit(f"planning runner failed closed: {exc}") from exc

    print(
        f"Canonical planning support executed: stage={args.stage}; "
        f"source_sha={envelope['execution']['source_sha']}; "
        f"output={output}"
    )


if __name__ == "__main__":
    main()
