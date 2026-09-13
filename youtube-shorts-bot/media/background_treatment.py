"""Private continuous-range allocation for schema-v6 background planning.

ChatGPT freezes one long continuous source range for each primary/backup logical
asset. The exact playback rate is deliberately NOT frozen here; public execution
derives it later from the actual post-TTS render duration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from media.background_selector import is_successful_receipt, load_successful_receipts
from media.continuous_background import (
    FIT_TO_SHORT_MODE,
    MIN_CONTINUOUS_SOURCE_SECONDS,
    preferred_range_duration,
    trusted_duration_seconds,
)
from media.validate_media_library import REGISTRY_PATH, asset_map, load_registry

BASE = Path(__file__).resolve().parents[1]
RESULTS_DIR = BASE / "content" / "results"
MEANINGFUL_OVERLAP_RATIO = 0.25
RECENT_TREATMENT_LIMIT = 24


def _normalized_range(value):
    if not isinstance(value, dict) or value.get("mode") != FIT_TO_SHORT_MODE:
        return None
    try:
        start = float(value.get("segment_start_seconds"))
        duration = float(value.get("segment_duration_seconds"))
    except (TypeError, ValueError):
        return None
    if start < 0 or duration < MIN_CONTINUOUS_SOURCE_SECONDS:
        return None
    return {
        "mode": FIT_TO_SHORT_MODE,
        "segment_start_seconds": round(start, 3),
        "segment_duration_seconds": round(duration, 3),
    }


def treatment_from_receipt(record):
    return _normalized_range(record.get("background_treatment")) or _normalized_range(record.get("background_usage"))


def derive_treatment_history(receipts, asset_id, limit=RECENT_TREATMENT_LIMIT):
    output = []
    for record in receipts:
        if not is_successful_receipt(record) or record.get("background_asset_id") != asset_id:
            continue
        treatment = treatment_from_receipt(record)
        if treatment:
            output.append(treatment)
        if len(output) >= max(0, int(limit)):
            break
    return output


def _planned_for_asset(planned_treatments, asset_id):
    output = []
    for item in planned_treatments or ():
        if not isinstance(item, dict):
            continue
        if (item.get("asset_id") or item.get("logical_asset_id")) != asset_id:
            continue
        treatment = _normalized_range(item.get("treatment") or item)
        if treatment:
            output.append(treatment)
    return output


def _overlap_ratio(left, right):
    l0 = float(left["segment_start_seconds"])
    l1 = l0 + float(left["segment_duration_seconds"])
    r0 = float(right["segment_start_seconds"])
    r1 = r0 + float(right["segment_duration_seconds"])
    overlap = max(0.0, min(l1, r1) - max(l0, r0))
    denominator = min(l1 - l0, r1 - r0)
    return 0.0 if denominator <= 0 else overlap / denominator


def _candidate_starts(source_duration, window):
    last = max(0.0, source_duration - window)
    starts = [0.0]
    cursor = window
    while cursor < last - 0.05:
        starts.append(cursor)
        cursor += window
    starts.append(last)
    return tuple(dict.fromkeys(round(value, 3) for value in starts))


def select_background_treatment(asset, receipts, planned_treatments=()):
    source_duration = trusted_duration_seconds(asset)
    if source_duration is None or source_duration < MIN_CONTINUOUS_SOURCE_SECONDS:
        raise ValueError(f"background {asset.get('id')} lacks sufficient trusted continuous duration")
    window = preferred_range_duration(asset)
    previous = [*_planned_for_asset(planned_treatments, asset["id"]), *derive_treatment_history(receipts, asset["id"])]
    candidates = [{
        "mode": FIT_TO_SHORT_MODE,
        "segment_start_seconds": start,
        "segment_duration_seconds": window,
    } for start in _candidate_starts(source_duration, window)]

    def score(candidate):
        overlaps = [_overlap_ratio(candidate, prior) for prior in previous]
        meaningful = sum(value >= MEANINGFUL_OVERLAP_RATIO for value in overlaps)
        weighted = sum(value / (index + 1) for index, value in enumerate(overlaps))
        return meaningful, round(weighted, 6), candidate["segment_start_seconds"]

    return min(candidates, key=score)


def select_pair_treatments(registry, primary_id, backup_id, receipts, planned_treatments=()):
    mapping = asset_map(registry)
    if primary_id == backup_id:
        raise ValueError("primary and backup background IDs must differ")
    missing = [value for value in (primary_id, backup_id) if value not in mapping]
    if missing:
        raise ValueError("unknown logical background IDs: " + ", ".join(missing))
    primary = select_background_treatment(mapping[primary_id], receipts, planned_treatments)
    local_planned = [*(planned_treatments or ()), {"asset_id": primary_id, "treatment": primary}]
    backup = select_background_treatment(mapping[backup_id], receipts, local_planned)
    return {"background_primary_treatment": primary, "background_backup_treatment": backup}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-id", required=True)
    parser.add_argument("--backup-id", required=True)
    parser.add_argument("--registry", default=str(REGISTRY_PATH))
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    parser.add_argument("--planned-json")
    args = parser.parse_args()
    registry = load_registry(args.registry)
    receipts = load_successful_receipts(args.results_dir)
    planned = []
    if args.planned_json:
        planned = json.loads(Path(args.planned_json).read_text(encoding="utf-8"))
        if not isinstance(planned, list):
            raise SystemExit("--planned-json must contain a list")
    print(json.dumps(select_pair_treatments(registry, args.primary_id, args.backup_id, receipts, planned), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
