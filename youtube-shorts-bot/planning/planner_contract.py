"""Live shared planner contract with current schema-v7 background policy."""
from __future__ import annotations

import json

from media.continuous_background import (
    CONCATENATED_FIT_TO_SHORT_MODE,
    FIT_PLAYBACK_RATE_MAX,
    FIT_PLAYBACK_RATE_MIN,
    MAX_SEQUENCE_CLIPS,
    MAX_SEQUENCE_SOURCE_SECONDS,
    MIN_SEQUENCE_CLIP_SECONDS,
    MIN_SEQUENCE_CLIPS,
    MIN_SEQUENCE_SOURCE_SECONDS,
    PREFERRED_SEQUENCE_CLIPS,
    PREFERRED_SEQUENCE_SOURCE_SECONDS,
)
from planning import planner_contract_base as base
from planning.connector_checkpoint import CANONICAL_BACKGROUND_FALLBACK_CATEGORY
from planning.planner_contract_base import *  # noqa: F401,F403


def build_contract():
    contract = base.build_contract()
    contract["media_readiness"].update(
        {
            "planner_uses_global_readiness": False,
            "required_before_daily": False,
            "required_before_adhoc": False,
            "automatic_continuation_required": False,
            "automatic_replenishment_enabled": False,
            "maintenance_only": True,
        }
    )
    contract["background_treatment"] = {
        "mode": CONCATENATED_FIT_TO_SHORT_MODE,
        "request_schema_version": contract["request_schema_version"],
        "planner_freezes_clip_order": True,
        "planner_freezes_segment_ranges": True,
        "planner_freezes_playback_rate": False,
        "runtime_derives_playback_rate_after_tts": True,
        "playback_rate_min": FIT_PLAYBACK_RATE_MIN,
        "playback_rate_max": FIT_PLAYBACK_RATE_MAX,
        "minimum_atomic_clip_seconds": MIN_SEQUENCE_CLIP_SECONDS,
        "sequence_clip_count_min": MIN_SEQUENCE_CLIPS,
        "sequence_clip_count_preferred": PREFERRED_SEQUENCE_CLIPS,
        "sequence_clip_count_max": MAX_SEQUENCE_CLIPS,
        "minimum_sequence_source_seconds": MIN_SEQUENCE_SOURCE_SECONDS,
        "preferred_sequence_source_seconds": PREFERRED_SEQUENCE_SOURCE_SECONDS,
        "maximum_sequence_source_seconds": MAX_SEQUENCE_SOURCE_SECONDS,
        "normal_looping_allowed": False,
        "primary_and_backup_required": True,
        "primary_and_backup_must_be_disjoint": True,
        "same_category_primary_and_backup_required": True,
        "canonical_fallback_category": CANONICAL_BACKGROUND_FALLBACK_CATEGORY,
        "fallback_rule": (
            "preferred category -> alternate suitable eligible category -> canonical fallback"
        ),
        "global_inventory_gate": False,
        "automatic_planner_replenishment": False,
    }
    contract["planner_recovery"] = {
        "recoverable_failures_are_terminal": False,
        "repair_scope": "affected candidate or field only",
        "checkpoint_failure": "repair -> rerun same canonical checkpoint",
        "background_failure": "replace same-category clip or choose alternate/fallback category",
        "repository_drift": "refresh affected evidence/rules -> revalidate",
        "commit_conflict": "refresh main -> apply drift policy -> revalidate if needed -> safe retry",
        "post_commit": "end_planner",
    }
    return contract


def main():
    print(json.dumps(build_contract(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
