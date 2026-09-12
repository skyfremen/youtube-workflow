"""Private background selector with canonical successful-receipt semantics.

The retention-first ranking implementation is retained in background_selector_base.
This wrapper fixes production-history classification so current immediate-public
Ad-hoc receipts contribute to the same private anti-repetition history as scheduled
successes, excludes recovery-only retired assets from all new planning, and adds
the one allowed mechanical substitution: a fixed emergency default pair when
ChatGPT's chosen pair fails audit.
"""

from media import background_selector_base as base
from media.background_selector_base import *  # re-export selector API

DEFAULT_BACKGROUND_PRIMARY_ID = "satisfying-001"
DEFAULT_BACKGROUND_BACKUP_ID = "satisfying-002"
_base_audit_ai_selection = base.audit_ai_selection
_base_rank_assets = base.rank_assets


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


def _selection_registry(registry):
    """Return a planning-only view that excludes recovery-only retired assets."""
    return {
        **registry,
        "assets": [
            asset
            for asset in registry.get("assets", [])
            if asset.get("selection_enabled") is not False
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
        _selection_registry(registry),
        requirements,
        receipts,
        planned_asset_ids=planned_asset_ids,
        planned_categories=planned_categories,
    )


def _fallback_asset_audit(registry, asset_id):
    asset = base.asset_map(registry).get(asset_id)
    if not asset:
        return None, f"default background {asset_id} is missing from cache"
    if asset.get("selection_enabled") is False:
        return None, f"default background {asset_id} is retired from new selection"
    if asset.get("status") != "active" or asset.get("verified") is not True:
        return None, f"default background {asset_id} must be active and verified"
    if asset.get("commercial_use") is not True:
        return None, f"default background {asset_id} must allow commercial use"
    if asset.get("has_watermark") is not False or asset.get("has_embedded_text") is not False:
        return None, f"default background {asset_id} must be watermark/text free"
    quality = base.quality_score(asset)
    if quality < base.MIN_QUALITY_SCORE:
        return None, f"default background {asset_id} is below the quality floor"
    if not base._has_production_rendition(asset):
        return None, f"default background {asset_id} has no qualifying post-crop 1080x1920 rendition"
    return {
        **asset,
        "retention_category": base.retention_category(asset),
        "semantic_score": None,
        "quality_score": quality,
        "retention_score": base.retention_score(asset),
        "fallback_default": True,
    }, None


def audit_ai_selection(registry, primary_id, backup_id, receipts, requirements=None):
    """Audit ChatGPT's exact pair, falling back only to the fixed safe default pair."""
    mapping = base.asset_map(registry)
    retired = [
        asset_id
        for asset_id in (primary_id, backup_id)
        if mapping.get(asset_id, {}).get("selection_enabled") is False
    ]
    if retired:
        requested = {
            "passed": False,
            "errors": [
                "retired backgrounds may not be used for new production: "
                + ", ".join(retired)
            ],
        }
    else:
        requested = _base_audit_ai_selection(
            registry, primary_id, backup_id, receipts, requirements
        )
    if requested.get("passed"):
        return {
            **requested,
            "fallback_used": False,
            "requested_primary_id": primary_id,
            "requested_backup_id": backup_id,
            "resolved_primary_id": primary_id,
            "resolved_backup_id": backup_id,
            "selection_errors": [],
        }

    selection_errors = list(requested.get("errors") or [])
    fallback_errors = []
    if DEFAULT_BACKGROUND_PRIMARY_ID == DEFAULT_BACKGROUND_BACKUP_ID:
        fallback_errors.append("default primary and backup background IDs must differ")
    fallback_primary, error = _fallback_asset_audit(registry, DEFAULT_BACKGROUND_PRIMARY_ID)
    if error:
        fallback_errors.append(error)
    fallback_backup, error = _fallback_asset_audit(registry, DEFAULT_BACKGROUND_BACKUP_ID)
    if error:
        fallback_errors.append(error)

    if fallback_errors:
        return {
            "passed": False,
            "errors": selection_errors + fallback_errors,
            "selection_errors": selection_errors,
            "fallback_errors": fallback_errors,
            "fallback_used": False,
            "requested_primary_id": primary_id,
            "requested_backup_id": backup_id,
            "resolved_primary_id": None,
            "resolved_backup_id": None,
            "primary": None,
            "backup": None,
        }

    return {
        "passed": True,
        "errors": selection_errors,
        "selection_errors": selection_errors,
        "fallback_errors": [],
        "fallback_used": True,
        "fallback_reason": "ChatGPT-selected background pair failed audit",
        "requested_primary_id": primary_id,
        "requested_backup_id": backup_id,
        "resolved_primary_id": DEFAULT_BACKGROUND_PRIMARY_ID,
        "resolved_backup_id": DEFAULT_BACKGROUND_BACKUP_ID,
        "primary": fallback_primary,
        "backup": fallback_backup,
    }


# Existing selector helpers resolve these symbols through their defining module's
# globals, so update those hooks rather than duplicating ranking/history logic.
base.is_successful_receipt = is_successful_receipt
base.audit_ai_selection = audit_ai_selection
base.rank_assets = rank_assets


if __name__ == "__main__":
    base.main()
