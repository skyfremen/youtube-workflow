"""Private immutable background segment/playback allocation.

Logical asset selection happens first. This module then reserves a deterministic
segment and playback rate using only private immutable success receipts plus
optional in-progress Daily-plan context. The public runtime receives the frozen
result and remains stateless across independent runs.
"""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from media.background_selector import (
    is_successful_receipt,
    load_successful_receipts,
    retention_category,
)
from media.validate_media_library import REGISTRY_PATH, asset_map, load_registry
from validation.validate_content import PLAYBACK_RATE_MAX, PLAYBACK_RATE_MIN

BASE = Path(__file__).resolve().parents[1]
RESULTS_DIR = BASE / "content" / "results"
SEGMENT_WINDOW_SECONDS = 12.0
SHORT_CLIP_FULL_USE_SECONDS = 18.0
RECENT_TREATMENT_LIMIT = 16
MEANINGFUL_OVERLAP_RATIO = 0.25

CATEGORY_SPEED_RANGES = {
    "cooking": (1.25, 1.55),
    "baking": (1.20, 1.50),
    "food_prep": (1.30, 1.65),
    "satisfying_process": (1.20, 1.70),
    "crafting": (1.20, 1.50),
    "cleaning": (1.30, 1.80),
    "assembly": (1.25, 1.60),
    "pov_movement": (1.10, 1.35),
    "city_motion": (1.15, 1.50),
    "licensed_gameplay": (1.00, 1.25),
    "generic": (1.00, 1.25),
}


def _timestamp(record):
    raw = record.get("receipt_created_at") or record.get("youtube_verified_at") or ""
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def _normalized_treatment(value):
    if not isinstance(value, dict):
        return None
    try:
        start = float(value.get("segment_start_seconds"))
        duration = value.get("segment_duration_seconds")
        duration = None if duration is None else float(duration)
        rate = float(value.get("playback_rate"))
    except (TypeError, ValueError):
        return None
    if start < 0 or duration is not None and duration <= 0:
        return None
    if not PLAYBACK_RATE_MIN <= rate <= PLAYBACK_RATE_MAX:
        return None
    return {
        "segment_start_seconds": round(start, 3),
        "segment_duration_seconds": None if duration is None else round(duration, 3),
        "playback_rate": round(rate, 3),
    }


def treatment_from_receipt(record):
    direct = _normalized_treatment(record.get("background_treatment"))
    if direct:
        return direct
    usage = record.get("background_usage") or {}
    if all(
        key in usage
        for key in (
            "segment_start_seconds",
            "segment_duration_seconds",
            "playback_rate",
        )
    ):
        return _normalized_treatment(usage)
    return None


def derive_treatment_history(receipts, asset_id, limit=RECENT_TREATMENT_LIMIT):
    records = sorted(
        (
            record
            for record in receipts
            if is_successful_receipt(record)
            and record.get("background_asset_id") == asset_id
            and treatment_from_receipt(record) is not None
        ),
        key=lambda record: (_timestamp(record), record.get("content_id", "")),
        reverse=True,
    )
    return [
        {
            "content_id": record.get("content_id"),
            "receipt_created_at": record.get("receipt_created_at"),
            "treatment": treatment_from_receipt(record),
        }
        for record in records[: max(0, int(limit))]
    ]


def _planned_for_asset(planned_treatments, asset_id):
    values = []
    for item in planned_treatments or ():
        if not isinstance(item, dict):
            continue
        planned_asset = item.get("asset_id") or item.get("logical_asset_id")
        if planned_asset != asset_id:
            continue
        treatment = _normalized_treatment(item.get("treatment") or item)
        if treatment:
            values.append(treatment)
    return values


def _overlap_ratio(left, right):
    if left.get("segment_duration_seconds") is None or right.get("segment_duration_seconds") is None:
        return 1.0
    l0 = float(left["segment_start_seconds"])
    l1 = l0 + float(left["segment_duration_seconds"])
    r0 = float(right["segment_start_seconds"])
    r1 = r0 + float(right["segment_duration_seconds"])
    overlap = max(0.0, min(l1, r1) - max(l0, r0))
    denominator = min(l1 - l0, r1 - r0)
    return 0.0 if denominator <= 0 else overlap / denominator


def _segment_candidates(duration_seconds):
    if duration_seconds is None:
        return [{
            "segment_start_seconds": 0.0,
            "segment_duration_seconds": None,
        }]
    try:
        duration = float(duration_seconds)
    except (TypeError, ValueError):
        return [{
            "segment_start_seconds": 0.0,
            "segment_duration_seconds": None,
        }]
    if duration < 1.0:
        return [{
            "segment_start_seconds": 0.0,
            "segment_duration_seconds": None,
        }]
    if duration <= SHORT_CLIP_FULL_USE_SECONDS:
        return [{
            "segment_start_seconds": 0.0,
            "segment_duration_seconds": round(duration, 3),
        }]

    window = min(SEGMENT_WINDOW_SECONDS, duration)
    last_start = max(0.0, duration - window)
    starts = [0.0]
    cursor = window
    while cursor < last_start - 0.05:
        starts.append(cursor)
        cursor += window
    starts.append(last_start)
    unique = []
    for start in starts:
        rounded = round(start, 3)
        if rounded not in unique:
            unique.append(rounded)
    return [
        {
            "segment_start_seconds": start,
            "segment_duration_seconds": round(window, 3),
        }
        for start in unique
    ]


def _segment_score(candidate, previous):
    overlaps = [_overlap_ratio(candidate, item) for item in previous]
    meaningful = sum(value >= MEANINGFUL_OVERLAP_RATIO for value in overlaps)
    weighted = sum(value / (index + 1) for index, value in enumerate(overlaps))
    max_overlap = max(overlaps, default=0.0)
    return meaningful, round(weighted, 6), round(max_overlap, 6), candidate["segment_start_seconds"]


def select_segment(asset, receipts, planned_treatments=()):
    candidates = _segment_candidates(asset.get("duration_seconds"))
    historical = [
        item["treatment"]
        for item in derive_treatment_history(receipts, asset["id"])
    ]
    planned = _planned_for_asset(planned_treatments, asset["id"])
    previous = [*planned, *historical]
    return min(candidates, key=lambda candidate: _segment_score(candidate, previous))


def speed_range(asset):
    category = retention_category(asset)
    default_min, default_max = CATEGORY_SPEED_RANGES.get(
        category, CATEGORY_SPEED_RANGES["generic"]
    )
    raw_min = asset.get("recommended_speed_min", default_min)
    raw_max = asset.get("recommended_speed_max", default_max)
    try:
        minimum = max(PLAYBACK_RATE_MIN, float(raw_min))
        maximum = min(PLAYBACK_RATE_MAX, float(raw_max))
    except (TypeError, ValueError):
        minimum, maximum = default_min, default_max
    if minimum > maximum:
        minimum, maximum = default_min, default_max
    return round(minimum, 3), round(maximum, 3)


def _speed_candidates(asset):
    minimum, maximum = speed_range(asset)
    midpoint = round((minimum + maximum) / 2.0, 3)
    return tuple(dict.fromkeys((minimum, midpoint, maximum)))


def select_playback_rate(asset, receipts, planned_treatments=()):
    candidates = _speed_candidates(asset)
    historical = [
        item["treatment"]["playback_rate"]
        for item in derive_treatment_history(receipts, asset["id"])
    ]
    planned = [
        item["playback_rate"]
        for item in _planned_for_asset(planned_treatments, asset["id"])
    ]
    recent = [*planned, *historical]
    counts = Counter(round(float(value), 3) for value in recent)
    last = round(float(recent[0]), 3) if recent else None
    return min(
        candidates,
        key=lambda rate: (
            counts[round(rate, 3)],
            int(last is not None and abs(rate - last) <= 1e-6),
            abs(rate - sum(candidates) / len(candidates)),
            rate,
        ),
    )


def select_background_treatment(asset, receipts, planned_treatments=()):
    segment = select_segment(asset, receipts, planned_treatments)
    return {
        **segment,
        "playback_rate": select_playback_rate(
            asset, receipts, planned_treatments
        ),
    }


def select_pair_treatments(
    registry,
    primary_id,
    backup_id,
    receipts,
    planned_treatments=(),
):
    mapping = asset_map(registry)
    if primary_id == backup_id:
        raise ValueError("primary and backup background IDs must differ")
    missing = [value for value in (primary_id, backup_id) if value not in mapping]
    if missing:
        raise ValueError("unknown logical background IDs: " + ", ".join(missing))
    primary = select_background_treatment(
        mapping[primary_id], receipts, planned_treatments
    )
    local_planned = [
        *(planned_treatments or ()),
        {"asset_id": primary_id, "treatment": primary},
    ]
    backup = select_background_treatment(
        mapping[backup_id], receipts, local_planned
    )
    return {
        "background_primary_treatment": primary,
        "background_backup_treatment": backup,
    }


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
    print(json.dumps(
        select_pair_treatments(
            registry,
            args.primary_id,
            args.backup_id,
            receipts,
            planned_treatments=planned,
        ),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
