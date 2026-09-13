"""Private execution-contract fingerprint for schema-v6 continuous backgrounds."""

import copy
import hashlib
import json

from common import runtime_contract_base as contract_impl
from media.continuous_background import (
    FIT_PLAYBACK_RATE_MAX,
    FIT_PLAYBACK_RATE_MIN,
    FIT_TO_SHORT_MODE,
    MIN_CONTINUOUS_SOURCE_SECONDS,
    PREFERRED_CONTINUOUS_RANGE_SECONDS,
)
from validation import validate_content as schema

CONTRACT_PROTOCOL_VERSION = contract_impl.CONTRACT_PROTOCOL_VERSION


def contract_payload():
    payload = copy.deepcopy(contract_impl.contract_payload())
    payload["schema"].update(
        {
            "treatment_keys": sorted(schema.TREATMENT_KEYS),
            "background_modes": [FIT_TO_SHORT_MODE],
            "fit_playback_rate_min": FIT_PLAYBACK_RATE_MIN,
            "fit_playback_rate_max": FIT_PLAYBACK_RATE_MAX,
            "max_segment_start_seconds": schema.MAX_SEGMENT_START_SECONDS,
            "min_continuous_source_seconds": MIN_CONTINUOUS_SOURCE_SECONDS,
            "preferred_continuous_range_seconds": PREFERRED_CONTINUOUS_RANGE_SECONDS,
            "runtime_derived_playback_rate": True,
            "normal_loop_count": 0,
        }
    )
    return payload


def canonical_contract_bytes():
    return json.dumps(
        contract_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def contract_hash():
    return hashlib.sha256(canonical_contract_bytes()).hexdigest()


if __name__ == "__main__":
    print(contract_hash())
