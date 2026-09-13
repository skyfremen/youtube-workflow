"""Backward-compatible Daily wrapper around the shared planner precommit engine."""
from __future__ import annotations

from planning.planner_precommit import main_for_profile
from planning.planner_precommit import validate_draft as _validate_shared_draft

PROFILE = "daily"
SHARED_ENGINE_MODULE = "planning.planner_precommit"


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
    return _validate_shared_draft(
        PROFILE,
        pool,
        rules_source_sha,
        raw_bytes=raw_bytes,
        registry=registry,
        check_checkout_head=check_checkout_head,
        check_uniqueness=check_uniqueness,
        now_utc=now_utc,
    )


def main():
    main_for_profile(PROFILE)


if __name__ == "__main__":
    main()
