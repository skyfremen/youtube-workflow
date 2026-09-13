"""Private retention-first background selector for new continuous production.

New planning uses only the active registry and never falls back to immortal default
IDs. A candidate either freezes a valid distinct primary/backup pair or fails.
"""
from media import background_selector_base as base
from media.background_selector_base import *  # re-export established selector surface
from media.continuous_background import continuous_source_eligible

_base_rank_assets = base.rank_assets
_base_audit_ai_selection = base.audit_ai_selection


def is_successful_receipt(record):
    if not (
        isinstance(record, dict)
        and record.get("background_asset_id")
        and record.get("verification", {}).get("passed") is True
    ):
        return False
    state = record.get("verification_state")
    if state in {"verified_public", "verified_immediate_public"}:
        return bool(
            record.get("privacy_status") == "public"
            and (
                record.get("publish_at_absent") is True
                or (
                    record.get("publication_mode") == "immediate"
                    and record.get("publish_at") is None
                )
            )
        )
    if state == "verified_private":
        return bool(
            record.get("privacy_status") == "private"
            and record.get("publish_at_absent") is True
        )
    if state in {"verified_scheduled", "verified_scheduled_published"}:
        return bool(
            record.get("publication_mode") == "scheduled"
            and record.get("publish_at")
            and record.get("privacy_status") in {"private", "public"}
        )
    return False


def _continuous_registry(registry):
    return {
        **registry,
        "assets": [
            asset
            for asset in registry.get("assets", [])
            if continuous_source_eligible(asset)
        ],
    }


def rank_assets(
    registry,
    requirements,
    receipts,
    planned_asset_ids=(),
    planned_categories=(),
):
    return _base_rank_assets(
        _continuous_registry(registry),
        requirements,
        receipts,
        planned_asset_ids=planned_asset_ids,
        planned_categories=planned_categories,
    )


def audit_ai_selection(registry, primary_id, backup_id, receipts, requirements=None):
    if primary_id == backup_id:
        return {
            "passed": False,
            "errors": ["primary and backup background IDs must differ"],
            "fallback_used": False,
            "requested_primary_id": primary_id,
            "requested_backup_id": backup_id,
            "resolved_primary_id": None,
            "resolved_backup_id": None,
        }
    mapping = base.asset_map(registry)
    duration_errors = [
        f"background {asset_id} is not eligible for continuous fit-to-short"
        for asset_id in (primary_id, backup_id)
        if asset_id in mapping and not continuous_source_eligible(mapping[asset_id])
    ]
    requested = _base_audit_ai_selection(
        _continuous_registry(registry), primary_id, backup_id, receipts, requirements
    )
    errors = [*duration_errors, *(requested.get("errors") or [])]
    passed = bool(requested.get("passed")) and not duration_errors
    return {
        **requested,
        "passed": passed,
        "errors": errors,
        "selection_errors": errors,
        "fallback_used": False,
        "requested_primary_id": primary_id,
        "requested_backup_id": backup_id,
        "resolved_primary_id": primary_id if passed else None,
        "resolved_backup_id": backup_id if passed else None,
    }


base.is_successful_receipt = is_successful_receipt
base.audit_ai_selection = audit_ai_selection
base.rank_assets = rank_assets


if __name__ == "__main__":
    base.main()
