"""Global background-library readiness audit for maintenance workflows.

This module measures whether the checked-in registry has broad inventory/category
coverage and enough sequence-capable atomic clips for healthy library maintenance.
Its PASS/REPLENISH result is deliberately **not** a prerequisite for new Daily or
Ad-hoc planning. Current planners validate only the exact background assets they
select and never enter a planner-bound replenishment loop.

Schema-v7 sequence capability remains useful maintenance information: an atomic
asset must be a production-quality >=60s clip, and the audit reports whether the
library can broadly form two disjoint 2-3 clip sequences. Separate background
management tooling may use these deficits to replenish the library proactively.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import combinations

from media.background_selector_base import (
    HIGH_RETENTION_CATEGORIES,
    MIN_QUALITY_SCORE,
    MIN_RETENTION_SCORE,
    quality_score,
    retention_category,
    retention_score,
    _has_production_rendition,
)
from media.continuous_background import (
    MAX_SEQUENCE_CLIPS,
    MAX_SEQUENCE_SOURCE_SECONDS,
    MIN_SEQUENCE_CLIP_SECONDS,
    MIN_SEQUENCE_CLIPS,
    MIN_SEQUENCE_SOURCE_SECONDS,
    PREFERRED_SEQUENCE_CLIPS,
    PREFERRED_SEQUENCE_SOURCE_SECONDS,
    sequence_clip_eligible,
    trusted_duration_seconds,
)
from media.validate_media_library import REGISTRY_PATH, load_registry

MIN_SELECTABLE_ASSETS = 32
REQUIRED_CATEGORY_MINIMUMS = {
    "cooking": 3,
    "baking": 3,
    "food_prep": 3,
    "satisfying_process": 4,
    "crafting": 3,
    "cleaning": 2,
    "assembly": 3,
    "pov_movement": 3,
    "city_motion": 3,
}


def is_selectable(asset):
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
    if not _has_production_rendition(asset):
        return False
    return sequence_clip_eligible(asset)


def _can_form_sequence(capacities):
    """Return whether 2-3 distinct clips can be trimmed to a valid v7 sequence."""
    values = [float(value) for value in capacities]
    if len(values) < MIN_SEQUENCE_CLIPS:
        return False
    for size in range(MIN_SEQUENCE_CLIPS, min(MAX_SEQUENCE_CLIPS, len(values)) + 1):
        if any(sum(group) >= MIN_SEQUENCE_SOURCE_SECONDS for group in combinations(values, size)):
            return True
    return False


def has_two_disjoint_sequences(selectable):
    """Prove primary and backup can be formed without sharing a logical asset."""
    capacities = [trusted_duration_seconds(asset) for asset in selectable]
    if any(value is None for value in capacities):
        return False
    if len(capacities) < MIN_SEQUENCE_CLIPS * 2:
        return False

    indexed = list(enumerate(float(value) for value in capacities))
    for size in range(MIN_SEQUENCE_CLIPS, MAX_SEQUENCE_CLIPS + 1):
        for first in combinations(indexed, size):
            if sum(value for _, value in first) < MIN_SEQUENCE_SOURCE_SECONDS:
                continue
            used = {index for index, _ in first}
            remaining = sorted(
                (value for index, value in indexed if index not in used),
                reverse=True,
            )[:MAX_SEQUENCE_CLIPS]
            if _can_form_sequence(remaining):
                return True
    return False


def audit_registry(registry):
    assets = list(registry.get("assets") or [])
    selectable = [asset for asset in assets if is_selectable(asset)]
    counts = Counter(retention_category(asset) for asset in selectable)
    category_deficits = {
        category: max(0, minimum - counts.get(category, 0))
        for category, minimum in REQUIRED_CATEGORY_MINIMUMS.items()
    }
    total_deficit = max(0, MIN_SELECTABLE_ASSETS - len(selectable))
    inventory_ready = total_deficit == 0 and not any(category_deficits.values())
    sequence_pair_feasible = has_two_disjoint_sequences(selectable)
    required_new_assets = max(
        total_deficit,
        sum(category_deficits.values()),
        0 if sequence_pair_feasible else 1,
    )
    ready = inventory_ready and sequence_pair_feasible
    duration_ineligible = sum(
        1
        for asset in assets
        if asset.get("status") == "active"
        and asset.get("verified") is True
        and not sequence_clip_eligible(asset)
    )
    return {
        "status": "PASS" if ready else "REPLENISH",
        "ready": ready,
        "inventory_ready": inventory_ready,
        "sequence_pair_feasible": sequence_pair_feasible,
        "registry_assets": len(assets),
        "selectable_assets": len(selectable),
        "minimum_selectable_assets": MIN_SELECTABLE_ASSETS,
        "minimum_sequence_clip_seconds": MIN_SEQUENCE_CLIP_SECONDS,
        "sequence_clip_count_min": MIN_SEQUENCE_CLIPS,
        "sequence_clip_count_preferred": PREFERRED_SEQUENCE_CLIPS,
        "sequence_clip_count_max": MAX_SEQUENCE_CLIPS,
        "minimum_sequence_source_seconds": MIN_SEQUENCE_SOURCE_SECONDS,
        "preferred_sequence_source_seconds": PREFERRED_SEQUENCE_SOURCE_SECONDS,
        "maximum_sequence_source_seconds": MAX_SEQUENCE_SOURCE_SECONDS,
        "duration_ineligible_assets": duration_ineligible,
        "category_counts": dict(sorted(counts.items())),
        "required_category_minimums": REQUIRED_CATEGORY_MINIMUMS,
        "category_deficits": category_deficits,
        "required_new_assets_at_least": required_new_assets,
        "replenishment_required": not ready,
        "automatic_continuation_required": not ready,
    }


def main():
    parser = argparse.ArgumentParser(description="Wacky Dramas global background maintenance audit")
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
