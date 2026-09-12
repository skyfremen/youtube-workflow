"""Fail-closed promotion of ChatGPT-ranked production candidate pools.

ChatGPT owns editorial ranking, logical background choice, fallback choice, and
background treatment authoring. This module performs only mechanical validation
and promotion: it validates every candidate against the current private contract
and preserves ChatGPT's frozen rank when choosing the first valid production
items.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from media.validate_media_library import load_registry
from planning.planning_config import (
    ADHOC_RANKED_POOL_COUNT,
    CANONICAL_TIMEZONE,
    DAILY_PUBLISH_COUNT,
    DAILY_RANKED_POOL_COUNT,
)
from publishing.upload import build_upload_body
from validation.validate_content import SCHEMA_VERSION, validate_request_data

REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
DAILY_POOL_RE = re.compile(
    r"^youtube-shorts-bot/content/candidate-pools/daily/(\d{4}-\d{2}-\d{2})\.json$"
)
ADHOC_POOL_RE = re.compile(
    r"^youtube-shorts-bot/content/candidate-pools/adhoc/(ap-[A-Za-z0-9-]{8,96})\.json$"
)
CONTENT_ID_RE = re.compile(r"^wd-[A-Za-z0-9-]+$")
CANDIDATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SINGAPORE = ZoneInfo(CANONICAL_TIMEZONE)
POOL_SCHEMA_VERSION = 1
DAILY_POOL_KEYS = {
    "schema_version",
    "pool_type",
    "plan_date",
    "planning_mode",
    "target_count",
    "rules_source_sha",
    "publication_slots",
    "candidates",
}
ADHOC_POOL_KEYS = {
    "schema_version",
    "pool_type",
    "pool_id",
    "rules_source_sha",
    "candidates",
}
CANDIDATE_KEYS = {"rank", "candidate_id", "request"}


class CandidatePoolError(RuntimeError):
    pass


def _fail(message: str):
    raise CandidatePoolError(message)


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=REPO_ROOT, text=True, stderr=subprocess.STDOUT
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        output = getattr(exc, "output", "") or ""
        _fail(f"git {' '.join(args)} failed: {output.strip() or type(exc).__name__}")


def _single_parent(source_sha: str) -> str:
    line = _git("rev-list", "--parents", "-n", "1", source_sha)
    parts = line.split()
    if len(parts) != 2 or parts[0] != source_sha:
        _fail("candidate-pool commit must have exactly one parent")
    return parts[1]


def _changed_paths(source_sha: str):
    raw = _git("diff-tree", "--no-commit-id", "--name-status", "-r", source_sha)
    changes = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            _fail("candidate-pool commit contains unsupported rename/copy diff")
        changes.append((parts[0], parts[1]))
    return changes


def _pool_path(source_sha: str, pool_type: str) -> str:
    changes = _changed_paths(source_sha)
    if len(changes) != 1 or changes[0][0] != "A":
        _fail("candidate-pool commit must add exactly one immutable pool file")
    path = changes[0][1]
    matcher = DAILY_POOL_RE if pool_type == "daily" else ADHOC_POOL_RE
    if not matcher.fullmatch(path):
        _fail(f"candidate-pool commit does not contain one canonical {pool_type} pool")
    return path


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"cannot read candidate pool {path}: {exc}")


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _validate_source(source_sha: str, rules_source_sha: str):
    if not HEX40.fullmatch(source_sha):
        _fail("candidate-pool source SHA must be a lowercase 40-character SHA")
    parent = _single_parent(source_sha)
    if rules_source_sha != parent:
        _fail("rules_source_sha must equal the candidate-pool commit parent SHA")
    return parent


def _validate_candidate_envelopes(candidates, expected_count: int):
    if not isinstance(candidates, list) or len(candidates) != expected_count:
        _fail(f"ranked candidate pool must contain exactly {expected_count} candidates")
    ranks = []
    candidate_ids = []
    content_ids = []
    for index, item in enumerate(candidates, 1):
        if not isinstance(item, dict) or set(item) != CANDIDATE_KEYS:
            _fail(f"candidate {index} must contain exactly rank, candidate_id, request")
        rank = item.get("rank")
        if isinstance(rank, bool) or not isinstance(rank, int):
            _fail(f"candidate {index} rank must be an integer")
        candidate_id = str(item.get("candidate_id") or "")
        if not CANDIDATE_ID_RE.fullmatch(candidate_id):
            _fail(f"candidate {index} has invalid candidate_id")
        request = item.get("request")
        if not isinstance(request, dict):
            _fail(f"candidate {index} request must be an object")
        content_id = str(request.get("content_id") or "")
        if not CONTENT_ID_RE.fullmatch(content_id):
            _fail(f"candidate {index} has invalid request content_id")
        ranks.append(rank)
        candidate_ids.append(candidate_id)
        content_ids.append(content_id)
    if ranks != list(range(1, expected_count + 1)):
        _fail("candidate ranks must be exactly contiguous 1..N in frozen ChatGPT order")
    if len(candidate_ids) != len(set(candidate_ids)):
        _fail("candidate_id values must be unique")
    if len(content_ids) != len(set(content_ids)):
        _fail("candidate request content_id values must be unique")
    return candidate_ids, content_ids


def _parse_daily_slots(plan_date: str, planning_mode: str, slots, target_count: int):
    if planning_mode not in {"normal_next_day", "same_day_catch_up"}:
        _fail("planning_mode must be normal_next_day or same_day_catch_up")
    if not isinstance(slots, list) or not slots:
        _fail("publication_slots must be a non-empty array")
    if not isinstance(target_count, int) or isinstance(target_count, bool):
        _fail("target_count must be an integer")
    if target_count != len(slots) or not 1 <= target_count <= DAILY_PUBLISH_COUNT:
        _fail("target_count must exactly match 1-24 publication_slots")
    parsed = []
    seen = set()
    for index, raw in enumerate(slots, 1):
        if not isinstance(raw, str) or not raw.endswith("Z") or raw in seen:
            _fail(f"publication_slots[{index}] must be a unique RFC3339 UTC timestamp ending Z")
        seen.add(raw)
        try:
            instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            _fail(f"publication_slots[{index}] is invalid")
        if instant.utcoffset() != timedelta(0):
            _fail(f"publication_slots[{index}] must be UTC")
        local = instant.astimezone(SINGAPORE)
        if local.date().isoformat() != plan_date or any((local.minute, local.second, local.microsecond)):
            _fail("Daily publication slots must be exact Singapore top-of-hour slots on plan_date")
        parsed.append((instant, raw, local.hour))
    parsed.sort(key=lambda item: item[0])
    if planning_mode == "normal_next_day":
        if target_count != DAILY_PUBLISH_COUNT or {item[2] for item in parsed} != set(range(24)):
            _fail("normal_next_day requires all 24 Singapore hourly slots")
        return [item[1] for item in parsed]

    # Catch-up remains mechanical: a delayed workflow must never revive a slot that
    # is no longer at least 30 minutes in the future.
    cutoff = datetime.now(timezone.utc) + timedelta(minutes=30)
    safe = [item[1] for item in parsed if item[0] >= cutoff]
    if not safe:
        _fail("same_day_catch_up has no safely future publication slots remaining")
    return safe


def _candidate_errors(request, registry, *, publication=None):
    candidate = copy.deepcopy(request)
    if publication is not None:
        candidate["publication"] = copy.deepcopy(publication)
    errors = validate_request_data(candidate, registry_data=registry)
    if not errors:
        try:
            build_upload_body(candidate, require_future=False)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"final publication payload is invalid: {exc}")
    return candidate, errors


def _existing_source_commit(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT).as_posix()
    commits = _git("log", "--diff-filter=A", "--format=%H", "--", relative).splitlines()
    if not commits:
        _fail(f"cannot resolve immutable source commit for {relative}")
    return commits[-1]


def _write_output(path: str, payload):
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def promote_daily(source_sha: str, output: str):
    pool_rel = _pool_path(source_sha, "daily")
    pool = _load_json(REPO_ROOT / pool_rel)
    if not isinstance(pool, dict) or set(pool) != DAILY_POOL_KEYS:
        _fail("Daily candidate pool has an invalid root contract")
    if pool.get("schema_version") != POOL_SCHEMA_VERSION or pool.get("pool_type") != "daily":
        _fail("Daily candidate pool schema/type mismatch")
    match = DAILY_POOL_RE.fullmatch(pool_rel)
    plan_date = match.group(1)
    if pool.get("plan_date") != plan_date:
        _fail("Daily pool plan_date must match its canonical filename")
    try:
        datetime.fromisoformat(plan_date)
    except ValueError:
        _fail("Daily pool plan_date is invalid")
    _validate_source(source_sha, str(pool.get("rules_source_sha") or ""))
    ranked_ids, _content_ids = _validate_candidate_envelopes(
        pool.get("candidates"), DAILY_RANKED_POOL_COUNT
    )
    slots = _parse_daily_slots(
        plan_date,
        str(pool.get("planning_mode") or ""),
        pool.get("publication_slots"),
        pool.get("target_count"),
    )
    target_count = len(slots)
    registry = load_registry()

    valid = []
    rejected = []
    probe_publication = {
        "mode": "scheduled",
        "timezone": CANONICAL_TIMEZONE,
        "publish_at": slots[0],
    }
    for item in pool["candidates"]:
        request = item["request"]
        if request.get("schema_version") != SCHEMA_VERSION:
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": [f"schema_version must be {SCHEMA_VERSION}"]})
            continue
        if (request.get("planning") or {}).get("plan_date") != plan_date:
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": ["planning.plan_date mismatch"]})
            continue
        if request.get("publication") != {
            "mode": "scheduled",
            "timezone": CANONICAL_TIMEZONE,
            "publish_at": None,
        }:
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": ["Daily candidate publication must be the scheduled null-slot template"]})
            continue
        candidate, errors = _candidate_errors(
            request, registry, publication=probe_publication
        )
        if errors:
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": errors})
        else:
            valid.append((item, candidate))

    if len(valid) < target_count:
        _fail(
            f"only {len(valid)} of {DAILY_RANKED_POOL_COUNT} Daily candidates passed strict validation; "
            f"{target_count} are required"
        )
    selected = valid[:target_count]
    final_requests = []
    selected_candidate_ids = []
    for slot, (item, request) in zip(slots, selected):
        request = copy.deepcopy(request)
        request["publication"] = {
            "mode": "scheduled",
            "timezone": CANONICAL_TIMEZONE,
            "publish_at": slot,
        }
        errors = validate_request_data(request, registry_data=registry)
        if not errors:
            try:
                build_upload_body(request, require_future=False)
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f"final publication payload is invalid: {exc}")
        if errors:
            _fail(
                f"promoted Daily candidate rank {item['rank']} failed final validation: "
                + "; ".join(errors)
            )
        final_requests.append(request)
        selected_candidate_ids.append(item["candidate_id"])

    content_ids = [request["content_id"] for request in final_requests]
    plan = {
        "plan_date": plan_date,
        "planning_mode": pool["planning_mode"],
        "final_selected": len(final_requests),
        "content_ids": content_ids,
        "planning_execution": {
            "editorial_selection_owner": "chatgpt",
            "planning_method": "chatgpt_ranked_pool",
            "rules_source_sha": pool["rules_source_sha"],
            "candidate_pool_source_sha": source_sha,
            "ranked_candidate_ids": ranked_ids,
            "selected_candidate_ids": selected_candidate_ids,
        },
        "candidate_pool": {
            "source_sha": source_sha,
            "candidate_count": DAILY_RANKED_POOL_COUNT,
            "target_count": target_count,
            "selected_ranks": [item["rank"] for item, _request in selected],
            "rejected_candidates": rejected,
        },
    }
    plan_path = BOT_ROOT / "content" / "planning" / f"{plan_date}.json"

    if plan_path.exists():
        existing = _load_json(plan_path)
        if (existing.get("candidate_pool") or {}).get("source_sha") != source_sha:
            _fail("canonical Daily plan already exists for this date from another source")
        if existing.get("content_ids") != content_ids:
            _fail("existing promoted Daily plan differs from deterministic promotion")
        for request in final_requests:
            target = BOT_ROOT / "content" / "requests" / f"{request['content_id']}.json"
            if not target.is_file() or _load_json(target) != request:
                _fail("existing promoted Daily request differs from deterministic promotion")
        payload = {
            "pool_path": pool_rel,
            "plan_path": plan_path.relative_to(REPO_ROOT).as_posix(),
            "request_paths": [
                (BOT_ROOT / "content" / "requests" / f"{content_id}.json").relative_to(REPO_ROOT).as_posix()
                for content_id in content_ids
            ],
            "content_ids": content_ids,
            "selected_candidate_ids": selected_candidate_ids,
            "target_count": target_count,
            "reused": True,
            "production_source_sha": _existing_source_commit(plan_path),
        }
        _write_output(output, payload)
        return payload

    request_paths = []
    for request in final_requests:
        target = BOT_ROOT / "content" / "requests" / f"{request['content_id']}.json"
        if target.exists():
            _fail(f"immutable request already exists: {request['content_id']}")
        _write_json(target, request)
        request_paths.append(target.relative_to(REPO_ROOT).as_posix())
    _write_json(plan_path, plan)
    payload = {
        "pool_path": pool_rel,
        "plan_path": plan_path.relative_to(REPO_ROOT).as_posix(),
        "request_paths": request_paths,
        "content_ids": content_ids,
        "selected_candidate_ids": selected_candidate_ids,
        "target_count": target_count,
        "reused": False,
        "production_source_sha": None,
    }
    _write_output(output, payload)
    return payload


def promote_adhoc(source_sha: str, output: str):
    pool_rel = _pool_path(source_sha, "adhoc")
    pool = _load_json(REPO_ROOT / pool_rel)
    if not isinstance(pool, dict) or set(pool) != ADHOC_POOL_KEYS:
        _fail("Ad-hoc candidate pool has an invalid root contract")
    if pool.get("schema_version") != POOL_SCHEMA_VERSION or pool.get("pool_type") != "adhoc":
        _fail("Ad-hoc candidate pool schema/type mismatch")
    match = ADHOC_POOL_RE.fullmatch(pool_rel)
    if pool.get("pool_id") != match.group(1):
        _fail("Ad-hoc pool_id must match its canonical filename")
    _validate_source(source_sha, str(pool.get("rules_source_sha") or ""))
    _ranked_ids, _content_ids = _validate_candidate_envelopes(
        pool.get("candidates"), ADHOC_RANKED_POOL_COUNT
    )
    registry = load_registry()

    valid = []
    rejected = []
    expected_publication = {
        "mode": "immediate",
        "timezone": CANONICAL_TIMEZONE,
        "publish_at": None,
    }
    for item in pool["candidates"]:
        request = item["request"]
        if request.get("schema_version") != SCHEMA_VERSION:
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": [f"schema_version must be {SCHEMA_VERSION}"]})
            continue
        if request.get("publication") != expected_publication:
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": ["Ad-hoc candidate must use immediate-public publication"]})
            continue
        content_id = str(request.get("content_id") or "")
        if "-adhoc-" not in f"-{content_id.lower()}-":
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": ["Ad-hoc content_id must contain the adhoc identity marker"]})
            continue
        candidate, errors = _candidate_errors(request, registry)
        if errors:
            rejected.append({"rank": item["rank"], "candidate_id": item["candidate_id"], "errors": errors})
        else:
            valid.append((item, candidate))

    if not valid:
        _fail(f"none of the {ADHOC_RANKED_POOL_COUNT} Ad-hoc candidates passed strict validation")
    item, request = valid[0]
    target = BOT_ROOT / "content" / "requests" / f"{request['content_id']}.json"
    if target.exists():
        if _load_json(target) != request:
            _fail("existing promoted Ad-hoc request differs from deterministic promotion")
        payload = {
            "pool_path": pool_rel,
            "request_path": target.relative_to(REPO_ROOT).as_posix(),
            "content_id": request["content_id"],
            "selected_candidate_id": item["candidate_id"],
            "selected_rank": item["rank"],
            "rejected_candidates": rejected,
            "reused": True,
            "request_source_sha": _existing_source_commit(target),
        }
        _write_output(output, payload)
        return payload

    _write_json(target, request)
    payload = {
        "pool_path": pool_rel,
        "request_path": target.relative_to(REPO_ROOT).as_posix(),
        "content_id": request["content_id"],
        "selected_candidate_id": item["candidate_id"],
        "selected_rank": item["rank"],
        "rejected_candidates": rejected,
        "reused": False,
        "request_source_sha": None,
    }
    _write_output(output, payload)
    return payload


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("promote-daily", "promote-adhoc"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--source-sha", required=True)
        sub.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "promote-daily":
            promote_daily(args.source_sha, args.output)
        else:
            promote_adhoc(args.source_sha, args.output)
    except (CandidatePoolError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"candidate pool promotion failed closed: {exc}") from exc


if __name__ == "__main__":
    main()
