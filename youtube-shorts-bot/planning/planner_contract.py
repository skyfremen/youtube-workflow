"""Live shared planner contract with sequence-background policy."""
import json

from media.continuous_background import (
    CONCATENATED_FIT_TO_SHORT_MODE,
    FIT_PLAYBACK_RATE_MAX,
    FIT_PLAYBACK_RATE_MIN,
    MAX_SEQUENCE_CLIPS,
    MAX_SEQUENCE_SOURCE_SECONDS,
    MIN_SEQUENCE_CLIP_SECONDS,
    MIN_SEQUENCE_CLIPS,
    MIN_SEQUENCE_SOURCE_SECONDS,
    PREFERRED_SEQUENCE_CLIPS,
    PREFERRED_SEQUENCE_SOURCE_SECONDS,
)
from planning import planner_contract_base as base
from planning.planner_contract_base import *


def build_contract():
    contract = base.build_contract()
    readiness = dict(contract.get("media_readiness") or {})
    readiness.pop("retired_asset_flag", None)
    readiness.update({
        "active_registry": "media-library/backgrounds.json",
        "hard_reset_active_registry": True,
        "empty_registry_is_valid_replenish_state": True,
        "automatic_continuation_required": True,
        "atomic_clip_minimum_seconds": MIN_SEQUENCE_CLIP_SECONDS,
        "normal_looping_allowed": False,
        "preview_review": {
            "required_before_verified_preview": True,
            "full_video_playback_required": False,
            "metadata_only_sufficient": False,
            "acceptable_visual_evidence": [
                "provider_page_visual_preview",
                "representative_preview_frames",
                "short_preview_clip",
            ],
            "review_goal": (
                "Confirm the source is visually suitable for background use and reject "
                "obvious watermarks, embedded text, unsafe material, static/weak footage, "
                "or misleading metadata using the strongest visual preview evidence "
                "available in the current ChatGPT/Work execution surface."
            ),
            "verified_preview_semantics": (
                "verified_preview=true means ChatGPT/Work reviewed actual visual preview "
                "evidence for the exact provider source; it does not assert that the full "
                "source video was played end-to-end."
            ),
            "downstream_verification": (
                "Background Management remains responsible for official Pexels identity, "
                "duration and rendition enrichment plus hard registry validation before "
                "an asset becomes selectable."
            ),
            "failure_rule": (
                "If no actual visual preview evidence for the exact source is accessible, "
                "do not set verified_preview=true for that candidate; reject it and continue "
                "discovery/reserve sourcing rather than failing replenishment merely because "
                "full-length playback is unavailable."
            ),
        },
    })
    contract["media_readiness"] = readiness
    contract["background_treatment"] = {
        "mode": CONCATENATED_FIT_TO_SHORT_MODE,
        "request_schema_version": contract["request_schema_version"],
        "planner_freezes_clip_order": True,
        "planner_freezes_segment_ranges": True,
        "planner_freezes_playback_rate": False,
        "runtime_derives_playback_rate_after_tts": True,
        "playback_rate_min": FIT_PLAYBACK_RATE_MIN,
        "playback_rate_max": FIT_PLAYBACK_RATE_MAX,
        "minimum_atomic_clip_seconds": MIN_SEQUENCE_CLIP_SECONDS,
        "sequence_clip_count_min": MIN_SEQUENCE_CLIPS,
        "sequence_clip_count_preferred": PREFERRED_SEQUENCE_CLIPS,
        "sequence_clip_count_max": MAX_SEQUENCE_CLIPS,
        "minimum_sequence_source_seconds": MIN_SEQUENCE_SOURCE_SECONDS,
        "preferred_sequence_source_seconds": PREFERRED_SEQUENCE_SOURCE_SECONDS,
        "maximum_sequence_source_seconds": MAX_SEQUENCE_SOURCE_SECONDS,
        "normal_looping_allowed": False,
        "primary_and_backup_required": True,
        "primary_and_backup_must_be_disjoint": True,
    }
    return contract


def main():
    print(json.dumps(build_contract(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
