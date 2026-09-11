"""Fail-closed Work/ChatGPT adapter for canonical Wacky Dramas planning.

This module does not duplicate planning policy. It serializes Work-produced semantic
inputs into the existing deterministic planning functions and returns their actual
outputs with lightweight execution provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from analytics.analytics_learning import score_candidate
from planning.planning_config import RAW_CANDIDATE_COUNT
from planning.planning_engine import PlanningError, evaluate, filter_candidates

CONTRACT_VERSION = 1
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
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


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


def _final_select(payload):
    raw_candidates = _require_list(payload, "raw_candidates")
    semifinalists = _require_list(payload, "semifinalists")
    recent = payload.get("recent", [])
    if not isinstance(recent, list):
        raise PlanningError("recent must be a JSON array")
    plan_date = payload.get("plan_date")
    if not isinstance(plan_date, str) or not plan_date.strip():
        raise PlanningError("plan_date must be a non-empty ISO date string")

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
        description="Execute canonical deterministic Wacky Dramas planning for Work/ChatGPT."
    )
    parser.add_argument("--stage", choices=("raw-filter", "final-select"), required=True)
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
        f"Canonical planning executed: stage={args.stage}; "
        f"source_sha={envelope['execution']['source_sha'] or 'unavailable'}; "
        f"output={output}"
    )


if __name__ == "__main__":
    main()
