"""Shared planning-time media readiness gate for Daily and Ad-hoc.

The checked-in registry is the shared background cache. Both planners must
obtain a PASS from this module before authoring an immutable ranked pool. An
empty or insufficient registry is a normal REPLENISH state.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from media.background_selector_base import (
    HIGH_RETENTION_CATEGORIES,
    MIN_QUALITY_SCORE,
    MIN_RETENTION_SCORE,
    quality_score,
    retention_category,
    retention_score,
    _has_production_rendition,
)
from media.validate_media_library import REGISTRY_PATH, load_registry

MIN_SELECTABLE_ASSETS = 32
REQUIRED_CATEGORY_MINIMUMS = {
    "cooking": 3,
    "baking": 3,
    "food_prep": 3,
    "satisfying_process": 4,
    "crafting": 3,
    "cleaning": 3,
    "assembly": 3,
    "pov_movement": 3,
    "city_motion": 3,
}


def is_selection_enabled(asset):
    return asset.get("selection_enabled") is not False


def is_selectable(asset):
    if not is_selection_enabled(asset):
        return False
    if asset.get("status") != "active" or asset.get("verified") is not True:
        return False
    if asset.get("commercial_use") is not True:
        return False
    if asset.get("has_watermark") is not False or asset.get("has_embedded_text") is not False:
        return False
    if retention_category(asset) not in HIGH_RETENTION_CATEGORIES:
        return False
    if quality_score(asset) < MIN_QUALITY_SCORE:
        return False
    if retention_score(asset) < MIN_RETENTION_SCORE:
        return False
    return _has_production_rendition(asset)


def audit_registry(registry):
    assets = list(registry.get("assets") or [])
    selectable = [asset for asset in assets if is_selectable(asset)]
    counts = Counter(retention_category(asset) for asset in selectable)
    category_deficits = {
        category: max(0, minimum - counts.get(category, 0))
        for category, minimum in REQUIRED_CATEGORY_MINIMUMS.items()
    }
    total_deficit = max(0, MIN_SELECTABLE_ASSETS - len(selectable))
    required_new_assets = max(total_deficit, sum(category_deficits.values()))
    ready = total_deficit == 0 and not any(category_deficits.values())
    return {
        "status": "PASS" if ready else "REPLENISH",
        "ready": ready,
        "registry_assets": len(assets),
        "selectable_assets": len(selectable),
        "retired_from_selection": sum(
            1 for asset in assets if asset.get("selection_enabled") is False
        ),
        "minimum_selectable_assets": MIN_SELECTABLE_ASSETS,
        "category_counts": dict(sorted(counts.items())),
        "required_category_minimums": REQUIRED_CATEGORY_MINIMUMS,
        "category_deficits": category_deficits,
        "required_new_assets_at_least": required_new_assets,
        "replenishment_required": not ready,
    }


def main():
    parser = argparse.ArgumentParser(description="Shared Wacky Dramas media readiness gate")
    parser.add_argument("--registry", default=str(REGISTRY_PATH))
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()

    try:
        report = audit_registry(load_registry(args.registry))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "ready": False, "error": str(exc)}, sort_keys=True))
        raise SystemExit(3)

    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["ready"] and not args.allow_not_ready:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
