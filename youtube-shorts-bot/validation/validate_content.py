"""Current private request validator.

Schema v4/v5/v6 remain immutable recovery formats. New production uses schema v7,
which freezes two or three distinct atomic background ranges per primary/backup
sequence. The public runtime concatenates the selected sequence once and derives
one playback rate only after the actual post-TTS render duration is known.
"""
from __future__ import annotations

import argparse
import copy
import math
from pathlib import Path

from common.workflow_common import load_json
from media.continuous_background import (
    CONCATENATED_FIT_TO_SHORT_MODE,
    DURATION_EPSILON_SECONDS,
    FIT_PLAYBACK_RATE_MAX,
    FIT_PLAYBACK_RATE_MIN,
    FIT_TO_SHORT_MODE,
    MAX_SEQUENCE_CLIPS,
    MAX_SEQUENCE_SOURCE_SECONDS,
    MIN_CONTINUOUS_SOURCE_SECONDS,
    MIN_SEQUENCE_CLIP_SECONDS,
    MIN_SEQUENCE_CLIPS,
    MIN_SEQUENCE_SOURCE_SECONDS,
    sequence_total_duration,
)
from media.media_readiness import audit_registry, is_selectable
from media.validate_media_library import asset_map, load_registry
from validation import validate_content_v5 as legacy5

SCHEMA_VERSION = 7
SUPPORTED_SCHEMA_VERSIONS = {4, 5, 6, 7}
FORBIDDEN_KEYS = legacy5.FORBIDDEN_KEYS
TOP_LEVEL_KEYS = legacy5.TOP_LEVEL_KEYS
STORY_KEYS = legacy5.STORY_KEYS
NARRATION_KEYS = legacy5.NARRATION_KEYS
YOUTUBE_KEYS = legacy5.YOUTUBE_KEYS
PUBLICATION_KEYS = legacy5.PUBLICATION_KEYS
PLANNING_KEYS = legacy5.PLANNING_KEYS
ATTRIBUTE_KEYS = legacy5.ATTRIBUTE_KEYS
TITLE_CANDIDATE_KEYS = legacy5.TITLE_CANDIDATE_KEYS
LEAD_GENDERS = legacy5.LEAD_GENDERS
NATURAL_TONES = legacy5.NATURAL_TONES
EXPRESSIVE_TONES = legacy5.EXPRESSIVE_TONES
STORY_TONES = legacy5.STORY_TONES
APPROVED_VOICES = legacy5.APPROVED_VOICES
expected_voice = legacy5.expected_voice

LEGACY_VISUAL_KEYS = legacy5.LEGACY_VISUAL_KEYS
V6_TREATMENT_KEYS = frozenset({
    "mode",
    "segment_start_seconds",
    "segment_duration_seconds",
})
V6_VISUAL_KEYS = frozenset({
    *LEGACY_VISUAL_KEYS,
    "background_primary_treatment",
    "background_backup_treatment",
})
SEQUENCE_SEGMENT_KEYS = frozenset({
    "background_id",
    "segment_start_seconds",
    "segment_duration_seconds",
})
V7_VISUAL_KEYS = frozenset({
    "background_mode",
    "background_primary_sequence",
    "background_backup_sequence",
})
PLAYBACK_RATE_MIN = FIT_PLAYBACK_RATE_MIN
PLAYBACK_RATE_MAX = FIT_PLAYBACK_RATE_MAX
MAX_SEGMENT_START_SECONDS = legacy5.MAX_SEGMENT_START_SECONDS
MIN_SEGMENT_DURATION_SECONDS = MIN_CONTINUOUS_SOURCE_SECONDS
TREATMENT_DURATION_EPSILON_SECONDS = DURATION_EPSILON_SECONDS


def _number(value, label, errors, *, minimum=None, maximum=None):
    if isinstance(value, bool):
        errors.append(f"{label} must be numeric")
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be numeric")
        return None
    if not math.isfinite(number):
        errors.append(f"{label} must be finite")
        return None
    if minimum is not None and number < minimum:
        errors.append(f"{label} must be >= {minimum:g}")
    if maximum is not None and number > maximum:
        errors.append(f"{label} must be <= {maximum:g}")
    return number


def validate_background_treatment(value, label="visual.background_treatment"):
    """Validate the historical schema-v6 single-source treatment."""
    errors = []
    if not isinstance(value, dict) or set(value) != V6_TREATMENT_KEYS:
        return [
            f"{label} must contain exactly mode, segment_start_seconds, "
            "segment_duration_seconds"
        ]
    if value.get("mode") != FIT_TO_SHORT_MODE:
        errors.append(f"{label}.mode must be {FIT_TO_SHORT_MODE}")
    _number(
        value.get("segment_start_seconds"),
        f"{label}.segment_start_seconds",
        errors,
        minimum=0.0,
        maximum=MAX_SEGMENT_START_SECONDS,
    )
    _number(
        value.get("segment_duration_seconds"),
        f"{label}.segment_duration_seconds",
        errors,
        minimum=MIN_CONTINUOUS_SOURCE_SECONDS,
    )
    return errors


def validate_background_sequence(value, label="visual.background_sequence"):
    errors = []
    if not isinstance(value, list):
        return [f"{label} must be a list of {MIN_SEQUENCE_CLIPS}-{MAX_SEQUENCE_CLIPS} segments"]
    if not MIN_SEQUENCE_CLIPS <= len(value) <= MAX_SEQUENCE_CLIPS:
        errors.append(
            f"{label} must contain {MIN_SEQUENCE_CLIPS}-{MAX_SEQUENCE_CLIPS} segments"
        )
    ids = []
    numeric_segments = []
    for index, segment in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(segment, dict) or set(segment) != SEQUENCE_SEGMENT_KEYS:
            errors.append(
                f"{item_label} must contain exactly background_id, "
                "segment_start_seconds, segment_duration_seconds"
            )
            continue
        asset_id = segment.get("background_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            errors.append(f"{item_label}.background_id must be a non-empty string")
        else:
            ids.append(asset_id)
        start = _number(
            segment.get("segment_start_seconds"),
            f"{item_label}.segment_start_seconds",
            errors,
            minimum=0.0,
            maximum=MAX_SEGMENT_START_SECONDS,
        )
        duration = _number(
            segment.get("segment_duration_seconds"),
            f"{item_label}.segment_duration_seconds",
            errors,
            minimum=MIN_SEQUENCE_CLIP_SECONDS,
        )
        if start is not None and duration is not None:
            numeric_segments.append(segment)
    if len(ids) != len(set(ids)):
        errors.append(f"{label} must not repeat a background_id")
    if len(numeric_segments) == len(value) and value:
        try:
            total = sequence_total_duration(value)
        except ValueError as exc:
            errors.append(f"{label}: {exc}")
        else:
            if total < MIN_SEQUENCE_SOURCE_SECONDS - DURATION_EPSILON_SECONDS:
                errors.append(
                    f"{label} total source duration must be >= {MIN_SEQUENCE_SOURCE_SECONDS:g}s"
                )
            if total > MAX_SEQUENCE_SOURCE_SECONDS + DURATION_EPSILON_SECONDS:
                errors.append(
                    f"{label} total source duration must be <= {MAX_SEQUENCE_SOURCE_SECONDS:g}s"
                )
    return errors


def treatment_for_slot(request, slot):
    if slot not in {"primary", "backup"}:
        raise ValueError("background slot must be primary or backup")
    version = request.get("schema_version")
    if version in {4, 5}:
        return legacy5.treatment_for_slot(request, slot)
    if version != 6:
        raise ValueError("treatment_for_slot is only valid through schema v6")
    treatment = (request.get("visual") or {}).get(f"background_{slot}_treatment")
    errors = validate_background_treatment(
        treatment, f"visual.background_{slot}_treatment"
    )
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "mode": FIT_TO_SHORT_MODE,
        "segment_start_seconds": float(treatment["segment_start_seconds"]),
        "segment_duration_seconds": float(treatment["segment_duration_seconds"]),
    }


def sequence_for_slot(request, slot):
    if slot not in {"primary", "backup"}:
        raise ValueError("background slot must be primary or backup")
    if request.get("schema_version") != 7:
        raise ValueError("sequence_for_slot requires schema v7")
    visual = request.get("visual") or {}
    if visual.get("background_mode") != CONCATENATED_FIT_TO_SHORT_MODE:
        raise ValueError("schema-v7 background_mode must be concatenated_fit_to_short")
    sequence = visual.get(f"background_{slot}_sequence")
    errors = validate_background_sequence(sequence, f"visual.background_{slot}_sequence")
    if errors:
        raise ValueError("; ".join(errors))
    return [
        {
            "background_id": str(item["background_id"]),
            "segment_start_seconds": float(item["segment_start_seconds"]),
            "segment_duration_seconds": float(item["segment_duration_seconds"]),
        }
        for item in sequence
    ]


def _as_v5_shape(data, primary_id=None, backup_id=None):
    candidate = copy.deepcopy(data)
    candidate["schema_version"] = 5
    visual = candidate.get("visual")
    if isinstance(visual, dict):
        if primary_id is None:
            primary_id = visual.get("background_primary_id")
        if backup_id is None:
            backup_id = visual.get("background_backup_id")
        candidate["visual"] = {
            "background_primary_id": primary_id,
            "background_backup_id": backup_id,
            "background_primary_treatment": {
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": None,
                "playback_rate": 1.0,
            },
            "background_backup_treatment": {
                "segment_start_seconds": 0.0,
                "segment_duration_seconds": None,
                "playback_rate": 1.0,
            },
        }
    return candidate


def _common_asset_errors(asset, asset_id, label):
    errors = []
    if not isinstance(asset, dict):
        return [f"{label} references unknown background asset {asset_id}"]
    if "selection_enabled" in asset:
        errors.append(f"{label} background {asset_id} uses obsolete selection_enabled state")
    if asset.get("status") != "active":
        errors.append(f"{label} background {asset_id} must be active")
    if asset.get("verified") is not True:
        errors.append(f"{label} background {asset_id} must be verified")
    if asset.get("commercial_use") is not True:
        errors.append(f"{label} background {asset_id} must allow commercial use")
    if asset.get("has_watermark") is not False:
        errors.append(f"{label} background {asset_id} must be watermark free")
    if asset.get("has_embedded_text") is not False:
        errors.append(f"{label} background {asset_id} must not contain embedded text")
    return errors


def _source_duration(asset):
    try:
        value = float(asset.get("duration_seconds"))
    except (AttributeError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def _v6_asset_errors(asset, asset_id, label, treatment):
    errors = _common_asset_errors(asset, asset_id, label)
    if not isinstance(asset, dict):
        return errors
    source_duration = _source_duration(asset)
    if source_duration is None:
        errors.append(f"{label} background {asset_id} requires trusted duration_seconds")
        return errors
    if source_duration + DURATION_EPSILON_SECONDS < MIN_CONTINUOUS_SOURCE_SECONDS:
        errors.append(f"{label} background {asset_id} is too short for continuous fit-to-short")
    if isinstance(treatment, dict):
        try:
            start = float(treatment["segment_start_seconds"])
            duration = float(treatment["segment_duration_seconds"])
        except (KeyError, TypeError, ValueError):
            return errors
        if start + duration > source_duration + DURATION_EPSILON_SECONDS:
            errors.append(f"{label} treatment exceeds background {asset_id} source duration")
    return errors


def _v7_asset_errors(asset, asset_id, label, segment):
    errors = _common_asset_errors(asset, asset_id, label)
    if not isinstance(asset, dict):
        return errors
    if not is_selectable(asset):
        errors.append(
            f"{label} background {asset_id} must satisfy current atomic media-readiness "
            "quality, retention, duration and production-rendition requirements"
        )
    source_duration = _source_duration(asset)
    if source_duration is None:
        errors.append(f"{label} background {asset_id} requires trusted duration_seconds")
        return errors
    try:
        start = float(segment["segment_start_seconds"])
        duration = float(segment["segment_duration_seconds"])
    except (KeyError, TypeError, ValueError):
        return errors
    if start + duration > source_duration + DURATION_EPSILON_SECONDS:
        errors.append(f"{label} selected range exceeds background {asset_id} source duration")
    return errors


def validate_background_registry_contract(data, registry=None):
    if not isinstance(data, dict) or data.get("schema_version") not in {6, 7}:
        return []
    visual = data.get("visual")
    if not isinstance(visual, dict):
        return ["visual must be an object before background registry validation"]
    try:
        registry = registry if registry is not None else load_registry()
        mapping = asset_map(registry)
    except (OSError, TypeError, ValueError) as exc:
        return [f"background registry is unavailable or invalid: {exc}"]

    errors = []
    if data.get("schema_version") == 6:
        primary_id = visual.get("background_primary_id")
        backup_id = visual.get("background_backup_id")
        if not isinstance(primary_id, str) or not primary_id.strip():
            errors.append("visual.background_primary_id must be a non-empty string")
        if not isinstance(backup_id, str) or not backup_id.strip():
            errors.append("visual.background_backup_id must be a non-empty string")
        if errors:
            return errors
        if primary_id == backup_id:
            errors.append("primary and backup background IDs must differ")
        for slot, asset_id in (("primary", primary_id), ("backup", backup_id)):
            errors.extend(
                _v6_asset_errors(
                    mapping.get(asset_id),
                    asset_id,
                    f"visual.background_{slot}_id",
                    visual.get(f"background_{slot}_treatment"),
                )
            )
        return errors

    try:
        primary = sequence_for_slot(data, "primary")
        backup = sequence_for_slot(data, "backup")
    except ValueError as exc:
        return [str(exc)]
    primary_ids = {item["background_id"] for item in primary}
    backup_ids = {item["background_id"] for item in backup}
    overlap = sorted(primary_ids & backup_ids)
    if overlap:
        errors.append(
            "primary and backup background sequences must be disjoint; overlap="
            + ", ".join(overlap)
        )
    for slot, sequence in (("primary", primary), ("backup", backup)):
        for index, segment in enumerate(sequence):
            asset_id = segment["background_id"]
            errors.extend(
                _v7_asset_errors(
                    mapping.get(asset_id),
                    asset_id,
                    f"visual.background_{slot}_sequence[{index}]",
                    segment,
                )
            )
    return errors


def _readiness_errors(registry_data):
    readiness = audit_registry(registry_data)
    if readiness["ready"]:
        return []
    deficits = {
        key: value
        for key, value in readiness["category_deficits"].items()
        if value
    }
    return [
        "shared background media readiness requires automatic replenishment "
        f"before new production: selectable={readiness['selectable_assets']}/"
        f"{readiness['minimum_selectable_assets']}; category_deficits={deficits}; "
        f"duration_ineligible={readiness['duration_ineligible_assets']}"
    ]


def _is_existing_immutable_request(request_path):
    """Return whether validation is operating on already-materialized request state."""
    return bool(request_path is not None and Path(request_path).is_file())


def _validate_v6(data, request_path=None, *, enforce_registry=False, registry=None):
    treatment_errors = []
    visual = data.get("visual")
    if not isinstance(visual, dict):
        treatment_errors.append("visual must be an object")
    else:
        missing = V6_VISUAL_KEYS - set(visual)
        extra = set(visual) - V6_VISUAL_KEYS
        if missing:
            treatment_errors.append("visual missing fields: " + ", ".join(sorted(missing)))
        if extra:
            treatment_errors.append("visual unexpected fields: " + ", ".join(sorted(extra)))
        for slot in ("primary", "backup"):
            treatment_errors.extend(
                validate_background_treatment(
                    visual.get(f"background_{slot}_treatment"),
                    f"visual.background_{slot}_treatment",
                )
            )
    errors = legacy5.validate_request_data(
        _as_v5_shape(data), request_path=request_path, enforce_registry=False
    )
    if enforce_registry and not errors and not treatment_errors:
        try:
            registry_data = registry if registry is not None else load_registry()
        except (OSError, TypeError, ValueError) as exc:
            errors.append(f"background registry is unavailable or invalid: {exc}")
        else:
            if not _is_existing_immutable_request(request_path):
                errors.extend(_readiness_errors(registry_data))
            errors.extend(validate_background_registry_contract(data, registry_data))
    return errors + treatment_errors


def _validate_v7(data, request_path=None, *, enforce_registry=False, registry=None):
    visual_errors = []
    visual = data.get("visual")
    primary = backup = None
    if not isinstance(visual, dict):
        visual_errors.append("visual must be an object")
    else:
        missing = V7_VISUAL_KEYS - set(visual)
        extra = set(visual) - V7_VISUAL_KEYS
        if missing:
            visual_errors.append("visual missing fields: " + ", ".join(sorted(missing)))
        if extra:
            visual_errors.append("visual unexpected fields: " + ", ".join(sorted(extra)))
        if visual.get("background_mode") != CONCATENATED_FIT_TO_SHORT_MODE:
            visual_errors.append(
                f"visual.background_mode must be {CONCATENATED_FIT_TO_SHORT_MODE}"
            )
        primary = visual.get("background_primary_sequence")
        backup = visual.get("background_backup_sequence")
        visual_errors.extend(
            validate_background_sequence(primary, "visual.background_primary_sequence")
        )
        visual_errors.extend(
            validate_background_sequence(backup, "visual.background_backup_sequence")
        )
        if isinstance(primary, list) and isinstance(backup, list):
            pids = {
                item.get("background_id") for item in primary if isinstance(item, dict)
            }
            bids = {
                item.get("background_id") for item in backup if isinstance(item, dict)
            }
            overlap = sorted(value for value in pids & bids if isinstance(value, str))
            if overlap:
                visual_errors.append(
                    "primary and backup background sequences must be disjoint; overlap="
                    + ", ".join(overlap)
                )

    first_primary = (
        primary[0].get("background_id")
        if isinstance(primary, list) and primary and isinstance(primary[0], dict)
        else "__invalid_primary__"
    )
    first_backup = (
        backup[0].get("background_id")
        if isinstance(backup, list) and backup and isinstance(backup[0], dict)
        else "__invalid_backup__"
    )
    errors = legacy5.validate_request_data(
        _as_v5_shape(data, first_primary, first_backup),
        request_path=request_path,
        enforce_registry=False,
    )
    if enforce_registry and not errors and not visual_errors:
        try:
            registry_data = registry if registry is not None else load_registry()
        except (OSError, TypeError, ValueError) as exc:
            errors.append(f"background registry is unavailable or invalid: {exc}")
        else:
            if not _is_existing_immutable_request(request_path):
                errors.extend(_readiness_errors(registry_data))
            errors.extend(validate_background_registry_contract(data, registry_data))
    return errors + visual_errors


def validate_request_data(data, request_path=None, *, enforce_registry=False, registry=None):
    if not isinstance(data, dict):
        return ["request root must be an object"]
    version = data.get("schema_version")
    if version in {4, 5}:
        return legacy5.validate_request_data(
            data,
            request_path=request_path,
            enforce_registry=enforce_registry,
            registry=registry,
        )
    if version == 6:
        return _validate_v6(
            data,
            request_path=request_path,
            enforce_registry=enforce_registry,
            registry=registry,
        )
    if version == 7:
        return _validate_v7(
            data,
            request_path=request_path,
            enforce_registry=enforce_registry,
            registry=registry,
        )
    return ["schema_version must be 4, 5, 6 or 7"]


def validate_request(path, *, enforce_registry=True):
    path = Path(path)
    data = load_json(path)
    errors = validate_request_data(
        data,
        request_path=path,
        enforce_registry=enforce_registry,
    )
    if errors:
        raise SystemExit("Request validation failed:\n- " + "\n- ".join(errors))
    print(f"Request valid: {path.name}; schema={data['schema_version']}")
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--schema-only", action="store_true")
    args = parser.parse_args()
    validate_request(args.request, enforce_registry=not args.schema_only)


if __name__ == "__main__":
    main()
