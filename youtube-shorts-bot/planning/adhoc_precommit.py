"""Fail-closed pre-commit validation for ChatGPT-authored Ad-hoc ranked pools.

The planner remains ChatGPT-owned. This module makes ChatGPT execute the live
repository contract against its temporary draft before immutable history is
created. It never generates, ranks, repairs or substitutes creative content.

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
from pathlib import Path

from common.workflow_common import CONTENT_ID_RE
from media.validate_media_library import load_registry
from planning import ranked_promotion
from planning.planning_config import TITLE_WEIGHTS
from planning.planner_contract import ADHOC_PUBLICATION
from validation.validate_content import SCHEMA_VERSION

EXPECTED_POOL_KEYS = {
    "schema_version",
    "pool_type",
    "pool_id",
    "planning_mode",
    "singapore_date",
    "target_count",
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
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        errors.append(
            f"planning.title_candidates[{index}].score_components keys mismatch; "
            f"missing={missing}; unexpected={unexpected}"
        )
    return errors


def _pool_structure(pool, rules_source_sha):
    errors = []
    if not isinstance(pool, dict):
        return None, None, None, None, ["Ad-hoc draft root must be an object"]

    missing = EXPECTED_POOL_KEYS - set(pool)
    extra = set(pool) - EXPECTED_POOL_KEYS
    if missing:
        errors.append("Ad-hoc ranked pool missing fields: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("Ad-hoc ranked pool unexpected fields: " + ", ".join(sorted(extra)))
    if errors:
        return None, None, None, None, errors

    if pool.get("schema_version") != ranked_promotion.POOL_SCHEMA_VERSION:
        errors.append(
            f"Ad-hoc ranked pool schema_version must be "
            f"{ranked_promotion.POOL_SCHEMA_VERSION}"
        )
    if pool.get("pool_type") != "adhoc":
        errors.append("Ad-hoc ranked pool pool_type must be adhoc")

    pool_id = pool.get("pool_id")
    expected_path = (
        f"youtube-shorts-bot/content/planning-pools/adhoc/{pool_id}.json"
        if isinstance(pool_id, str)
        else ""
    )
    if not ranked_promotion.ADHOC_POOL_RE.fullmatch(expected_path):
        errors.append("Ad-hoc pool_id must satisfy the canonical immutable pool naming contract")

    planning_mode = pool.get("planning_mode")
    if planning_mode not in ranked_promotion.ADHOC_PLANNING_MODES:
        errors.append("Ad-hoc planning_mode must be scheduled_daily or manual_on_demand")

    singapore_date = str(pool.get("singapore_date", ""))
    try:
        ranked_promotion._parse_date(singapore_date, "Ad-hoc singapore_date")
    except ranked_promotion.PromotionError as exc:
        errors.append(str(exc))

    if pool.get("target_count") != 1:
        errors.append("Ad-hoc ranked pool target_count must be exactly 1")

    try:
        candidates, candidate_ids = ranked_promotion._validate_ranked_candidates(
            pool, ranked_promotion.ADHOC_POOL_SIZE
        )
    except ranked_promotion.PromotionError as exc:
        errors.append(str(exc))
        return pool_id, planning_mode, singapore_date, None, errors

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

    if planning_mode == "scheduled_daily" and singapore_date:
        prefix = f"wd-{singapore_date.replace('-', '')}T010000-adhoc-"
        for item in candidates:
            content_id = str(item["request"].get("content_id", ""))
            if not content_id.startswith(prefix):
                errors.append(
                    f"rank {item['rank']} scheduled_daily content_id must use "
                    f"the exact {prefix} namespace"
                )

    return pool_id, planning_mode, singapore_date, candidates, errors


def validate_draft(
    pool,
    rules_source_sha,
    *,
    raw_bytes=b"",
    registry=None,
    check_checkout_head=False,
    check_uniqueness=True,
):
    """Validate all five AI-authored candidates without mutating the draft.

    ``rules_source_sha`` is the authoritative repository identity for normal
    execution. ``check_checkout_head`` is optional and intended only for a real
    checkout where an additional Git HEAD cross-check is useful.
    """
    original = copy.deepcopy(pool)
    pool_id, planning_mode, singapore_date, candidates, pool_errors = _pool_structure(
        pool, rules_source_sha
    )

    if check_checkout_head and not pool_errors:
        head = _current_head()
        if head != rules_source_sha:
            pool_errors.append(
                f"rules_source_sha {rules_source_sha} does not match checkout HEAD {head}"
            )

    if (
        check_uniqueness
        and not pool_errors
        and planning_mode == "scheduled_daily"
        and ranked_promotion._scheduled_adhoc_matches(singapore_date)
    ):
        pool_errors.append(
            "scheduled Ad-hoc production already exists for this Singapore date; "
            "recover the canonical request instead of creating a new pool"
        )

    try:
        registry = registry if registry is not None else load_registry()
    except (OSError, TypeError, ValueError) as exc:
        pool_errors.append(f"background registry unavailable or invalid: {exc}")
        registry = None

    candidate_results = []
    if candidates is not None and registry is not None:
        for item in candidates:
            request = item["request"]
            content_id = str(request.get("content_id", ""))
            errors = []

            if not CONTENT_ID_RE.fullmatch(content_id):
                errors.append(
                    f"content_id must match canonical pattern {CONTENT_ID_RE.pattern}"
                )
            if "-adhoc-" not in content_id.lower():
                errors.append("Ad-hoc content_id must contain -adhoc-")
            if request.get("publication") != ADHOC_PUBLICATION:
                errors.append(
                    "Ad-hoc publication must exactly equal immediate/Asia-Singapore/null"
                )

            errors.extend(_title_component_key_errors(request))

            request_path = (
                ranked_promotion.BOT_ROOT
                / "content"
                / "requests"
                / f"{content_id}.json"
            )
            errors.extend(
                ranked_promotion._candidate_errors(
                    request,
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
    expected_count = ranked_promotion.ADHOC_POOL_SIZE
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
        "pool_id": pool_id,
        "planning_mode": planning_mode,
        "singapore_date": singapore_date,
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
    parser.add_argument("--pool", required=True, help="Temporary ChatGPT-authored pool JSON")
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
            "pool_errors": [f"cannot read Ad-hoc draft {path}: {exc}"],
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
