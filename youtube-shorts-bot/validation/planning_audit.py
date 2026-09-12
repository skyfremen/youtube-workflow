"""Fail-closed validation for canonical daily planning commits.

This module validates the private control-plane handoff before Daily Production
creates any dispatch evidence. Historical immutable files are not mutated; only
new canonical daily content commits are checked.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from planning.planning_runner import CONTRACT_VERSION, implementation_digest
from publishing.upload import build_upload_body
from validation.validate_content import validate_request_data

REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
PLAN_RE = re.compile(r"^youtube-shorts-bot/content/planning/(\d{4}-\d{2}-\d{2})\.json$")
REQUEST_RE = re.compile(r"^youtube-shorts-bot/content/requests/(wd-[A-Za-z0-9-]+)\.json$")
SOURCING_RE = re.compile(r"^youtube-shorts-bot/content/background-sourcing/(\d{4}-\d{2}-\d{2})\.json$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CANDIDATE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PLANNING_MODES = {"normal_next_day", "same_day_catch_up"}
FORBIDDEN_PRODUCTION_ID_MARKERS = (
    "-acceptance-",
    "-test-",
    "-smoke-",
    "-dryrun-",
    "-dry-run-",
    "-adhoc-",
)
EXECUTION_KEYS = {
    "contract_version",
    "stage",
    "source_sha",
    "implementation_sha256",
    "input_sha256",
    "entry_points",
}
EXPECTED_ENTRY_POINTS = {
    "raw-filter": ["planning.planning_engine.filter_candidates"],
    "final-select": [
        "analytics.analytics_learning.score_candidate",
        "planning.planning_engine.evaluate",
    ],
}


class PlanningAuditError(RuntimeError):
    pass


def _fail(message):
    raise PlanningAuditError(message)


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"cannot read JSON {path}: {exc}")


def _git(*args):
    try:
        return subprocess.check_output(
            ["git", *args], cwd=REPO_ROOT, text=True, stderr=subprocess.STDOUT
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        output = getattr(exc, "output", "") or ""
        _fail(f"git {' '.join(args)} failed: {output.strip() or type(exc).__name__}")


def _single_parent(source_sha):
    line = _git("rev-list", "--parents", "-n", "1", source_sha)
    parts = line.split()
    if len(parts) != 2 or parts[0] != source_sha:
        _fail("daily planning commit must have exactly one parent")
    return parts[1]


def _changed_paths(source_sha):
    raw = _git("diff-tree", "--no-commit-id", "--name-status", "-r", source_sha)
    changes = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            _fail("daily planning commit contains unsupported rename/copy diff")
        changes.append((parts[0], parts[1]))
    return changes


def classify_daily_changes(changes):
    if not changes:
        _fail("daily planning commit contains no changes")
    if any(status != "A" for status, _ in changes):
        _fail("daily planning commit may only add immutable planning/request/sourcing files")

    plans = []
    requests = []
    sourcing = []
    unexpected = []
    for _, path in changes:
        if PLAN_RE.fullmatch(path):
            plans.append(path)
        elif REQUEST_RE.fullmatch(path):
            requests.append(path)
        elif SOURCING_RE.fullmatch(path):
            sourcing.append(path)
        else:
            unexpected.append(path)

    if unexpected:
        _fail("daily planning commit contains unexpected files: " + ", ".join(sorted(unexpected)))
    if len(plans) != 1:
        _fail("daily planning commit must add exactly one canonical YYYY-MM-DD planning audit")
    if not 1 <= len(requests) <= 24:
        _fail("daily planning commit must add 1-24 immutable requests")
    if len(sourcing) > 1:
        _fail("daily planning commit may add at most one same-day sourcing manifest")
    return plans[0], requests, sourcing[0] if sourcing else None


def _validate_execution(execution, stage, parent_sha, impl_sha):
    if not isinstance(execution, dict) or set(execution) != EXECUTION_KEYS:
        _fail(f"planning_execution.{stage} must be the verbatim canonical runner execution object")
    if execution.get("contract_version") != CONTRACT_VERSION:
        _fail(f"planning_execution.{stage}.contract_version mismatch")
    if execution.get("stage") != stage:
        _fail(f"planning_execution.{stage}.stage mismatch")
    if execution.get("source_sha") != parent_sha:
        _fail(
            f"planning_execution.{stage}.source_sha must equal the daily content commit parent SHA"
        )
    if execution.get("implementation_sha256") != impl_sha:
        _fail(f"planning_execution.{stage}.implementation_sha256 does not match current canonical code")
    input_sha = execution.get("input_sha256")
    if not isinstance(input_sha, str) or not HEX64.fullmatch(input_sha):
        _fail(f"planning_execution.{stage}.input_sha256 must be a lowercase SHA-256")
    if execution.get("entry_points") != EXPECTED_ENTRY_POINTS[stage]:
        _fail(f"planning_execution.{stage}.entry_points mismatch")


def validate_plan_core(plan, plan_path, request_ids, parent_sha, impl_sha):
    if not isinstance(plan, dict):
        _fail("planning audit root must be an object")
    required = {"plan_date", "planning_mode", "final_selected", "content_ids", "planning_execution"}
    missing = required - set(plan)
    if missing:
        _fail("planning audit missing required fields: " + ", ".join(sorted(missing)))

    match = PLAN_RE.fullmatch(plan_path)
    if not match:
        _fail("planning audit path must be content/planning/YYYY-MM-DD.json")
    path_date = match.group(1)
    try:
        date.fromisoformat(path_date)
    except ValueError:
        _fail("planning audit filename date is invalid")
    if plan.get("plan_date") != path_date:
        _fail("planning audit plan_date must exactly match its canonical filename")
    if plan.get("planning_mode") not in PLANNING_MODES:
        _fail("planning_mode must be normal_next_day or same_day_catch_up")

    content_ids = plan.get("content_ids")
    if not isinstance(content_ids, list) or not content_ids:
        _fail("planning audit content_ids must be a non-empty array")
    if any(not isinstance(item, str) or not item for item in content_ids):
        _fail("planning audit content_ids entries must be non-empty strings")
    if len(content_ids) != len(set(content_ids)):
        _fail("planning audit content_ids must be unique")
    if set(content_ids) != set(request_ids):
        _fail("planning audit content_ids must exactly match request filenames added by the same commit")
    if plan.get("final_selected") != len(content_ids):
        _fail("planning audit final_selected must equal the number of new immutable requests")
    if not 1 <= len(content_ids) <= 24:
        _fail("planning audit final_selected must be between 1 and 24")

    padded_ids = [f"-{content_id.lower()}-" for content_id in content_ids]
    for content_id, padded in zip(content_ids, padded_ids):
        if any(marker in padded for marker in FORBIDDEN_PRODUCTION_ID_MARKERS):
            _fail(f"canonical daily production rejects reserved acceptance/test/ad-hoc identity: {content_id}")

    planning_execution = plan.get("planning_execution")
    if not isinstance(planning_execution, dict) or set(planning_execution) != {
        "raw_filter", "final_selection", "selected_candidate_ids"
    }:
        _fail("planning_execution must contain exactly raw_filter, final_selection, selected_candidate_ids")

    _validate_execution(planning_execution["raw_filter"], "raw-filter", parent_sha, impl_sha)
    _validate_execution(planning_execution["final_selection"], "final-select", parent_sha, impl_sha)
    if planning_execution["raw_filter"]["input_sha256"] == planning_execution["final_selection"]["input_sha256"]:
        _fail("raw-filter and final-select must record distinct canonical runner inputs")

    selected = planning_execution.get("selected_candidate_ids")
    if not isinstance(selected, list) or len(selected) != len(content_ids):
        _fail("selected_candidate_ids must contain exactly one candidate identity per final request")
    if len(selected) != len(set(selected)):
        _fail("selected_candidate_ids must be unique")
    if any(not isinstance(item, str) or not CANDIDATE_ID.fullmatch(item) for item in selected):
        _fail("selected_candidate_ids contains an invalid candidate identity")
    return path_date, content_ids


def _validate_requests(plan_date, request_paths, expected_ids):
    publish_times = set()
    requests = {}
    singapore = ZoneInfo("Asia/Singapore")
    for request_path in request_paths:
        match = REQUEST_RE.fullmatch(request_path)
        if not match:
            _fail(f"invalid request path: {request_path}")
        content_id = match.group(1)
        path = REPO_ROOT / request_path
        data = _load_json(path)
        errors = validate_request_data(data, path)
        if errors:
            _fail(f"request {content_id} failed canonical validation: {'; '.join(errors)}")
        if data.get("schema_version") != 4:
            _fail(f"new daily request {content_id} must use schema-v4")
        if data.get("content_id") != content_id:
            _fail(f"request {content_id} content_id does not match filename")
        if data.get("planning", {}).get("plan_date") != plan_date:
            _fail(f"request {content_id} planning.plan_date must match daily planning audit")
        publication = data.get("publication") or {}
        if publication.get("mode") != "scheduled":
            _fail(f"daily request {content_id} must use scheduled publication mode")
        raw = publication.get("publish_at")
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            _fail(f"request {content_id} publish_at is invalid")
        if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
            _fail(f"request {content_id} publish_at must be UTC")
        local = parsed.astimezone(singapore)
        if local.date().isoformat() != plan_date or any((local.minute, local.second, local.microsecond)):
            _fail(f"request {content_id} must publish on an exact top-of-hour slot of the plan date")
        if raw in publish_times:
            _fail("daily request publication slots must be unique")
        publish_times.add(raw)
        try:
            build_upload_body(data, require_future=False)
        except (KeyError, TypeError, ValueError) as exc:
            _fail(f"request {content_id} final publication payload is invalid: {exc}")
        requests[content_id] = data

    if set(requests) != set(expected_ids):
        _fail("loaded request identities do not match planning audit")
    return requests


def _validate_sourcing(plan_date, sourcing_path, content_ids, requests):
    if not sourcing_path:
        return
    match = SOURCING_RE.fullmatch(sourcing_path)
    if not match or match.group(1) != plan_date:
        _fail("background sourcing manifest filename must match planning audit date")
    data = _load_json(REPO_ROOT / sourcing_path)
    if data.get("plan_date") != plan_date:
        _fail("background sourcing manifest plan_date mismatch")
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        _fail("background sourcing manifest candidates must be a non-empty array")
    allowed_ids = set(content_ids)
    for index, item in enumerate(candidates):
        if not isinstance(item, dict):
            _fail(f"background sourcing candidate {index} must be an object")
        logical_id = str(item.get("logical_id") or "").strip()
        required_by = item.get("required_by_content_ids")
        if not logical_id or not isinstance(required_by, list) or not required_by:
            _fail(f"background sourcing candidate {index} requires logical_id and required_by_content_ids")
        if any(content_id not in allowed_ids for content_id in required_by):
            _fail(f"background sourcing candidate {index} references content outside this daily plan")
        for content_id in required_by:
            visual = requests[content_id].get("visual") or {}
            if logical_id not in {
                visual.get("background_primary_id"),
                visual.get("background_backup_id"),
            }:
                _fail(
                    f"background sourcing candidate {logical_id} is not referenced by required request {content_id}"
                )


def validate_commit(source_sha):
    if not isinstance(source_sha, str) or not HEX40.fullmatch(source_sha):
        _fail("source_sha must be a lowercase full Git commit SHA")
    if _git("rev-parse", source_sha) != source_sha:
        _fail("source_sha cannot be resolved exactly")

    parent_sha = _single_parent(source_sha)
    plan_path, request_paths, sourcing_path = classify_daily_changes(_changed_paths(source_sha))
    plan = _load_json(REPO_ROOT / plan_path)
    request_ids = [REQUEST_RE.fullmatch(path).group(1) for path in request_paths]
    impl_sha = implementation_digest()
    plan_date, content_ids = validate_plan_core(
        plan, plan_path, request_ids, parent_sha, impl_sha
    )

    subject = _git("show", "-s", "--format=%s", source_sha)
    if subject != f"[daily production] {plan_date}":
        _fail("daily planning commit subject must exactly be [daily production] YYYY-MM-DD")

    requests = _validate_requests(plan_date, request_paths, content_ids)
    _validate_sourcing(plan_date, sourcing_path, content_ids, requests)
    return {
        "source_sha": source_sha,
        "parent_sha": parent_sha,
        "plan_date": plan_date,
        "request_count": len(content_ids),
        "planning_mode": plan["planning_mode"],
    }


def main():
    parser = argparse.ArgumentParser(description="Validate one canonical daily planning content commit.")
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    try:
        result = validate_commit(args.source_sha)
    except PlanningAuditError as exc:
        raise SystemExit(f"daily planning audit failed closed: {exc}") from exc
    print(
        "Daily planning audit PASS: "
        f"date={result['plan_date']} requests={result['request_count']} "
        f"mode={result['planning_mode']} parent={result['parent_sha']}"
    )


if __name__ == "__main__":
    main()
