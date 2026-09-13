"""Current private request validator.

Schema v4/v5 remain immutable recovery formats. New production uses schema v6,
which freezes a long continuous source range and derives playback rate only after
public runtime knows actual post-TTS render duration.
"""
from __future__ import annotations

import argparse
import copy
import math
from pathlib import Path

from common.workflow_common import load_json
from media.continuous_background import FIT_TO_SHORT_MODE, FIT_PLAYBACK_RATE_MAX, FIT_PLAYBACK_RATE_MIN, MIN_CONTINUOUS_SOURCE_SECONDS, DURATION_EPSILON_SECONDS
from media.media_readiness import audit_registry
from media.validate_media_library import asset_map, load_registry
from validation import validate_content_v5 as legacy5

SCHEMA_VERSION = 6
SUPPORTED_SCHEMA_VERSIONS = {4, 5, 6}
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
TREATMENT_KEYS = frozenset({"mode", "segment_start_seconds", "segment_duration_seconds"})
VISUAL_KEYS = frozenset({*LEGACY_VISUAL_KEYS, "background_primary_treatment", "background_backup_treatment"})
PLAYBACK_RATE_MIN = FIT_PLAYBACK_RATE_MIN
PLAYBACK_RATE_MAX = FIT_PLAYBACK_RATE_MAX
MAX_SEGMENT_START_SECONDS = legacy5.MAX_SEGMENT_START_SECONDS
MIN_SEGMENT_DURATION_SECONDS = MIN_CONTINUOUS_SOURCE_SECONDS
TREATMENT_DURATION_EPSILON_SECONDS = DURATION_EPSILON_SECONDS
LEGACY_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "media-library" / "backgrounds-legacy-v5.json"


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
    errors = []
    if not isinstance(value, dict) or set(value) != TREATMENT_KEYS:
        return [f"{label} must contain exactly mode, segment_start_seconds, segment_duration_seconds"]
    if value.get("mode") != FIT_TO_SHORT_MODE:
        errors.append(f"{label}.mode must be {FIT_TO_SHORT_MODE}")
    _number(value.get("segment_start_seconds"), f"{label}.segment_start_seconds", errors, minimum=0.0, maximum=MAX_SEGMENT_START_SECONDS)
    _number(value.get("segment_duration_seconds"), f"{label}.segment_duration_seconds", errors, minimum=MIN_CONTINUOUS_SOURCE_SECONDS)
    return errors


def treatment_for_slot(request, slot):
    if slot not in {"primary", "backup"}:
        raise ValueError("background slot must be primary or backup")
    version = request.get("schema_version")
    if version in {4, 5}:
        return legacy5.treatment_for_slot(request, slot)
    if version != 6:
        raise ValueError("unsupported request schema")
    treatment = (request.get("visual") or {}).get(f"background_{slot}_treatment")
    errors = validate_background_treatment(treatment, f"visual.background_{slot}_treatment")
    if errors:
        raise ValueError("; ".join(errors))
    return {"mode": FIT_TO_SHORT_MODE, "segment_start_seconds": float(treatment["segment_start_seconds"]), "segment_duration_seconds": float(treatment["segment_duration_seconds"])}


def _as_v5_shape(data):
    candidate = copy.deepcopy(data)
    candidate["schema_version"] = 5
    visual = candidate.get("visual")
    if isinstance(visual, dict):
        for slot in ("primary", "backup"):
            visual[f"background_{slot}_treatment"] = {"segment_start_seconds": 0.0, "segment_duration_seconds": None, "playback_rate": 1.0}
    return candidate


def _asset_errors(asset, asset_id, label, treatment):
    errors = []
    if not isinstance(asset, dict):
        return [f"{label} references unknown background asset {asset_id}"]
    if "selection_enabled" in asset:
        errors.append(f"{label} background {asset_id} uses obsolete selection_enabled state")
    for ok, message in (
        (asset.get("status") == "active", "must be active"),
        (asset.get("verified") is True, "must be verified"),
        (asset.get("commercial_use") is True, "must allow commercial use"),
        (asset.get("has_watermark") is False, "must be watermark free"),
        (asset.get("has_embedded_text") is False, "must not contain embedded text"),
    ):
        if not ok:
            errors.append(f"{label} background {asset_id} {message}")
    try:
        source_duration = float(asset.get("duration_seconds"))
    except (TypeError, ValueError):
        source_duration = None
    if source_duration is None or not math.isfinite(source_duration):
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


def validate_background_registry_contract(data, registry=None):
    if not isinstance(data, dict) or data.get("schema_version") != 6:
        return []
    visual = data.get("visual")
    if not isinstance(visual, dict):
        return ["visual must be an object before background registry validation"]
    primary_id, backup_id = visual.get("background_primary_id"), visual.get("background_backup_id")
    errors = []
    if not isinstance(primary_id, str) or not primary_id.strip(): errors.append("visual.background_primary_id must be a non-empty string")
    if not isinstance(backup_id, str) or not backup_id.strip(): errors.append("visual.background_backup_id must be a non-empty string")
    if errors: return errors
    if primary_id == backup_id: errors.append("primary and backup background IDs must differ")
    try:
        registry = registry if registry is not None else load_registry()
        mapping = asset_map(registry)
    except (OSError, TypeError, ValueError) as exc:
        return [f"background registry is unavailable or invalid: {exc}"]
    for slot, asset_id in (("primary", primary_id), ("backup", backup_id)):
        errors.extend(_asset_errors(mapping.get(asset_id), asset_id, f"visual.background_{slot}_id", visual.get(f"background_{slot}_treatment")))
    return errors


def validate_request_data(data, request_path=None, *, enforce_registry=False, registry=None):
    if not isinstance(data, dict): return ["request root must be an object"]
    version = data.get("schema_version")
    if version in {4, 5}:
        if enforce_registry and version == 5 and registry is None and LEGACY_REGISTRY_PATH.is_file():
            registry = legacy5.load_registry(LEGACY_REGISTRY_PATH)
        return legacy5.validate_request_data(data, request_path=request_path, enforce_registry=enforce_registry, registry=registry)
    if version != 6: return ["schema_version must be 4, 5 or 6"]
    errors = []
    visual = data.get("visual")
    if not isinstance(visual, dict): errors.append("visual must be an object")
    else:
        missing, extra = VISUAL_KEYS - set(visual), set(visual) - VISUAL_KEYS
        if missing: errors.append("visual missing fields: " + ", ".join(sorted(missing)))
        if extra: errors.append("visual unexpected fields: " + ", ".join(sorted(extra)))
        for slot in ("primary", "backup"):
            errors.extend(validate_background_treatment(visual.get(f"background_{slot}_treatment"), f"visual.background_{slot}_treatment"))
    shared = legacy5.validate_request_data(_as_v5_shape(data), request_path=request_path, enforce_registry=False)
    if enforce_registry and not shared and not errors:
        try:
            registry_data = registry if registry is not None else load_registry()
        except (OSError, TypeError, ValueError) as exc:
            shared.append(f"background registry is unavailable or invalid: {exc}")
        else:
            readiness = audit_registry(registry_data)
            if not readiness["ready"]:
                deficits = {k:v for k,v in readiness["category_deficits"].items() if v}
                shared.append(f"shared background media readiness requires automatic replenishment before new production: selectable={readiness['selectable_assets']}/{readiness['minimum_selectable_assets']}; category_deficits={deficits}; duration_ineligible={readiness['duration_ineligible_assets']}")
            shared.extend(validate_background_registry_contract(data, registry_data))
    return shared + errors


def validate_request(path, *, enforce_registry=True):
    path = Path(path)
    data = load_json(path)
    errors = validate_request_data(data, request_path=path, enforce_registry=enforce_registry)
    if errors: raise SystemExit("Request validation failed:\n- " + "\n- ".join(errors))
    print(f"Request valid: {path.name}; schema={data['schema_version']}")
    return data


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--request", required=True); parser.add_argument("--schema-only", action="store_true"); args = parser.parse_args()
    validate_request(args.request, enforce_registry=not args.schema_only)


if __name__ == "__main__": main()
