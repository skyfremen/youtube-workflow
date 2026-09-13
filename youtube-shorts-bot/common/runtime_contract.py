"""Private-side execution contract fingerprint with schema-v7 sequence semantics."""

import hashlib
import json

from common import runtime_contract_base as contract_impl
from media.continuous_background import PREFERRED_SEQUENCE_SOURCE_SECONDS
from validation import validate_content as schema

CONTRACT_PROTOCOL_VERSION = contract_impl.CONTRACT_PROTOCOL_VERSION
LEGACY_CONTRACT_HASHES = contract_impl.LEGACY_CONTRACT_HASHES


def contract_payload():
    payload = contract_impl.contract_payload()
    payload["schema"].update(
        {
            "sequence_segment_keys": sorted(schema.SEQUENCE_SEGMENT_KEYS),
            "background_modes": [schema.CONCATENATED_FIT_TO_SHORT_MODE],
            "fit_playback_rate_min": schema.FIT_PLAYBACK_RATE_MIN,
            "fit_playback_rate_max": schema.FIT_PLAYBACK_RATE_MAX,
            "max_segment_start_seconds": schema.MAX_SEGMENT_START_SECONDS,
            "min_sequence_clip_seconds": schema.MIN_SEQUENCE_CLIP_SECONDS,
            "min_sequence_clips": schema.MIN_SEQUENCE_CLIPS,
            "max_sequence_clips": schema.MAX_SEQUENCE_CLIPS,
            "min_sequence_source_seconds": schema.MIN_SEQUENCE_SOURCE_SECONDS,
            "preferred_sequence_source_seconds": PREFERRED_SEQUENCE_SOURCE_SECONDS,
            "max_sequence_source_seconds": schema.MAX_SEQUENCE_SOURCE_SECONDS,
            "runtime_derived_playback_rate": True,
            "normal_loop_count": 0,
            "primary_backup_disjoint": True,
        }
    )
    return payload


def canonical_contract_bytes():
    return json.dumps(
        contract_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def contract_hash():
    return hashlib.sha256(canonical_contract_bytes()).hexdigest()


if __name__ == "__main__":
    print(contract_hash())
