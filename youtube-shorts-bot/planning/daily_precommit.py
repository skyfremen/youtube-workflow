"""Fail-closed pre-commit validation for ChatGPT-authored Daily ranked pools.

ChatGPT remains the creative/editorial owner. This module executes the live
repository contract against a temporary 36-candidate Daily draft before any
immutable pool commit exists. It never generates, ranks, repairs or substitutes
creative content.

Repository identity is supplied explicitly through ``rules_source_sha``. A Git
checkout is not required for normal planner execution. Real checkouts may opt
into an additional HEAD cross-check for CI/developer hardening.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common.workflow_common import CONTENT_ID_RE
from media.validate_media_library import load_registry
from planning import ranked_promotion
from planning.planner_contract import DAILY_PUBLICATION
from planning.planning_config import TITLE_WEIGHTS
from validation.validate_content import SCHEMA_VERSION

EXPECTED_POOL_KEYS = {
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
EXPECTED_EXECUTION_KEYS = {
    "editorial_selection_owner",
    "planning_method",
    "rules_source_sha",
    "ranked_candidate_ids",
}


def _current_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ranked_promotion.REPO_ROOT,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        output = getattr(exc, "output", "") or ""
        raise ranked_promotion.PromotionError(
            f"cannot resolve planner checkout HEAD: {output.strip() or type(exc).__name__}"
        ) from exc


def _title_component_key_errors(request):
    errors = []
    planning = request.get("planning")
    titles = planning.get("title_candidates") if isinstance(planning, dict) else None
    if not isinstance(titles, list):
        return errors
    expected = set(TITLE_WEIGHTS)
    for index, item in enumerate(titles):
        components = item.get("score_components") if isinstance(item, dict) else None
        if not isinstance(components, dict):
            continue
        actual = set(components)
        if actual == expected:
            continue
        errors.append(
            f"planning.title_candidates[{index}].score_components keys mismatch; "
            f"missing={sorted(expected - actual)}; unexpected={sorted(actual - expected)}"
        )
    return errors


def _pool_structure(pool, rules_source_sha, *, now_utc=None):
    errors = []
    if not isinstance(pool, dict):
        return None, None, None, None, None, ["Daily draft root must be an object"]

    missing = EXPECTED_POOL_KEYS - set(pool)
    extra = set(pool) - EXPECTED_POOL_KEYS
    if missing:
        errors.append("Daily ranked pool missing fields: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("Daily ranked pool unexpected fields: " + ", ".join(sorted(extra)))
    if errors:
        return None, None, None, None, None, errors

    if pool.get("schema_version") != ranked_promotion.POOL_SCHEMA_VERSION:
        errors.append(
            f"Daily ranked pool schema_version must be {ranked_promotion.POOL_SCHEMA_VERSION}"
        )
    if pool.get("pool_type") != "daily":
        errors.append("Daily ranked pool pool_type must be daily")

    plan_date = str(pool.get("plan_date", ""))
    try:
        ranked_promotion._parse_date(plan_date, "daily plan_date")
    except ranked_promotion.PromotionError as exc:
        errors.append(str(exc))

    pool_id = pool.get("pool_id")
    expected_path = (
        f"youtube-shorts-bot/content/planning-pools/daily/{plan_date}/{pool_id}.json"
        if isinstance(pool_id, str)
        else ""
    )
    match = ranked_promotion.DAILY_POOL_RE.fullmatch(expected_path)
    if not match or match.groups() != (plan_date, pool_id):
        errors.append(
            "Daily pool_id/plan_date must satisfy the canonical immutable pool naming contract"
        )

    mode = pool.get("planning_mode")
    if mode not in ranked_promotion.PLANNING_MODES:
        errors.append("Daily planning_mode must be normal_next_day or same_day_catch_up")

    target = pool.get("target_count")
    if isinstance(target, bool) or not isinstance(target, int) or not 1 <= target <= 24:
        errors.append("Daily target_count must be an integer between 1 and 24")
    elif mode == "normal_next_day" and target != ranked_promotion.NORMAL_DAILY_TARGET:
        errors.append(
            f"normal_next_day target_count must be exactly {ranked_promotion.NORMAL_DAILY_TARGET}"
        )

    slots = pool.get("publication_slots")
    parsed_slots = []
    if not isinstance(slots, list) or target is None or len(slots) != target or len(slots) != len(set(slots)):
        errors.append("publication_slots must contain exactly target_count unique slots")
    elif plan_date:
        for raw in slots:
            try:
                parsed_slots.append(ranked_promotion._parse_slot(raw, plan_date))
            except ranked_promotion.PromotionError as exc:
                errors.append(str(exc))
        if len(parsed_slots) == len(slots):
            if parsed_slots != sorted(parsed_slots):
                errors.append("publication_slots must be chronological")
            if mode == "normal_next_day" and slots != ranked_promotion._canonical_normal_slots(plan_date):
                errors.append(
                    "normal_next_day publication_slots must be the canonical 24 hourly slots"
                )
            if mode == "same_day_catch_up":
                current = now_utc or datetime.now(timezone.utc)
                if current.tzinfo is None:
                    current = current.replace(tzinfo=timezone.utc)
                threshold = current.astimezone(timezone.utc) + timedelta(
                    minutes=ranked_promotion.CATCH_UP_MIN_LEAD_MINUTES
                )
                if any(slot < threshold for slot in parsed_slots):
                    errors.append(
                        "same_day_catch_up publication slots must remain at least "
                        f"{ranked_promotion.CATCH_UP_MIN_LEAD_MINUTES} minutes in the future"
                    )

    try:
        candidates, candidate_ids = ranked_promotion._validate_ranked_candidates(
            pool, ranked_promotion.DAILY_POOL_SIZE
        )
    except ranked_promotion.PromotionError as exc:
        errors.append(str(exc))
        return pool_id, plan_date, mode, target, slots, errors

    execution = pool.get("planning_execution")
    if not isinstance(execution, dict) or set(execution) != EXPECTED_EXECUTION_KEYS:
        errors.append("planning_execution must contain ranked-pool ChatGPT provenance")
    else:
        if execution.get("editorial_selection_owner") != "chatgpt":
            errors.append("ranked planning requires editorial_selection_owner=chatgpt")
        if execution.get("planning_method") != "chatgpt_ranked_pool":
            errors.append("ranked planning requires planning_method=chatgpt_ranked_pool")
        if execution.get("rules_source_sha") != rules_source_sha:
            errors.append(
                "planning_execution.rules_source_sha must equal the exact "
                "rules_source_sha supplied to the validator"
            )
        if execution.get("ranked_candidate_ids") != candidate_ids:
            errors.append(
                "planning_execution.ranked_candidate_ids must exactly match frozen rank order"
            )

    if not ranked_promotion.HEX40_RE.fullmatch(str(rules_source_sha or "")):
        errors.append("rules_source_sha must be a lowercase full 40-character commit SHA")

    return pool_id, plan_date, mode, target, slots, candidates if 'candidates' in locals() else None, errors


def validate_draft(
    pool,
    rules_source_sha,
    *,
    raw_bytes=b"",
    registry=None,
    check_checkout_head=False,
    check_uniqueness=True,
    now_utc=None,
):
    """Validate every one of the 36 AI-authored Daily candidates without mutation.

    ``rules_source_sha`` is the authoritative repository identity for normal
    execution. ``check_checkout_head`` is optional and intended only for a real
    checkout where an additional Git HEAD cross-check is useful.
    """
    original = copy.deepcopy(pool)
    structure = _pool_structure(pool, rules_source_sha, now_utc=now_utc)
    if len(structure) == 6:
        pool_id, plan_date, mode, target, slots, pool_errors = structure
        candidates = None
    else:
        pool_id, plan_date, mode, target, slots, candidates, pool_errors = structure

    if check_checkout_head and not pool_errors:
        head = _current_head()
        if head != rules_source_sha:
            pool_errors.append(
                f"rules_source_sha {rules_source_sha} does not match checkout HEAD {head}"
            )

    expected_path = None
    if pool_id and plan_date:
        expected_path = (
            ranked_promotion.BOT_ROOT
            / "content"
            / "planning-pools"
            / "daily"
            / plan_date
            / f"{pool_id}.json"
        )
    if check_uniqueness and not pool_errors:
        canonical_plan = ranked_promotion.BOT_ROOT / "content" / "planning" / f"{plan_date}.json"
        if canonical_plan.exists():
            pool_errors.append(
                f"canonical Daily plan already exists for {plan_date}; recover it instead of replanning"
            )
        if expected_path is not None and expected_path.exists():
            pool_errors.append(
                "immutable Daily planning pool already exists; use a new immutable attempt ID"
            )

    try:
        registry = registry if registry is not None else load_registry()
    except (OSError, TypeError, ValueError) as exc:
        pool_errors.append(f"background registry unavailable or invalid: {exc}")
        registry = None

    candidate_results = []
    if candidates is not None and registry is not None and isinstance(slots, list) and slots:
        for item in candidates:
            request = item["request"]
            content_id = str(request.get("content_id", ""))
            errors = []

            if not CONTENT_ID_RE.fullmatch(content_id):
                errors.append(
                    f"content_id must match canonical pattern {CONTENT_ID_RE.pattern}"
                )
            if request.get("publication") != DAILY_PUBLICATION:
                errors.append(
                    "Daily publication must exactly equal scheduled/Asia-Singapore/null before promotion"
                )
            errors.extend(_title_component_key_errors(request))

            candidate = copy.deepcopy(request)
            if candidate.get("publication") == DAILY_PUBLICATION:
                slot_index = (int(item["rank"]) - 1) % len(slots)
                candidate["publication"]["publish_at"] = slots[slot_index]
            request_path = (
                ranked_promotion.BOT_ROOT
                / "content"
                / "requests"
                / f"{content_id}.json"
            )
            errors.extend(
                ranked_promotion._candidate_errors(
                    candidate,
                    registry=registry,
                    request_path=request_path,
                )
            )

            deduped = list(dict.fromkeys(errors))
            candidate_results.append(
                {
                    "rank": item["rank"],
                    "candidate_id": item["candidate_id"],
                    "content_id": content_id,
                    "status": "PASS" if not deduped else "FAIL",
                    "errors": deduped,
                }
            )

    valid_count = sum(item["status"] == "PASS" for item in candidate_results)
    expected_count = ranked_promotion.DAILY_POOL_SIZE
    status = (
        "PASS"
        if not pool_errors
        and len(candidate_results) == expected_count
        and valid_count == expected_count
        else "FAIL"
    )

    if pool != original:
        raise AssertionError("pre-commit validation mutated the ChatGPT-authored Daily draft")

    return {
        "status": status,
        "commit_allowed": status == "PASS",
        "pool_id": pool_id,
        "plan_date": plan_date,
        "planning_mode": mode,
        "target_count": target,
        "request_schema_version": SCHEMA_VERSION,
        "rules_source_sha": rules_source_sha,
        "draft_sha256": hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None,
        "expected_candidates": expected_count,
        "valid_candidates": valid_count,
        "failed_candidates": expected_count - valid_count,
        "pool_errors": pool_errors,
        "candidate_results": candidate_results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", required=True, help="Temporary ChatGPT-authored Daily pool JSON")
    parser.add_argument("--rules-source-sha", required=True)
    parser.add_argument(
        "--verify-git-head",
        action="store_true",
        help="Optional CI/developer check that rules_source_sha equals git rev-parse HEAD",
    )
    args = parser.parse_args()

    path = Path(args.pool)
    try:
        raw = path.read_bytes()
        pool = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = {
            "status": "FAIL",
            "commit_allowed": False,
            "pool_errors": [f"cannot read Daily draft {path}: {exc}"],
            "candidate_results": [],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(2)

    result = validate_draft(
        pool,
        args.rules_source_sha,
        raw_bytes=raw,
        check_checkout_head=args.verify_git_head,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
