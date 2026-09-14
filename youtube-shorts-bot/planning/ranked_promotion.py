"""Promote immutable ChatGPT planning pools into canonical production state.

Pool schema v2 is the current simplified contract: every authored candidate is a
required production candidate and must validate. Schema-v1 compatibility remains
for immutable historical 5-candidate Ad-hoc and 36-candidate Daily pools, including
historical scheduled Ad-hoc recovery.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath as PurePath

from media.validate_media_library import load_registry
from planning.planner_core import (
    ADHOC_POOL_RE,
    BOT_ROOT,
    CATCH_UP_MIN_LEAD_MINUTES,
    DAILY_POOL_RE,
    HEX40_RE,
    LEGACY_POOL_SCHEMA_VERSION,
    POOL_SCHEMA_VERSION,
    REPO_ROOT,
    PlannerContractError,
    candidate_errors as _shared_candidate_errors,
    canonical_normal_slots as _canonical_normal_slots,
    parse_date as _parse_date,
    parse_slot as _parse_slot,
    scheduled_adhoc_matches as _scheduled_adhoc_matches,
    validate_ranked_candidates as _validate_ranked_candidates,
)
from planning.planner_profiles import ADHOC, DAILY

CONTENT_ID_RE = __import__("common.workflow_common", fromlist=["CONTENT_ID_RE"]).CONTENT_ID_RE
DAILY_POOL_SIZE = DAILY.pool_size
ADHOC_POOL_SIZE = ADHOC.pool_size
LEGACY_DAILY_POOL_SIZE = 36
LEGACY_ADHOC_POOL_SIZE = 5
NORMAL_DAILY_TARGET = DAILY.normal_target_count
PLANNING_MODES = set(DAILY.planning_modes)
ADHOC_PLANNING_MODES = set(ADHOC.planning_modes)
HISTORICAL_ADHOC_PLANNING_MODES = {"scheduled_daily", "manual_on_demand"}
PromotionError = PlannerContractError


def _fail(message):
    raise PromotionError(message)


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"cannot read planning pool {path}: {exc}")


def _git(*args):
    try:
        return subprocess.check_output(
            ["git", *args], cwd=REPO_ROOT, text=True, stderr=subprocess.STDOUT
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        output = getattr(exc, "output", "") or ""
        _fail(f"git {' '.join(args)} failed: {output.strip() or type(exc).__name__}")


def _single_parent(source_sha):
    if not HEX40_RE.fullmatch(source_sha):
        _fail("candidate-pool source SHA must be a lowercase full commit SHA")
    parts = _git("rev-list", "--parents", "-n", "1", source_sha).split()
    if len(parts) != 2 or parts[0] != source_sha:
        _fail("candidate-pool commit must have exactly one parent")
    return parts[1]


def _validate_exact_pool_commit(source_sha, expected_path):
    raw = _git("diff-tree", "--no-commit-id", "--name-status", "-r", source_sha)
    changes = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            _fail("candidate-pool commit contains unsupported rename/copy diff")
        changes.append((parts[0], parts[1]))
    if changes != [("A", expected_path)]:
        _fail("candidate-pool commit must add exactly one immutable pool file")


def _validate_execution(pool, candidate_ids, source_sha):
    execution = pool.get("planning_execution")
    expected_keys = {
        "editorial_selection_owner",
        "planning_method",
        "rules_source_sha",
        "ranked_candidate_ids",
    }
    if not isinstance(execution, dict) or set(execution) != expected_keys:
        _fail("planning_execution must contain ranked-pool ChatGPT provenance")
    if execution.get("editorial_selection_owner") != "chatgpt":
        _fail("ranked planning requires editorial_selection_owner=chatgpt")
    if execution.get("planning_method") != "chatgpt_ranked_pool":
        _fail("ranked planning requires planning_method=chatgpt_ranked_pool")
    if execution.get("rules_source_sha") != _single_parent(source_sha):
        _fail("rules_source_sha must equal the candidate-pool commit parent SHA")
    if execution.get("ranked_candidate_ids") != candidate_ids:
        _fail("planning_execution.ranked_candidate_ids must exactly match candidate order")


def _pool_schema(pool):
    value = pool.get("schema_version") if isinstance(pool, dict) else None
    if value not in {LEGACY_POOL_SCHEMA_VERSION, POOL_SCHEMA_VERSION}:
        _fail(
            f"planning pool schema_version must be historical {LEGACY_POOL_SCHEMA_VERSION} "
            f"or current {POOL_SCHEMA_VERSION}"
        )
    return value


def _validate_daily_pool(pool, pool_path, source_sha, *, now_utc=None):
    match = DAILY_POOL_RE.fullmatch(pool_path)
    if not match:
        _fail("daily pool path must be content/planning-pools/daily/YYYY-MM-DD/dp-<id>.json")
    plan_date, pool_id = match.groups()
    _parse_date(plan_date, "daily plan_date")
    expected_keys = {
        "schema_version", "pool_type", "pool_id", "plan_date", "planning_mode",
        "target_count", "publication_slots", "planning_execution", "ranked_candidates",
    }
    if not isinstance(pool, dict) or set(pool) != expected_keys:
        _fail("daily planning pool contains missing or unexpected top-level fields")
    schema_version = _pool_schema(pool)
    if pool.get("pool_type") != DAILY.pool_type:
        _fail("daily planning pool type mismatch")
    if pool.get("pool_id") != pool_id:
        _fail("daily pool_id must match its filename")
    if pool.get("plan_date") != plan_date:
        _fail("daily pool plan_date must match its directory")
    mode = pool.get("planning_mode")
    if mode not in DAILY.planning_modes:
        _fail("daily planning_mode must be normal_next_day or same_day_catch_up")
    target = pool.get("target_count")
    if isinstance(target, bool) or not isinstance(target, int) or not 1 <= target <= 24:
        _fail("daily target_count must be an integer between 1 and 24")
    if mode == DAILY.normal_mode and target != DAILY.normal_target_count:
        _fail("normal_next_day planning pool target_count must be exactly 24")
    slots = pool.get("publication_slots")
    if not isinstance(slots, list) or len(slots) != target or len(slots) != len(set(slots)):
        _fail("publication_slots must contain exactly target_count unique slots")
    parsed_slots = [_parse_slot(raw, plan_date) for raw in slots]
    if parsed_slots != sorted(parsed_slots):
        _fail("publication_slots must be chronological")
    if mode == DAILY.normal_mode and slots != _canonical_normal_slots(plan_date):
        _fail("normal_next_day publication_slots must be the canonical 24 hourly slots")
    if mode == "same_day_catch_up":
        now_utc = now_utc or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)
        threshold = now_utc.astimezone(timezone.utc) + timedelta(minutes=CATCH_UP_MIN_LEAD_MINUTES)
        if any(slot < threshold for slot in parsed_slots):
            _fail(
                f"same_day_catch_up slots must remain at least {CATCH_UP_MIN_LEAD_MINUTES} "
                "minutes in the future at promotion time"
            )
    if schema_version == POOL_SCHEMA_VERSION:
        expected_count = target
        candidates, candidate_ids = _validate_ranked_candidates(
            pool, expected_count, require_background_category=True
        )
    else:
        expected_count = LEGACY_DAILY_POOL_SIZE
        candidates, candidate_ids = _validate_ranked_candidates(
            pool, expected_count, require_background_category=False
        )
    _validate_execution(pool, candidate_ids, source_sha)
    _validate_exact_pool_commit(source_sha, pool_path)
    return schema_version, plan_date, pool_id, mode, target, slots, candidates, candidate_ids


def _validate_adhoc_pool(pool, pool_path, source_sha):
    match = ADHOC_POOL_RE.fullmatch(pool_path)
    if not match:
        _fail("Ad-hoc pool path must be content/planning-pools/adhoc/ap-<id>.json")
    pool_id = match.group(1)
    expected_keys = {
        "schema_version", "pool_type", "pool_id", "planning_mode", "singapore_date",
        "target_count", "planning_execution", "ranked_candidates",
    }
    if not isinstance(pool, dict) or set(pool) != expected_keys:
        _fail("Ad-hoc planning pool contains missing or unexpected top-level fields")
    schema_version = _pool_schema(pool)
    if pool.get("pool_type") != ADHOC.pool_type:
        _fail("Ad-hoc planning pool type mismatch")
    if pool.get("pool_id") != pool_id:
        _fail("Ad-hoc pool_id must match its filename")
    planning_mode = pool.get("planning_mode")
    allowed = ADHOC.planning_modes if schema_version == POOL_SCHEMA_VERSION else HISTORICAL_ADHOC_PLANNING_MODES
    if planning_mode not in allowed:
        _fail(f"Ad-hoc planning_mode must be one of {sorted(allowed)}")
    singapore_date = str(pool.get("singapore_date", ""))
    _parse_date(singapore_date, "Ad-hoc singapore_date")
    if pool.get("target_count") != 1:
        _fail("Ad-hoc planning pool target_count must be exactly 1")
    if schema_version == POOL_SCHEMA_VERSION:
        candidates, candidate_ids = _validate_ranked_candidates(
            pool, 1, require_background_category=True
        )
    else:
        candidates, candidate_ids = _validate_ranked_candidates(
            pool, LEGACY_ADHOC_POOL_SIZE, require_background_category=False
        )
        if planning_mode == "scheduled_daily":
            prefix = f"wd-{singapore_date.replace('-', '')}T010000-adhoc-"
            for item in candidates:
                if not item["request"]["content_id"].startswith(prefix):
                    _fail("historical scheduled_daily Ad-hoc content IDs must use the 01:00 namespace")
    _validate_execution(pool, candidate_ids, source_sha)
    _validate_exact_pool_commit(source_sha, pool_path)
    return schema_version, pool_id, planning_mode, singapore_date, candidates, candidate_ids


def _candidate_errors(request, *, registry, request_path, profile, background_category=None):
    publish_at = None
    if profile is DAILY:
        publish_at = (request.get("publication") or {}).get("publish_at")
        authored = copy.deepcopy(request)
        authored["publication"] = copy.deepcopy(DAILY.publication_template)
    else:
        authored = request
    return _shared_candidate_errors(
        authored,
        registry=registry,
        request_path=request_path,
        profile=profile,
        publish_at_override=publish_at,
        background_category=background_category,
    )


def _ensure_targets_absent(paths):
    existing = [str(path) for path in paths if Path(path).exists()]
    if existing:
        _fail("immutable production target already exists: " + ", ".join(existing))


def verify_scheduled_adhoc_uniqueness(singapore_date, content_id):
    """Historical schema-v1 scheduled Ad-hoc compatibility only."""
    _parse_date(singapore_date, "Ad-hoc singapore_date")
    prefix = f"wd-{singapore_date.replace('-', '')}T010000-adhoc-"
    if not content_id.startswith(prefix):
        _fail("promoted historical scheduled Ad-hoc content ID does not match date namespace")
    conflicts = _scheduled_adhoc_matches(singapore_date, exclude_content_id=content_id)
    if conflicts:
        _fail(
            "historical scheduled Ad-hoc production already exists for this Singapore date: "
            + ", ".join(path.stem for path in conflicts)
        )


def promote_daily(pool_path, source_sha, summary_path, *, now_utc=None):
    pool_path = str(PurePath(pool_path))
    pool = _load_json(REPO_ROOT / pool_path)
    (
        schema_version,
        plan_date,
        pool_id,
        mode,
        target,
        slots,
        candidates,
        candidate_ids,
    ) = _validate_daily_pool(pool, pool_path, source_sha, now_utc=now_utc)
    try:
        registry = load_registry()
    except (OSError, TypeError, ValueError) as exc:
        _fail(f"private promotion preflight failed: background registry unavailable or invalid: {exc}")

    selected = []
    rejected = []
    if schema_version == POOL_SCHEMA_VERSION:
        # Current pools have no reserves: candidate N maps to slot N and every one
        # must pass deterministic validation. Promotion never searches for a substitute.
        for item, publish_at in zip(candidates, slots):
            request = copy.deepcopy(item["request"])
            content_id = request["content_id"]
            if request.get("publication") != DAILY.publication_template:
                rejected.append({
                    "rank": item["rank"],
                    "candidate_id": item["candidate_id"],
                    "errors": ["Daily publication must be the exact scheduled template with publish_at=null"],
                })
                continue
            request["publication"]["publish_at"] = publish_at
            planning = request.get("planning")
            if not isinstance(planning, dict) or planning.get("plan_date") != plan_date:
                rejected.append({
                    "rank": item["rank"],
                    "candidate_id": item["candidate_id"],
                    "errors": ["planning.plan_date must match planning pool"],
                })
                continue
            request_path = BOT_ROOT / "content" / "requests" / f"{content_id}.json"
            errors = _candidate_errors(
                request,
                registry=registry,
                request_path=request_path,
                profile=DAILY,
                background_category=item["background_category"],
            )
            if errors:
                rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": errors})
                continue
            selected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "request": request})
        if rejected or len(selected) != target:
            _fail(
                f"current Daily pool requires all {target} candidates to validate; "
                f"valid={len(selected)} failed={len(rejected)}"
            )
    else:
        # Historical schema-v1 compatibility: preserve the original first-target-valid
        # rank walk so immutable 36-candidate pools remain recoverable.
        for item in candidates:
            if len(selected) >= target:
                break
            request = copy.deepcopy(item["request"])
            content_id = request["content_id"]
            if request.get("publication") != DAILY.publication_template:
                rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": ["Daily publication template mismatch"]})
                continue
            request["publication"]["publish_at"] = slots[len(selected)]
            request_path = BOT_ROOT / "content" / "requests" / f"{content_id}.json"
            errors = _candidate_errors(request, registry=registry, request_path=request_path, profile=DAILY)
            if errors:
                rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": errors})
                continue
            selected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "request": request})
        if len(selected) != target:
            _fail(f"historical Daily pool produced only {len(selected)} valid candidates; {target} required")

    request_paths = [
        BOT_ROOT / "content" / "requests" / f"{item['request']['content_id']}.json"
        for item in selected
    ]
    plan_path = BOT_ROOT / "content" / "planning" / f"{plan_date}.json"
    _ensure_targets_absent([plan_path, *request_paths])

    selected_candidate_ids = [item["candidate_id"] for item in selected]
    selected_content_ids = [item["request"]["content_id"] for item in selected]
    execution = pool["planning_execution"]
    canonical_plan = {
        "plan_date": plan_date,
        "planning_mode": mode,
        "final_selected": target,
        "content_ids": selected_content_ids,
        "candidate_pool_id": pool_id,
        "candidate_pool_source_sha": source_sha,
        "candidate_pool_size": len(candidates),
        "candidate_pool_schema_version": schema_version,
        "rejected_candidate_ids": [item["candidate_id"] for item in rejected],
        "planning_execution": {
            "editorial_selection_owner": "chatgpt",
            "planning_method": "chatgpt_ranked_pool",
            "rules_source_sha": execution["rules_source_sha"],
            "candidate_pool_source_sha": source_sha,
            "ranked_candidate_ids": candidate_ids,
            "selected_candidate_ids": selected_candidate_ids,
        },
    }

    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(canonical_plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for target_path, item in zip(request_paths, selected):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(item["request"], indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "pool_type": "daily",
        "pool_schema_version": schema_version,
        "pool_id": pool_id,
        "pool_source_sha": source_sha,
        "target_count": target,
        "selected_content_ids": selected_content_ids,
        "selected_candidate_ids": selected_candidate_ids,
        "rejected": rejected,
        "plan_path": plan_path.relative_to(REPO_ROOT).as_posix(),
    }
    Path(summary_path).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def promote_adhoc(pool_path, source_sha, summary_path):
    pool_path = str(PurePath(pool_path))
    pool = _load_json(REPO_ROOT / pool_path)
    schema_version, pool_id, planning_mode, singapore_date, candidates, candidate_ids = _validate_adhoc_pool(
        pool, pool_path, source_sha
    )
    if schema_version == LEGACY_POOL_SCHEMA_VERSION and planning_mode == "scheduled_daily" and _scheduled_adhoc_matches(singapore_date):
        _fail("historical scheduled Ad-hoc production already exists for this Singapore date")
    try:
        registry = load_registry()
    except (OSError, TypeError, ValueError) as exc:
        _fail(f"private promotion preflight failed: background registry unavailable or invalid: {exc}")

    selected = None
    rejected = []
    if schema_version == POOL_SCHEMA_VERSION:
        item = candidates[0]
        request = copy.deepcopy(item["request"])
        content_id = request["content_id"]
        if request.get("publication") != ADHOC.publication_template:
            _fail("current Ad-hoc candidate publication must be immediate public")
        request_path = BOT_ROOT / "content" / "requests" / f"{content_id}.json"
        errors = _candidate_errors(
            request,
            registry=registry,
            request_path=request_path,
            profile=ADHOC,
            background_category=item["background_category"],
        )
        if errors:
            _fail("current Ad-hoc single candidate failed deterministic validation: " + "; ".join(errors))
        selected = {"rank": item["rank"], "candidate_id": item["candidate_id"], "request": request}
    else:
        # Historical schema-v1 compatibility preserves first-valid-of-five behavior.
        for item in candidates:
            request = copy.deepcopy(item["request"])
            content_id = request["content_id"]
            if request.get("publication") != ADHOC.publication_template:
                rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": ["Ad-hoc publication must be immediate public"]})
                continue
            request_path = BOT_ROOT / "content" / "requests" / f"{content_id}.json"
            errors = _candidate_errors(request, registry=registry, request_path=request_path, profile=ADHOC)
            if errors:
                rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": errors})
                continue
            selected = {"rank": item["rank"], "candidate_id": item["candidate_id"], "request": request}
            break
        if selected is None:
            _fail("historical Ad-hoc pool contains no valid candidate")

    request_path = BOT_ROOT / "content" / "requests" / f"{selected['request']['content_id']}.json"
    _ensure_targets_absent([request_path])
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(selected["request"], indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if schema_version == LEGACY_POOL_SCHEMA_VERSION and planning_mode == "scheduled_daily":
        verify_scheduled_adhoc_uniqueness(singapore_date, selected["request"]["content_id"])

    summary = {
        "pool_type": "adhoc",
        "pool_schema_version": schema_version,
        "pool_id": pool_id,
        "planning_mode": planning_mode,
        "singapore_date": singapore_date,
        "pool_source_sha": source_sha,
        "selected_content_id": selected["request"]["content_id"],
        "selected_candidate_id": selected["candidate_id"],
        "ranked_candidate_ids": candidate_ids,
        "rejected": rejected,
        "request_path": request_path.relative_to(REPO_ROOT).as_posix(),
    }
    Path(summary_path).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("daily", "adhoc"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--pool", required=True)
        sub.add_argument("--source-sha", required=True)
        sub.add_argument("--summary", required=True)
    verify = subparsers.add_parser("verify-adhoc")
    verify.add_argument("--singapore-date", required=True)
    verify.add_argument("--content-id", required=True)
    args = parser.parse_args()
    try:
        if args.command == "daily":
            result = promote_daily(args.pool, args.source_sha, args.summary)
        elif args.command == "adhoc":
            result = promote_adhoc(args.pool, args.source_sha, args.summary)
        else:
            verify_scheduled_adhoc_uniqueness(args.singapore_date, args.content_id)
            result = {
                "singapore_date": args.singapore_date,
                "content_id": args.content_id,
                "unique": True,
            }
    except PromotionError as exc:
        raise SystemExit(f"planning promotion failed closed: {exc}") from exc
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
