"""Versioned private request validator with immutable background treatments.

Schema v4 remains readable for historical recovery. New planner output uses schema
v5. Production promotion validates schema-v5 requests against the current private
background registry before any public dispatch, while callers that only need pure
schema validation may leave registry enforcement disabled.
"""

import argparse
import copy
import math
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
TREATMENT_DURATION_EPSILON_SECONDS = 0.05


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
    if not math.isfinite(number):
        errors.append(f"{label} must be finite")
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
    if value.get("segment_duration_seconds") is None and start not in (None, 0.0):
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


def _production_rendition_exists(asset):
    renditions = asset.get("renditions")
    if not isinstance(renditions, list):
        return False
    return any(
        isinstance(item, dict) and rendition_is_production_suitable(item)
        for item in renditions
    )


def _validate_registry_asset(asset, asset_id, label, *, allow_retired=False):
    errors = []
    if not isinstance(asset, dict):
        return [f"{label} references unknown background asset {asset_id}"]
    if asset.get("selection_enabled") is False and not allow_retired:
        errors.append(
            f"{label} background {asset_id} is retired from new production selection"
        )
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
    if quality_score(asset) < MIN_QUALITY_SCORE:
        errors.append(f"{label} background {asset_id} is below the quality floor")
    if not _production_rendition_exists(asset):
        errors.append(
            f"{label} background {asset_id} has no production-suitable rendition"
        )
    return errors


def validate_background_registry_contract(data, registry=None, *, allow_retired=False):
    """Validate hard background/treatment invariants for a schema-v5 request.

    Creative relevance, recency preference and ranking remain ChatGPT-owned. This
    validator enforces only non-negotiable registry, licensing, production and
    treatment bounds so an AI-authored request cannot cross the dispatch boundary
    with an invalid physical contract. Recovery of an already-materialized immutable
    request may still resolve a background retired from future selection.
    """
    if not isinstance(data, dict) or data.get("schema_version") != 5:
        return []
    visual = data.get("visual")
    if not isinstance(visual, dict):
        return ["visual must be an object before background registry validation"]

    primary_id = visual.get("background_primary_id")
    backup_id = visual.get("background_backup_id")
    errors = []
    if not isinstance(primary_id, str) or not primary_id.strip():
        errors.append("visual.background_primary_id must be a non-empty string")
    if not isinstance(backup_id, str) or not backup_id.strip():
        errors.append("visual.background_backup_id must be a non-empty string")
    if errors:
        return errors
    if primary_id == backup_id:
        errors.append("primary and backup background IDs must differ")

    try:
        registry = registry if registry is not None else load_registry()
        mapping = asset_map(registry)
    except (OSError, TypeError, ValueError) as exc:
        return [f"background registry is unavailable or invalid: {exc}"]

    for slot, asset_id in (("primary", primary_id), ("backup", backup_id)):
        label = f"visual.background_{slot}_id"
        asset = mapping.get(asset_id)
        errors.extend(
            _validate_registry_asset(
                asset, asset_id, label, allow_retired=allow_retired
            )
        )
        if not isinstance(asset, dict):
            continue
        treatment = visual.get(f"background_{slot}_treatment")
        treatment_errors = validate_background_treatment(
            treatment, f"visual.background_{slot}_treatment"
        )
        if treatment_errors or not isinstance(treatment, dict):
            continue
        try:
            asset_duration = float(asset.get("duration_seconds"))
        except (TypeError, ValueError):
            asset_duration = None
        if asset_duration is not None and not math.isfinite(asset_duration):
            asset_duration = None
        if asset_duration is None or asset_duration <= 0:
            if not (
                float(treatment.get("segment_start_seconds")) == 0.0
                and treatment.get("segment_duration_seconds") is None
            ):
                errors.append(
                    f"visual.background_{slot}_treatment must use full-source treatment "
                    f"for background {asset_id} because source duration is unknown"
                )
            continue
        duration = treatment.get("segment_duration_seconds")
        if duration is None:
            continue
        try:
            start = float(treatment.get("segment_start_seconds"))
            segment_duration = float(duration)
        except (TypeError, ValueError):
            continue
        if start + segment_duration > asset_duration + TREATMENT_DURATION_EPSILON_SECONDS:
            errors.append(
                f"visual.background_{slot}_treatment exceeds background {asset_id} duration"
            )
    return errors


def validate_request_data(data, request_path=None, *, enforce_registry=False, registry=None):
    if not isinstance(data, dict):
        return ["request root must be an object"]
    version = data.get("schema_version")
    if version == 4:
        return legacy.validate_request_data(data, request_path=request_path)
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
    if enforce_registry and not errors and not treatment_errors:
        existing_immutable_request = bool(
            request_path is not None and Path(request_path).is_file()
        )
        errors.extend(
            validate_background_registry_contract(
                data,
                registry=registry,
                allow_retired=existing_immutable_request,
            )
        )
    return errors + treatment_errors


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
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Skip private registry enforcement; intended for isolated schema tests only",
    )
    args = parser.parse_args()
    validate_request(args.request, enforce_registry=not args.schema_only)


if __name__ == "__main__":
    main()
