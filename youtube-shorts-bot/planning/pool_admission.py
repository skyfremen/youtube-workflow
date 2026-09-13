"""Defensive admission gate for already-committed ranked pools.

This reuses the exact shared planner precommit engine. The only semantic
difference from planner-time precommit is uniqueness: the pool itself is already
committed, so pool-existence checks must not reject the just-created immutable pool.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from planning.planner_precommit import validate_draft


def _failure(message):
    return {
        "status": "FAIL",
        "commit_allowed": False,
        "pool_errors": [message],
        "candidate_results": [],
    }


def validate_committed_pool(pool_type, pool, raw_bytes=b""):
    if not isinstance(pool, dict):
        return _failure("ranked pool root must be an object")

    execution = pool.get("planning_execution")
    rules_source_sha = (
        execution.get("rules_source_sha") if isinstance(execution, dict) else None
    )
    if not isinstance(rules_source_sha, str) or not rules_source_sha:
        return _failure(
            "planning_execution.rules_source_sha is required for admission validation"
        )

    if pool_type not in {"adhoc", "daily"}:
        return _failure(f"unsupported pool type: {pool_type}")
    return validate_draft(
        pool_type,
        pool,
        rules_source_sha,
        raw_bytes=raw_bytes,
        check_checkout_head=False,
        check_uniqueness=False,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run shared planner precommit as the committed-pool admission gate"
    )
    parser.add_argument("pool_type", choices=("adhoc", "daily"))
    parser.add_argument("--pool", required=True)
    parser.add_argument("--summary")
    args = parser.parse_args()

    path = Path(args.pool)
    try:
        raw = path.read_bytes()
        pool = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = _failure(f"cannot read ranked pool {path}: {exc}")
    else:
        result = validate_committed_pool(args.pool_type, pool, raw)

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.summary:
        Path(args.summary).write_text(rendered, encoding="utf-8")
    if result.get("status") != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
