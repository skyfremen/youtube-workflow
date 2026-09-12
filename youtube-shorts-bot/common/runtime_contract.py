"""Private execution-contract fingerprint including v5 treatment semantics."""

import copy
import hashlib
import json

from common import runtime_contract_base as base
from common.runtime_contract_base import *  # re-export established contract helpers
from validation import validate_content as schema

CONTRACT_PROTOCOL_VERSION = base.CONTRACT_PROTOCOL_VERSION


def contract_payload():
    payload = copy.deepcopy(base.contract_payload())
    payload["schema"].update({
        "treatment_keys": sorted(schema.TREATMENT_KEYS),
        "playback_rate_min": schema.PLAYBACK_RATE_MIN,
        "playback_rate_max": schema.PLAYBACK_RATE_MAX,
        "max_segment_start_seconds": schema.MAX_SEGMENT_START_SECONDS,
        "min_segment_duration_seconds": schema.MIN_SEGMENT_DURATION_SECONDS,
    })
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
