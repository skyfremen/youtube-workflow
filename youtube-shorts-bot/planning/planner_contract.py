"""Live shared planner contract with continuous-background policy."""
import json

from media.continuous_background import (
    FIT_TO_SHORT_MODE,
    FIT_PLAYBACK_RATE_MIN,
    FIT_PLAYBACK_RATE_MAX,
    MIN_CONTINUOUS_SOURCE_SECONDS,
    PREFERRED_CONTINUOUS_RANGE_SECONDS,
)
from planning import planner_contract_base as base
from planning.planner_contract_base import *


def build_contract():
    contract = base.build_contract()
    readiness = dict(contract.get("media_readiness") or {})
    readiness.pop("retired_asset_flag", None)
    readiness.update({
        "active_registry": "media-library/backgrounds.json",
        "legacy_recovery_registry": "media-library/backgrounds-legacy-v5.json",
        "hard_reset_active_registry": True,
        "empty_registry_is_valid_replenish_state": True,
        "automatic_continuation_required": True,
        "normal_looping_allowed": False,
    })
    contract["media_readiness"] = readiness
    contract["background_treatment"] = {
        "mode": FIT_TO_SHORT_MODE,
        "planner_freezes_playback_rate": False,
        "runtime_derives_playback_rate_after_tts": True,
        "playback_rate_min": FIT_PLAYBACK_RATE_MIN,
        "playback_rate_max": FIT_PLAYBACK_RATE_MAX,
        "minimum_continuous_source_seconds": MIN_CONTINUOUS_SOURCE_SECONDS,
        "preferred_continuous_range_seconds": PREFERRED_CONTINUOUS_RANGE_SECONDS,
        "normal_looping_allowed": False,
        "primary_and_backup_required": True,
    }
    return contract


def main():
    print(json.dumps(build_contract(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
