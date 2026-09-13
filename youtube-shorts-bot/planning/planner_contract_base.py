"""Expose the live shared planner contract to ChatGPT/Work as JSON.

Daily and Ad-hoc are profiles of one planner. Shared schema, semantic, media,
background, narration and precommit behavior is imported once from authoritative
modules; profiles may declare only mode-specific policy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from common.workflow_common import CONTENT_ID_RE
from media.media_readiness import MIN_SELECTABLE_ASSETS, REQUIRED_CATEGORY_MINIMUMS
from planning.planner_core import (
    CANDIDATE_ID_RE,
    CATCH_UP_MIN_LEAD_MINUTES,
    POOL_SCHEMA_VERSION,
)
from planning.planner_profiles import (
    ADHOC,
    DAILY,
    PROFILES,
    assert_profiles_do_not_override_shared_contract,
)
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

ADHOC_PUBLICATION = ADHOC.publication_template
DAILY_PUBLICATION = DAILY.publication_template
ARCHITECTURE_VERSION = 1
SHARED_PRECOMMIT_MODULE = "planning.planner_precommit"
SHARED_CANDIDATE_VALIDATOR = "planning.planner_core.candidate_errors"
SHARED_REQUEST_VALIDATOR = "validation.validate_content.validate_request_data"
SHARED_PUBLICATION_VALIDATOR = "validation.publication.validate_upload_contract"


def _shared_contract_payload():
    return {
        "architecture_version": ARCHITECTURE_VERSION,
        "request_schema_version": SCHEMA_VERSION,
        "ranked_pool_schema_version": POOL_SCHEMA_VERSION,
        "precommit_module": SHARED_PRECOMMIT_MODULE,
        "candidate_validator": SHARED_CANDIDATE_VALIDATOR,
        "request_validator": SHARED_REQUEST_VALIDATOR,
        "publication_validator": SHARED_PUBLICATION_VALIDATOR,
        "editorial_score_components": list(EDITORIAL_WEIGHTS),
        "title_score_components": list(TITLE_WEIGHTS),
        "hook_score_components": list(HOOK_WEIGHTS),
        "voices": sorted(schema_v4.APPROVED_VOICES),
        "story_tones": sorted(schema_v4.STORY_TONES),
        "lead_genders": sorted(schema_v4.LEAD_GENDERS),
        "narration_engine": "kokoro",
        "narration_speed": 1.75,
    }


def _shared_fingerprint():
    raw = json.dumps(
        _shared_contract_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _materialization_summary():
    path = Path(__file__).with_name("PLANNER_MATERIALIZATION.json")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    shared_python = manifest.get("shared_required_python_files") or []
    shared_data = manifest.get("shared_required_data_files") or []
    profile_files = manifest.get("profile_required_files") or {}
    bootstrap = manifest.get("planner_bootstrap") or {}
    return {
        "manifest_schema_version": manifest.get("schema_version"),
        "preferred_bootstrap": bootstrap.get("preferred"),
        "fallback_bootstrap": bootstrap.get("fallback"),
        "shared_python_files": len(shared_python),
        "shared_data_files": len(shared_data),
        "profile_file_counts": {
            name: len((profile_files.get(name) or {}).get("python_files") or [])
            + len((profile_files.get(name) or {}).get("data_files") or [])
            for name in sorted(PROFILES)
        },
    }


def build_contract():
    """Return the canonical machine-readable planner contract for both profiles."""
    assert_profiles_do_not_override_shared_contract()
    fingerprint = _shared_fingerprint()
    profiles = {
        name: {
            **profile.contract_dict(),
            "shared_contract_fingerprint": fingerprint,
        }
        for name, profile in sorted(PROFILES.items())
    }
    if len({item["shared_contract_fingerprint"] for item in profiles.values()}) != 1:
        raise RuntimeError("Daily/Ad-hoc shared planner contract drift detected")

    return {
        "architecture_version": ARCHITECTURE_VERSION,
        "shared_contract_fingerprint": fingerprint,
        "shared_implementation": {
            "precommit": SHARED_PRECOMMIT_MODULE,
            "candidate_validation": SHARED_CANDIDATE_VALIDATOR,
            "request_validation": SHARED_REQUEST_VALIDATOR,
            "publication_validation": SHARED_PUBLICATION_VALIDATOR,
            "drift_classification": "planning.planner_drift",
        },
        "profiles": profiles,
        "request_schema_version": SCHEMA_VERSION,
        "ranked_pool_schema_version": POOL_SCHEMA_VERSION,
        "adhoc_pool_size": ADHOC.pool_size,
        "adhoc_planning_modes": sorted(ADHOC.planning_modes),
        "daily_pool_size": DAILY.pool_size,
        "daily_planning_modes": sorted(DAILY.planning_modes),
        "daily_normal_target": DAILY.normal_target_count,
        "daily_catch_up_min_lead_minutes": CATCH_UP_MIN_LEAD_MINUTES,
        "content_id_pattern": CONTENT_ID_RE.pattern,
        "candidate_id_pattern": CANDIDATE_ID_RE.pattern,
        "publication": ADHOC_PUBLICATION,
        "adhoc_publication": ADHOC_PUBLICATION,
        "daily_publication_template": DAILY_PUBLICATION,
        "materialization": _materialization_summary(),
        "execution_environment": {
            "canonical_mode": "connector_exact_sha_materialization",
            "preferred_bootstrap": "connector_materialization",
            "fallback_bootstrap": "none",
            "chatgpt_work_repository_source": "authorized_github_connector_api",
            "materialization_manifest": "planning/PLANNER_MATERIALIZATION.json",
            "materialization_mode": "shared_plus_selected_profile",
            "git_preferred": False,
            "git_reuse_preferred": False,
            "chatgpt_work_shell_git_allowed": False,
            "developer_git_checkout_supported": True,
            "exact_detached_snapshot_required_in_git_mode": True,
            "authenticated_checkout_required": False,
            "git_metadata_required": False,
            "repository_archive_required": False,
            "whole_directory_materialization_required": False,
            "connector_filesystem_mount_required": False,
            "special_connector_materialization_bridge_required": False,
            "github_actions_planner_execution_required": False,
            "repository_identity_source": "connector_resolved_current_main_sha",
            "canonical_precommit_command": (
                "python -m planning.planner_precommit --profile <daily|adhoc> "
                "--pool <pool> --rules-source-sha <sha>"
            ),
            "git_precommit_command": (
                "python -m planning.planner_precommit --profile <daily|adhoc> "
                "--pool <pool> --rules-source-sha <sha> --verify-git-head"
            ),
            "drift_command": (
                "python -m planning.planner_drift --base-sha <rules_source_sha> "
                "--connector-current-main-sha <latest_main_sha> "
                "[--changed-path <path> ...]"
            ),
            "developer_git_drift_command": (
                "python -m planning.planner_drift "
                "--base-sha <rules_source_sha> --head-sha <latest_main_sha>"
            ),
            "compatibility_wrappers": {
                "daily": "python -m planning.daily_precommit",
                "adhoc": "python -m planning.adhoc_precommit",
            },
            "cache": {
                "optional": True,
                "correctness_dependency": False,
                "primary_key": "rules_source_sha",
                "connector_reuse_rule": (
                    "reuse only previously blob-verified files for the identical immutable SHA"
                ),
                "developer_git_reuse_rule": (
                    "real Git checkout reuse is allowed only outside ChatGPT/Work and must "
                    "verify the exact intended commit"
                ),
                "cross_profile_shared_reuse": True,
            },
            "drift_policy": {
                "rules": "full_refresh",
                "media": "media_refresh",
                "history": "history_refresh",
                "operational": "continue_without_planner_restart",
                "unknown": "full_refresh",
            },
            "performance_diagnostics": [
                "materialization_mode",
                "bootstrap_ms",
                "connector_resolve_ms",
                "materialization_ms",
                "contract_ms",
                "media_readiness_ms",
                "state_load_ms",
                "precommit_ms",
                "commit_ms",
            ],
            "rules": [
                "For ChatGPT/Work, begin directly with the authorized GitHub connector/API; shell Git access to github.com is neither attempted nor required.",
                "Resolve one exact immutable current-main SHA through the connector/API and use it as explicit rules_source_sha.",
                "Materialize the exact manifest and every required file from that same SHA, record connector-returned source/blob evidence, and require planning.materialization_verify PASS.",
                "Pass rules_source_sha explicitly to the shared precommit engine without --verify-git-head in connector-materialized ChatGPT/Work execution.",
                "Never manufacture synthetic Git metadata or a fake HEAD for connector-materialized source.",
                "Real Git checkout verification remains available only for developer/CI contexts that genuinely use Git metadata.",
                "GitHub Actions must not execute creative planning.",
                "Before immutable commit, re-query current main through the connector/API; if it advanced, apply planning.planner_drift with connector-supplied changed paths or conservatively full-refresh when path evidence is unavailable.",
            ],
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
        "narration": {"engine": "kokoro", "speed": 1.75},
    }


def main():
    print(json.dumps(build_contract(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
