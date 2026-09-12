"""Versioned private request validator with strict production background checks.

Schema v4 remains readable for immutable recovery. Newly authored schema-v5
requests freeze both logical backgrounds and AI-authored temporal/playback
treatments. Creative choice belongs to ChatGPT; this validator only enforces the
mechanical production contract and fails closed before public dispatch.
"""

import argparse
import copy
from pathlib import Path

from common.workflow_common import load_json
from media.background_policy import rendition_is_production_suitable
from media.background_selector_base import MIN_QUALITY_SCORE, quality_score
from media.validate_media_library import asset_map, load_registry
from validation import schema_v4 as legacy

SCHEMA_VERSION = 5
SUPPORTED_SCHEMA_VERSIONS = {4, 5}
FORBIDDEN_KEYS = legacy.FORBIDDEN_KEYS
TOP_LEVEL_KEYS = legacy.TOP_LEVEL_KEYS
STORY_KEYS = legacy.STORY_KEYS
NARRATION_KEYS = legacy.NARRATION_KEYS
YOUTUBE_KEYS = legacy.YOUTUBE_KEYS
PUBLICATION_KEYS = legacy.PUBLICATION_KEYS
PLANNING_KEYS = legacy.PLANNING_KEYS
ATTRIBUTE_KEYS = legacy.ATTRIBUTE_KEYS
TITLE_CANDIDATE_KEYS = legacy.TITLE_CANDIDATE_KEYS
LEAD_GENDERS = legacy.LEAD_GENDERS
NATURAL_TONES = legacy.NATURAL_TONES
EXPRESSIVE_TONES = legacy.EXPRESSIVE_TONES
STORY_TONES = legacy.STORY_TONES
APPROVED_VOICES = legacy.APPROVED_VOICES
expected_voice = legacy.expected_voice

LEGACY_VISUAL_KEYS = frozenset({"background_primary_id", "background_backup_id"})
TREATMENT_KEYS = frozenset({
    "segment_start_seconds",
    "segment_duration_seconds",
    "playback_rate",
})
VISUAL_KEYS = frozenset({
    *LEGACY_VISUAL_KEYS,
    "background_primary_treatment",
    "background_backup_treatment",
})
PLAYBACK_RATE_MIN = 1.0
PLAYBACK_RATE_MAX = 2.0
MAX_SEGMENT_START_SECONDS = 24 * 60 * 60
MIN_SEGMENT_DURATION_SECONDS = 1.0


def _number(value, label, errors, *, minimum=None, maximum=None, nullable=False):
    if value is None and nullable:
        return None
    if isinstance(value, bool):
        errors.append(f"{label} must be numeric" + (" or null" if nullable else ""))
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be numeric" + (" or null" if nullable else ""))
        return None
    if minimum is not None and number < minimum:
        errors.append(f"{label} must be >= {minimum:g}")
    if maximum is not None and number > maximum:
        errors.append(f"{label} must be <= {maximum:g}")
    return number


def validate_background_treatment(value, label="visual.background_treatment"):
    errors = []
    if not isinstance(value, dict) or set(value) != TREATMENT_KEYS:
        return [
            f"{label} must contain exactly segment_start_seconds, "
            "segment_duration_seconds, playback_rate"
        ]
    start = _number(
        value.get("segment_start_seconds"),
        f"{label}.segment_start_seconds",
        errors,
        minimum=0.0,
        maximum=MAX_SEGMENT_START_SECONDS,
    )
    duration = _number(
        value.get("segment_duration_seconds"),
        f"{label}.segment_duration_seconds",
        errors,
        minimum=MIN_SEGMENT_DURATION_SECONDS,
        nullable=True,
    )
    _number(
        value.get("playback_rate"),
        f"{label}.playback_rate",
        errors,
        minimum=PLAYBACK_RATE_MIN,
        maximum=PLAYBACK_RATE_MAX,
    )
    if duration is None and start not in (None, 0.0):
        errors.append(
            f"{label}.segment_start_seconds must be 0 when segment_duration_seconds is null"
        )
    return errors


def treatment_for_slot(request, slot):
    if slot not in {"primary", "backup"}:
        raise ValueError("background slot must be primary or backup")
    if request.get("schema_version") == 4:
        return {
            "segment_start_seconds": 0.0,
            "segment_duration_seconds": None,
            "playback_rate": 1.0,
        }
    visual = request.get("visual") or {}
    treatment = visual.get(f"background_{slot}_treatment")
    errors = validate_background_treatment(
        treatment, f"visual.background_{slot}_treatment"
    )
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "segment_start_seconds": float(treatment["segment_start_seconds"]),
        "segment_duration_seconds": (
            None
            if treatment["segment_duration_seconds"] is None
            else float(treatment["segment_duration_seconds"])
        ),
        "playback_rate": float(treatment["playback_rate"]),
    }


def _legacy_view(data):
    candidate = copy.deepcopy(data)
    candidate["schema_version"] = 4
    visual = candidate.get("visual")
    if isinstance(visual, dict):
        candidate["visual"] = {
            key: visual.get(key) for key in LEGACY_VISUAL_KEYS
        }
    return candidate


def _strict_background_errors(data, registry_data):
    errors = []
    visual = data.get("visual")
    if not isinstance(visual, dict):
        return ["visual must be an object before registered-background validation"]
    try:
        mapping = asset_map(registry_data)
    except (TypeError, KeyError, ValueError):
        return ["background registry is unavailable or invalid"]

    primary = str(visual.get("background_primary_id") or "")
    backup = str(visual.get("background_backup_id") or "")
    if not primary or not backup:
        return ["primary and backup logical background IDs are required"]
    if primary == backup:
        errors.append("Primary and backup background IDs must differ")

    for slot, asset_id in (("primary", primary), ("backup", backup)):
        label = f"visual.background_{slot}_id"
        asset = mapping.get(asset_id)
        if not asset:
            errors.append(f"{label} references unknown registered background {asset_id}")
            continue
        if asset.get("status") != "active":
            errors.append(f"background {asset_id} must be active")
        if asset.get("verified") is not True:
            errors.append(f"background {asset_id} must be verified")
        if asset.get("commercial_use") is not True:
            errors.append(f"background {asset_id} must allow commercial use")
        if not str(asset.get("license") or "").strip():
            errors.append(f"background {asset_id} must have a non-empty license")
        if not str(asset.get("source_page") or "").strip():
            errors.append(f"background {asset_id} must have a source page")
        if asset.get("has_watermark") is not False:
            errors.append(f"background {asset_id} must be watermark-free")
        if asset.get("has_embedded_text") is not False:
            errors.append(f"background {asset_id} must be embedded-text-free")
        try:
            if quality_score(asset) < MIN_QUALITY_SCORE:
                errors.append(f"background {asset_id} is below the hard quality floor")
        except (TypeError, ValueError):
            errors.append(f"background {asset_id} has invalid quality metadata")
        if not any(
            rendition_is_production_suitable(rendition)
            for rendition in asset.get("renditions", [])
            if isinstance(rendition, dict)
        ):
            errors.append(
                f"background {asset_id} has no production-suitable post-crop rendition"
            )

        if data.get("schema_version") == 5:
            treatment = visual.get(f"background_{slot}_treatment")
            if not isinstance(treatment, dict) or set(treatment) != TREATMENT_KEYS:
                continue
            try:
                start = float(treatment["segment_start_seconds"])
                duration = treatment["segment_duration_seconds"]
                duration = None if duration is None else float(duration)
            except (TypeError, ValueError):
                continue
            raw_asset_duration = asset.get("duration_seconds")
            if raw_asset_duration is None:
                if start != 0.0 or duration is not None:
                    errors.append(
                        f"background {asset_id} has unknown duration; treatment must use the full asset from 0"
                    )
            else:
                try:
                    asset_duration = float(raw_asset_duration)
                except (TypeError, ValueError):
                    errors.append(f"background {asset_id} duration metadata is invalid")
                    continue
                if start > asset_duration + 1e-6:
                    errors.append(
                        f"visual.background_{slot}_treatment starts beyond background duration"
                    )
                if duration is not None and start + duration > asset_duration + 1e-6:
                    errors.append(
                        f"visual.background_{slot}_treatment exceeds background duration"
                    )
    return errors


def validate_request_data(data, request_path=None, registry_data=None):
    if not isinstance(data, dict):
        return ["request root must be an object"]
    version = data.get("schema_version")
    if version == 4:
        errors = legacy.validate_request_data(data, request_path=request_path)
        if registry_data is not None:
            errors.extend(_strict_background_errors(data, registry_data))
        return errors
    if version != 5:
        return ["schema_version must be 4 or 5"]

    visual = data.get("visual")
    treatment_errors = []
    if not isinstance(visual, dict):
        treatment_errors.append("visual must be an object")
    else:
        missing = VISUAL_KEYS - set(visual)
        extra = set(visual) - VISUAL_KEYS
        if missing:
            treatment_errors.append(
                "visual missing fields: " + ", ".join(sorted(missing))
            )
        if extra:
            treatment_errors.append(
                "visual unexpected fields: " + ", ".join(sorted(extra))
            )
        for slot in ("primary", "backup"):
            treatment_errors.extend(
                validate_background_treatment(
                    visual.get(f"background_{slot}_treatment"),
                    f"visual.background_{slot}_treatment",
                )
            )

    errors = legacy.validate_request_data(
        _legacy_view(data), request_path=request_path
    )
    errors.extend(treatment_errors)
    if registry_data is not None:
        errors.extend(_strict_background_errors(data, registry_data))
    return errors


def validate_request(path, *, registry_data=None, strict=True):
    path = Path(path)
    data = load_json(path)
    if strict and registry_data is None:
        registry_data = load_registry()
    errors = validate_request_data(
        data,
        request_path=path,
        registry_data=registry_data if strict else None,
    )
    if errors:
        raise SystemExit("Request validation failed:\n- " + "\n- ".join(errors))
    print(f"Request valid: {path.name}; schema={data['schema_version']}")
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", action="append", required=True)
    parser.add_argument("--structural-only", action="store_true")
    args = parser.parse_args()
    registry = None if args.structural_only else load_registry()
    for request_path in args.request:
        validate_request(
            request_path,
            registry_data=registry,
            strict=not args.structural_only,
        )


if __name__ == "__main__":
    main()
