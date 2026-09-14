"""Shared fail-closed pre-commit engine for current Daily and Ad-hoc pools.

ChatGPT/Work owns semantic/editorial decisions. This module validates only the
frozen authored pool and selected assets. It never generates, repairs, substitutes,
replenishes, reranks, or performs global media-readiness gating.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import time
from pathlib import Path

from media.validate_media_library import load_registry
from planning.planner_core import (
    ADHOC_POOL_RE,
    BOT_ROOT,
    DAILY_POOL_RE,
    HEX40_RE,
    POOL_SCHEMA_VERSION,
    PlannerContractError,
    candidate_errors,
    expected_candidate_count,
    parse_date,
    validate_daily_slots,
    validate_planning_execution,
    validate_ranked_candidates,
)
from planning.planner_profiles import DAILY, PlannerProfile, get_profile
from validation.validate_content import SCHEMA_VERSION

BASE_POOL_KEYS = {
    "schema_version",
    "pool_type",
    "pool_id",
    "planning_mode",
    "target_count",
    "planning_execution",
    "ranked_candidates",
}


def _current_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=BOT_ROOT.parent,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        output = getattr(exc, "output", "") or ""
        raise PlannerContractError(
            f"cannot resolve planner checkout HEAD: {output.strip() or type(exc).__name__}"
        ) from exc


def _expected_pool_keys(profile: PlannerProfile):
    keys = set(BASE_POOL_KEYS)
    keys.add(profile.date_field)
    if profile.has_publication_slots:
        keys.add("publication_slots")
    return keys


def _pool_path(profile: PlannerProfile, pool_id, date_value):
    if not isinstance(pool_id, str):
        return ""
    if profile is DAILY:
        return (
            "youtube-shorts-bot/content/planning-pools/daily/"
            f"{date_value}/{pool_id}.json"
        )
    return f"youtube-shorts-bot/content/planning-pools/adhoc/{pool_id}.json"


def _validate_structure(pool, profile, rules_source_sha, *, now_utc=None):
    errors = []
    empty = {
        "pool_id": None,
        "date_value": None,
        "planning_mode": None,
        "target_count": None,
        "publication_slots": None,
        "expected_count": 0,
        "candidates": None,
        "errors": errors,
    }
    if not isinstance(pool, dict):
        errors.append(f"{profile.name} draft root must be an object")
        return empty

    expected_keys = _expected_pool_keys(profile)
    missing = expected_keys - set(pool)
    extra = set(pool) - expected_keys
    if missing:
        errors.append(
            f"{profile.name} planning pool missing fields: " + ", ".join(sorted(missing))
        )
    if extra:
        errors.append(
            f"{profile.name} planning pool unexpected fields: " + ", ".join(sorted(extra))
        )

    date_value = str(pool.get(profile.date_field, ""))
    mode = pool.get("planning_mode")
    target = pool.get("target_count")
    slots = pool.get("publication_slots") if profile.has_publication_slots else None
    expected_count = expected_candidate_count(profile, target)
    result = {
        "pool_id": pool.get("pool_id"),
        "date_value": date_value,
        "planning_mode": mode,
        "target_count": target,
        "publication_slots": slots,
        "expected_count": expected_count,
        "candidates": None,
        "errors": errors,
    }
    if errors:
        return result

    if pool.get("schema_version") != POOL_SCHEMA_VERSION:
        errors.append(
            f"{profile.name} planning pool schema_version must be {POOL_SCHEMA_VERSION}"
        )
    if pool.get("pool_type") != profile.pool_type:
        errors.append(f"{profile.name} planning pool pool_type must be {profile.pool_type}")

    try:
        parse_date(date_value, f"{profile.name} {profile.date_field}")
    except PlannerContractError as exc:
        errors.append(str(exc))

    pool_id = pool.get("pool_id")
    expected_path = _pool_path(profile, pool_id, date_value)
    if profile is DAILY:
        match = DAILY_POOL_RE.fullmatch(expected_path)
        if not match or match.groups() != (date_value, pool_id):
            errors.append(
                "Daily pool_id/plan_date must satisfy the canonical immutable pool naming contract"
            )
    elif not ADHOC_POOL_RE.fullmatch(expected_path):
        errors.append("Ad-hoc pool_id must satisfy the canonical immutable pool naming contract")

    if mode not in profile.planning_modes:
        errors.append(
            f"{profile.name} planning_mode must be one of {sorted(profile.planning_modes)}"
        )

    if profile.fixed_target_count is not None:
        if target != profile.fixed_target_count:
            errors.append(
                f"{profile.name} planning pool target_count must be exactly "
                f"{profile.fixed_target_count}"
            )
    else:
        if isinstance(target, bool) or not isinstance(target, int) or not 1 <= target <= 24:
            errors.append("Daily target_count must be an integer between 1 and 24")
        elif mode == profile.normal_mode and target != profile.normal_target_count:
            errors.append(
                f"{profile.normal_mode} target_count must be exactly "
                f"{profile.normal_target_count}"
            )

    if profile.has_publication_slots and date_value:
        _, slot_errors = validate_daily_slots(
            mode,
            target,
            slots,
            date_value,
            now_utc=now_utc,
        )
        errors.extend(slot_errors)

    candidates = None
    candidate_ids = None
    if expected_count > 0:
        try:
            candidates, candidate_ids = validate_ranked_candidates(
                pool,
                expected_count,
                require_background_category=True,
            )
        except PlannerContractError as exc:
            errors.append(str(exc))
    if candidate_ids is not None:
        errors.extend(validate_planning_execution(pool, candidate_ids, rules_source_sha))
    elif not HEX40_RE.fullmatch(str(rules_source_sha or "")):
        errors.append("rules_source_sha must be a lowercase full 40-character commit SHA")

    result["candidates"] = candidates
    return result


def _apply_uniqueness(profile, structure):
    errors = []
    pool_id = structure["pool_id"]
    date_value = structure["date_value"]
    if profile is DAILY:
        canonical_plan = BOT_ROOT / "content" / "planning" / f"{date_value}.json"
        expected_pool = (
            BOT_ROOT
            / "content"
            / "planning-pools"
            / "daily"
            / date_value
            / f"{pool_id}.json"
        )
        if canonical_plan.exists():
            errors.append(
                f"canonical Daily plan already exists for {date_value}; recover it instead of replanning"
            )
        if expected_pool.exists():
            errors.append(
                "immutable Daily planning pool already exists; use a new immutable attempt ID"
            )
    return errors


def validate_draft(
    profile_name,
    pool,
    rules_source_sha,
    *,
    raw_bytes=b"",
    registry=None,
    check_checkout_head=False,
    check_uniqueness=True,
    now_utc=None,
):
    """Validate a complete current planning pool without mutating it."""
    started = time.perf_counter()
    profile = get_profile(profile_name)
    original = copy.deepcopy(pool)
    structure = _validate_structure(
        pool,
        profile,
        rules_source_sha,
        now_utc=now_utc,
    )
    pool_errors = list(structure["errors"])

    if check_checkout_head and not pool_errors:
        head = _current_head()
        if head != rules_source_sha:
            pool_errors.append(
                f"rules_source_sha {rules_source_sha} does not match checkout HEAD {head}"
            )

    if check_uniqueness and not pool_errors:
        pool_errors.extend(_apply_uniqueness(profile, structure))

    try:
        registry = registry if registry is not None else load_registry()
    except (OSError, TypeError, ValueError) as exc:
        pool_errors.append(f"background registry unavailable or invalid: {exc}")
        registry = None

    candidates = structure["candidates"]
    slots = structure["publication_slots"]
    candidate_results = []
    if candidates is not None and registry is not None:
        for item in candidates:
            request = item["request"]
            content_id = str(request.get("content_id", ""))
            publish_at = None
            if profile.has_publication_slots and isinstance(slots, list):
                rank = int(item["rank"])
                if 1 <= rank <= len(slots):
                    publish_at = slots[rank - 1]
            request_path = BOT_ROOT / "content" / "requests" / f"{content_id}.json"
            errors = candidate_errors(
                request,
                registry=registry,
                request_path=request_path,
                profile=profile,
                publish_at_override=publish_at,
                background_category=item.get("background_category"),
            )
            candidate_results.append(
                {
                    "rank": item["rank"],
                    "candidate_id": item["candidate_id"],
                    "content_id": content_id,
                    "status": "PASS" if not errors else "FAIL",
                    "errors": errors,
                }
            )

    valid_count = sum(item["status"] == "PASS" for item in candidate_results)
    expected_count = structure["expected_count"]
    status = (
        "PASS"
        if not pool_errors
        and len(candidate_results) == expected_count
        and valid_count == expected_count
        else "FAIL"
    )

    if pool != original:
        raise AssertionError("pre-commit validation mutated the ChatGPT-authored draft")

    return {
        "status": status,
        "commit_allowed": status == "PASS",
        "profile": profile.name,
        "pool_id": structure["pool_id"],
        profile.date_field: structure["date_value"],
        "planning_mode": structure["planning_mode"],
        "target_count": structure["target_count"],
        "request_schema_version": SCHEMA_VERSION,
        "rules_source_sha": rules_source_sha,
        "draft_sha256": hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None,
        "expected_candidates": expected_count,
        "valid_candidates": valid_count,
        "failed_candidates": max(0, expected_count - valid_count),
        "pool_errors": pool_errors,
        "candidate_results": candidate_results,
        "validation_elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }


def _read_pool(path, profile_name):
    try:
        raw = Path(path).read_bytes()
        return raw, json.loads(raw.decode("utf-8")), None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return b"", None, {
            "status": "FAIL",
            "commit_allowed": False,
            "profile": profile_name,
            "pool_errors": [f"cannot read {profile_name} draft {path}: {exc}"],
            "candidate_results": [],
        }


def main_for_profile(profile_name):
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", required=True, help="Temporary ChatGPT-authored pool JSON")
    parser.add_argument("--rules-source-sha", required=True)
    parser.add_argument(
        "--verify-git-head",
        action="store_true",
        help="Optional CI/developer check that rules_source_sha equals git rev-parse HEAD",
    )
    args = parser.parse_args()
    raw, pool, failure = _read_pool(args.pool, profile_name)
    result = failure or validate_draft(
        profile_name,
        pool,
        args.rules_source_sha,
        raw_bytes=raw,
        check_checkout_head=args.verify_git_head,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("status") != "PASS":
        raise SystemExit(2)


def main():
    parser = argparse.ArgumentParser(
        description="Shared Wacky Dramas planning-pool pre-commit validator"
    )
    parser.add_argument("--profile", choices=("daily", "adhoc"), required=True)
    parser.add_argument("--pool", required=True)
    parser.add_argument("--rules-source-sha", required=True)
    parser.add_argument("--verify-git-head", action="store_true")
    args = parser.parse_args()
    raw, pool, failure = _read_pool(args.pool, args.profile)
    result = failure or validate_draft(
        args.profile,
        pool,
        args.rules_source_sha,
        raw_bytes=raw,
        check_checkout_head=args.verify_git_head,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("status") != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
