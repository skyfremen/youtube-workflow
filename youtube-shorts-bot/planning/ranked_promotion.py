"""Promote immutable ChatGPT-ranked planning pools into canonical production state.

ChatGPT owns creative/editorial decisions, logical background choice, planning-time
background audit reasoning, background treatment values and final rank. This module
is a private fail-closed promotion gate: it validates facts, preserves the declared
rank order, and materializes only the first required valid candidates.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath as PurePath
from zoneinfo import ZoneInfo

from media.validate_media_library import load_registry
from publishing.upload import build_upload_body
from validation.validate_content import SCHEMA_VERSION, validate_request_data

REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
DAILY_POOL_RE = re.compile(
    r"^youtube-shorts-bot/content/planning-pools/daily/"
    r"(\d{4}-\d{2}-\d{2})/(dp-[A-Za-z0-9-]{8,96})\.json$"
)
ADHOC_POOL_RE = re.compile(
    r"^youtube-shorts-bot/content/planning-pools/adhoc/(ap-[A-Za-z0-9-]{8,96})\.json$"
)
CONTENT_ID_RE = re.compile(r"^wd-[A-Za-z0-9-]+$")
CANDIDATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
DAILY_POOL_SIZE = 36
ADHOC_POOL_SIZE = 5
NORMAL_DAILY_TARGET = 24
POOL_SCHEMA_VERSION = 1
PLANNING_MODES = {"normal_next_day", "same_day_catch_up"}
ADHOC_PLANNING_MODES = {"scheduled_daily", "manual_on_demand"}
CATCH_UP_MIN_LEAD_MINUTES = 30
SGT = ZoneInfo("Asia/Singapore")


class PromotionError(RuntimeError):
    pass


def _fail(message):
    raise PromotionError(message)


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"cannot read ranked pool {path}: {exc}")


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


def _validate_ranked_candidates(pool, expected_count):
    candidates = pool.get("ranked_candidates")
    if not isinstance(candidates, list) or len(candidates) != expected_count:
        _fail(f"ranked_candidates must contain exactly {expected_count} candidates")
    candidate_ids = []
    content_ids = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, dict) or set(item) != {"rank", "candidate_id", "request"}:
            _fail("each ranked candidate must contain exactly rank, candidate_id and request")
        if item.get("rank") != index:
            _fail("candidate ranks must be contiguous and start at 1")
        candidate_id = item.get("candidate_id")
        if not isinstance(candidate_id, str) or not CANDIDATE_ID_RE.fullmatch(candidate_id):
            _fail(f"candidate rank {index} has invalid candidate_id")
        request = item.get("request")
        if not isinstance(request, dict):
            _fail(f"candidate rank {index} request must be an object")
        content_id = request.get("content_id")
        if not isinstance(content_id, str) or not CONTENT_ID_RE.fullmatch(content_id):
            _fail(f"candidate rank {index} request has invalid content_id")
        candidate_ids.append(candidate_id)
        content_ids.append(content_id)
    if len(candidate_ids) != len(set(candidate_ids)):
        _fail("ranked candidate IDs must be unique")
    if len(content_ids) != len(set(content_ids)):
        _fail("ranked candidate request content IDs must be unique")
    return candidates, candidate_ids


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
        _fail("planning_execution.ranked_candidate_ids must exactly match rank order")


def _parse_date(raw, label):
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        _fail(f"{label} must be YYYY-MM-DD")


def _parse_slot(raw, plan_date):
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        _fail(f"invalid publication slot {raw!r}")
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        _fail("daily publication slots must be UTC timestamps")
    local = parsed.astimezone(SGT)
    if local.date().isoformat() != plan_date:
        _fail("daily publication slot must fall on the plan date in Asia/Singapore")
    if any((local.minute, local.second, local.microsecond)):
        _fail("daily publication slots must be exact top-of-hour timestamps")
    return parsed


def _canonical_normal_slots(plan_date):
    local_midnight = datetime.fromisoformat(plan_date).replace(tzinfo=SGT)
    return [
        local_midnight.replace(hour=hour).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        for hour in range(24)
    ]


def _validate_daily_pool(pool, pool_path, source_sha, *, now_utc=None):
    match = DAILY_POOL_RE.fullmatch(pool_path)
    if not match:
        _fail("daily pool path must be content/planning-pools/daily/YYYY-MM-DD/dp-<id>.json")
    plan_date, pool_id = match.groups()
    _parse_date(plan_date, "daily plan_date")
    expected_keys = {
        "schema_version",
        "pool_type",
        "pool_id",
        "plan_date",
        "planning_mode",
        "target_count",
        "publication_slots",
        "planning_execution",
        "ranked_candidates",
    }
    if not isinstance(pool, dict) or set(pool) != expected_keys:
        _fail("daily ranked pool contains missing or unexpected top-level fields")
    if pool.get("schema_version") != POOL_SCHEMA_VERSION or pool.get("pool_type") != "daily":
        _fail("daily ranked pool schema/type mismatch")
    if pool.get("pool_id") != pool_id:
        _fail("daily pool_id must match its filename")
    if pool.get("plan_date") != plan_date:
        _fail("daily pool plan_date must match its directory")
    mode = pool.get("planning_mode")
    if mode not in PLANNING_MODES:
        _fail("daily planning_mode must be normal_next_day or same_day_catch_up")
    target = pool.get("target_count")
    if isinstance(target, bool) or not isinstance(target, int) or not 1 <= target <= 24:
        _fail("daily target_count must be an integer between 1 and 24")
    if mode == "normal_next_day" and target != NORMAL_DAILY_TARGET:
        _fail("normal_next_day ranked pool target_count must be exactly 24")
    slots = pool.get("publication_slots")
    if not isinstance(slots, list) or len(slots) != target or len(slots) != len(set(slots)):
        _fail("publication_slots must contain exactly target_count unique slots")
    parsed_slots = [_parse_slot(raw, plan_date) for raw in slots]
    if parsed_slots != sorted(parsed_slots):
        _fail("publication_slots must be chronological")
    if mode == "normal_next_day" and slots != _canonical_normal_slots(plan_date):
        _fail("normal_next_day publication_slots must be the canonical 24 hourly slots")
    if mode == "same_day_catch_up":
        now_utc = now_utc or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)
        now_utc = now_utc.astimezone(timezone.utc)
        threshold = now_utc + timedelta(minutes=CATCH_UP_MIN_LEAD_MINUTES)
        if any(slot < threshold for slot in parsed_slots):
            _fail(
                f"same_day_catch_up slots must remain at least {CATCH_UP_MIN_LEAD_MINUTES} "
                "minutes in the future at promotion time"
            )
    candidates, candidate_ids = _validate_ranked_candidates(pool, DAILY_POOL_SIZE)
    _validate_execution(pool, candidate_ids, source_sha)
    _validate_exact_pool_commit(source_sha, pool_path)
    return plan_date, pool_id, mode, target, slots, candidates, candidate_ids


def _validate_adhoc_pool(pool, pool_path, source_sha):
    match = ADHOC_POOL_RE.fullmatch(pool_path)
    if not match:
        _fail("Ad-hoc pool path must be content/planning-pools/adhoc/ap-<id>.json")
    pool_id = match.group(1)
    expected_keys = {
        "schema_version",
        "pool_type",
        "pool_id",
        "planning_mode",
        "singapore_date",
        "target_count",
        "planning_execution",
        "ranked_candidates",
    }
    if not isinstance(pool, dict) or set(pool) != expected_keys:
        _fail("Ad-hoc ranked pool contains missing or unexpected top-level fields")
    if pool.get("schema_version") != POOL_SCHEMA_VERSION or pool.get("pool_type") != "adhoc":
        _fail("Ad-hoc ranked pool schema/type mismatch")
    if pool.get("pool_id") != pool_id:
        _fail("Ad-hoc pool_id must match its filename")
    planning_mode = pool.get("planning_mode")
    if planning_mode not in ADHOC_PLANNING_MODES:
        _fail("Ad-hoc planning_mode must be scheduled_daily or manual_on_demand")
    singapore_date = str(pool.get("singapore_date", ""))
    _parse_date(singapore_date, "Ad-hoc singapore_date")
    if pool.get("target_count") != 1:
        _fail("Ad-hoc ranked pool target_count must be exactly 1")
    candidates, candidate_ids = _validate_ranked_candidates(pool, ADHOC_POOL_SIZE)
    if planning_mode == "scheduled_daily":
        prefix = f"wd-{singapore_date.replace('-', '')}T010000-adhoc-"
        for item in candidates:
            if not item["request"]["content_id"].startswith(prefix):
                _fail("scheduled_daily Ad-hoc content IDs must use the Singapore-date 01:00 namespace")
    _validate_execution(pool, candidate_ids, source_sha)
    _validate_exact_pool_commit(source_sha, pool_path)
    return pool_id, planning_mode, singapore_date, candidates, candidate_ids


def _candidate_errors(request, *, registry, request_path):
    errors = validate_request_data(
        request,
        request_path=request_path,
        enforce_registry=True,
        registry=registry,
    )
    if request.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"new production request must use schema-v{SCHEMA_VERSION}")
    if not errors:
        try:
            build_upload_body(request, require_future=False)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"final publication payload is invalid: {exc}")
    return errors


def _ensure_targets_absent(paths):
    existing = [str(path) for path in paths if Path(path).exists()]
    if existing:
        _fail("immutable production target already exists: " + ", ".join(existing))


def _scheduled_adhoc_matches(singapore_date, *, exclude_content_id=None):
    prefix = f"wd-{singapore_date.replace('-', '')}T010000-adhoc-"
    request_dir = BOT_ROOT / "content" / "requests"
    matches = []
    if request_dir.is_dir():
        for path in request_dir.glob(f"{prefix}*.json"):
            if exclude_content_id and path.stem == exclude_content_id:
                continue
            matches.append(path)
    return sorted(matches)


def verify_scheduled_adhoc_uniqueness(singapore_date, content_id):
    """Fail if another scheduled Ad-hoc request already exists for the SG date."""
    _parse_date(singapore_date, "Ad-hoc singapore_date")
    prefix = f"wd-{singapore_date.replace('-', '')}T010000-adhoc-"
    if not content_id.startswith(prefix):
        _fail("promoted scheduled Ad-hoc content ID does not match the Singapore-date namespace")
    conflicts = _scheduled_adhoc_matches(
        singapore_date, exclude_content_id=content_id
    )
    if conflicts:
        _fail(
            "scheduled Ad-hoc production already exists for this Singapore date: "
            + ", ".join(path.stem for path in conflicts)
        )


def promote_daily(pool_path, source_sha, summary_path, *, now_utc=None):
    pool_path = str(PurePath(pool_path))
    pool = _load_json(REPO_ROOT / pool_path)
    plan_date, pool_id, mode, target, slots, candidates, candidate_ids = _validate_daily_pool(
        pool, pool_path, source_sha, now_utc=now_utc
    )
    try:
        registry = load_registry()
    except (OSError, TypeError, ValueError) as exc:
        _fail(f"private promotion preflight failed: background registry unavailable or invalid: {exc}")

    selected = []
    rejected = []
    expected_template = {
        "mode": "scheduled",
        "timezone": "Asia/Singapore",
        "publish_at": None,
    }
    for item in candidates:
        if len(selected) >= target:
            break
        request = copy.deepcopy(item["request"])
        content_id = request["content_id"]
        if request.get("publication") != expected_template:
            rejected.append({
                "rank": item["rank"],
                "candidate_id": item["candidate_id"],
                "errors": ["Daily publication must be the exact scheduled template with publish_at=null"],
            })
            continue
        request["publication"]["publish_at"] = slots[len(selected)]
        planning = request.get("planning")
        if not isinstance(planning, dict) or planning.get("plan_date") != plan_date:
            rejected.append({
                "rank": item["rank"],
                "candidate_id": item["candidate_id"],
                "errors": ["planning.plan_date must match ranked pool"],
            })
            continue
        request_path = BOT_ROOT / "content" / "requests" / f"{content_id}.json"
        errors = _candidate_errors(request, registry=registry, request_path=request_path)
        if errors:
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": errors})
            continue
        selected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "request": request})

    if len(selected) != target:
        _fail(f"ranked Daily pool produced only {len(selected)} valid candidates; {target} required")

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
        "candidate_pool_size": DAILY_POOL_SIZE,
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
    pool_id, planning_mode, singapore_date, candidates, candidate_ids = _validate_adhoc_pool(
        pool, pool_path, source_sha
    )
    if planning_mode == "scheduled_daily" and _scheduled_adhoc_matches(singapore_date):
        _fail("scheduled Ad-hoc production already exists for this Singapore date")
    try:
        registry = load_registry()
    except (OSError, TypeError, ValueError) as exc:
        _fail(f"private promotion preflight failed: background registry unavailable or invalid: {exc}")

    selected = None
    rejected = []
    for item in candidates:
        request = copy.deepcopy(item["request"])
        content_id = request["content_id"]
        if "-adhoc-" not in content_id.lower():
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": ["Ad-hoc content_id must contain -adhoc-"]})
            continue
        if request.get("publication") != {
            "mode": "immediate",
            "timezone": "Asia/Singapore",
            "publish_at": None,
        }:
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": ["Ad-hoc publication must be immediate public"]})
            continue
        request_path = BOT_ROOT / "content" / "requests" / f"{content_id}.json"
        errors = _candidate_errors(request, registry=registry, request_path=request_path)
        if errors:
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": errors})
            continue
        selected = {"rank": item["rank"], "candidate_id": item["candidate_id"], "request": request}
        break

    if selected is None:
        _fail("ranked Ad-hoc pool contains no valid candidate")

    request_path = BOT_ROOT / "content" / "requests" / f"{selected['request']['content_id']}.json"
    _ensure_targets_absent([request_path])
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(selected["request"], indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if planning_mode == "scheduled_daily":
        verify_scheduled_adhoc_uniqueness(singapore_date, selected["request"]["content_id"])

    summary = {
        "pool_type": "adhoc",
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
            result = {"singapore_date": args.singapore_date, "content_id": args.content_id, "unique": True}
    except PromotionError as exc:
        raise SystemExit(f"ranked promotion failed closed: {exc}") from exc
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
