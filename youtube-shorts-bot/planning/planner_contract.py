"""Expose the live planner contract to ChatGPT/Work as machine-readable JSON.

This module intentionally imports authoritative production constants instead of
redeclaring them. It is a read-only discovery surface for planner authorship.
"""
from __future__ import annotations

import json

from common.workflow_common import CONTENT_ID_RE
from media.media_readiness import MIN_SELECTABLE_ASSETS, REQUIRED_CATEGORY_MINIMUMS
from planning import ranked_promotion
from planning.planning_config import (
    ANTAGONIST_ROLES,
    CATEGORIES,
    EDITORIAL_WEIGHTS,
    EMOTIONS,
    ENDING_STYLES,
    HOOK_WEIGHTS,
    OPENING_STYLES,
    PROTAGONIST_ROLES,
    TITLE_STYLES,
    TITLE_WEIGHTS,
)
from validation import schema_v4
from validation.validate_content import SCHEMA_VERSION

ADHOC_PUBLICATION = {
    "mode": "immediate",
    "timezone": "Asia/Singapore",
    "publish_at": None,
}
DAILY_PUBLICATION = {
    "mode": "scheduled",
    "timezone": "Asia/Singapore",
    "publish_at": None,
}


def build_contract():
    """Return the current canonical fields ChatGPT must author against."""
    return {
        "request_schema_version": SCHEMA_VERSION,
        "ranked_pool_schema_version": ranked_promotion.POOL_SCHEMA_VERSION,
        "adhoc_pool_size": ranked_promotion.ADHOC_POOL_SIZE,
        "adhoc_planning_modes": sorted(ranked_promotion.ADHOC_PLANNING_MODES),
        "daily_pool_size": ranked_promotion.DAILY_POOL_SIZE,
        "daily_planning_modes": sorted(ranked_promotion.PLANNING_MODES),
        "daily_normal_target": ranked_promotion.NORMAL_DAILY_TARGET,
        "daily_catch_up_min_lead_minutes": ranked_promotion.CATCH_UP_MIN_LEAD_MINUTES,
        "content_id_pattern": CONTENT_ID_RE.pattern,
        "candidate_id_pattern": ranked_promotion.CANDIDATE_ID_RE.pattern,
        # Backward-compatible Ad-hoc discovery key used by the existing planner.
        "publication": ADHOC_PUBLICATION,
        "adhoc_publication": ADHOC_PUBLICATION,
        "daily_publication_template": DAILY_PUBLICATION,
        "execution_environment": {
            "checkout_mode": {
                "description": "Use the repository checkout directly when .git is available.",
                "head_command": "git rev-parse HEAD",
                "adhoc_precommit_command": (
                    "python -m planning.adhoc_precommit --pool <pool> "
                    "--rules-source-sha <sha>"
                ),
                "daily_precommit_command": (
                    "python -m planning.daily_precommit --pool <pool> "
                    "--rules-source-sha <sha>"
                ),
            },
            "chatgpt_snapshot_mode": {
                "description": (
                    "For isolated ChatGPT/Work Python environments without an authenticated "
                    "clone. Materialize all planner inputs from one immutable GitHub commit, "
                    "record repository-relative paths plus Git blob SHAs in a snapshot manifest, "
                    "verify/bootstrap temporary Git HEAD metadata, then run the normal canonical "
                    "precommit validator unchanged."
                ),
                "snapshot_manifest_schema_version": 1,
                "snapshot_manifest_fields": {
                    "schema_version": 1,
                    "source_sha": "<exact immutable GitHub commit SHA>",
                    "files": [
                        {"path": "<repository-relative path>", "blob_sha": "<Git blob SHA>"}
                    ],
                },
                "bootstrap_command": (
                    "python -m planning.snapshot_checkout --rules-source-sha <sha> "
                    "--snapshot-manifest <manifest>"
                ),
                "head_command_after_bootstrap": "git rev-parse HEAD",
                "adhoc_precommit_command": (
                    "python -m planning.adhoc_precommit --pool <pool> "
                    "--rules-source-sha <sha>"
                ),
                "daily_precommit_command": (
                    "python -m planning.daily_precommit --pool <pool> "
                    "--rules-source-sha <sha>"
                ),
                "rules": [
                    "Do not mix files from different source SHAs.",
                    "Every materialized repository file used for planning or validation must be listed in the manifest with its Git blob SHA.",
                    "Bootstrap must PASS before treating git rev-parse HEAD as authoritative in a snapshot.",
                    "The exact source SHA must remain the planning_execution.rules_source_sha.",
                    "Normal schema, media, uniqueness, publication and candidate validation remains mandatory.",
                ],
            },
        },
        "media_readiness": {
            "audit_command": "python -m media.media_readiness audit --allow-not-ready",
            "minimum_selectable_assets": MIN_SELECTABLE_ASSETS,
            "required_category_minimums": REQUIRED_CATEGORY_MINIMUMS,
            "readiness_manifest_prefix": "content/background-sourcing/readiness/",
            "background_management_workflow": ".github/workflows/background-management.yml",
            "retired_asset_flag": "selection_enabled=false",
            "required_before_daily": True,
            "required_before_adhoc": True,
            "replenish_is_terminal": False,
            "automatic_continuation_required": True,
            "replenishment_manifest_is_allowed_prerequisite_commit": True,
            "pool_only_commit_rule_applies_after_readiness_pass": True,
            "replenishment_sequence": [
                "audit returns REPLENISH",
                "ChatGPT/Work discovers and visually reviews enough Pexels candidates to satisfy returned deficits",
                "create exactly one new immutable readiness manifest for the replenishment attempt",
                "commit the readiness manifest so Background Management runs automatically",
                "observe Background Management to completion in the same planning invocation when tooling permits",
                "re-read current main after registry persistence",
                "rerun planning.planner_contract",
                "rerun media.media_readiness audit --allow-not-ready",
                "repeat with a new immutable readiness manifest if deficits remain",
                "resume Daily or Ad-hoc ranked-pool authorship only after status PASS and ready true",
            ],
            "rules": [
                "REPLENISH is a resumable prerequisite state, not a successful or terminal planner outcome.",
                "Do not end a planning invocation merely because readiness returned REPLENISH when the required replenishment actions and repository writes are available.",
                "A task instruction such as 'commit only the ranked-pool JSON' does not forbid prerequisite readiness-manifest commits; it governs the successful pool-authorship commit after readiness PASS.",
                "Fail closed only when replenishment itself cannot be completed safely or mechanically, Background Management fails, the required external capability is unavailable, or readiness still cannot reach PASS after compliant attempts.",
                "Never bypass readiness, invent local registry entries, or use retired assets for new planning.",
            ],
        },
        "editorial_score_components": list(EDITORIAL_WEIGHTS),
        "title_score_components": list(TITLE_WEIGHTS),
        "hook_score_components": list(HOOK_WEIGHTS),
        "controlled_values": {
            "categories": sorted(CATEGORIES),
            "emotions": sorted(EMOTIONS),
            "opening_styles": sorted(OPENING_STYLES),
            "title_styles": sorted(TITLE_STYLES),
            "ending_styles": sorted(ENDING_STYLES),
            "protagonist_roles": sorted(PROTAGONIST_ROLES),
            "antagonist_roles": sorted(ANTAGONIST_ROLES),
            "voices": sorted(schema_v4.APPROVED_VOICES),
            "story_tones": sorted(schema_v4.STORY_TONES),
            "lead_genders": sorted(schema_v4.LEAD_GENDERS),
        },
        "narration": {
            "engine": "kokoro",
            "speed": 1.75,
        },
    }


def main():
    print(json.dumps(build_contract(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
