"""Expose the live planner contract to ChatGPT/Work as machine-readable JSON.

This module intentionally imports authoritative production constants instead of
redeclaring them. It is a read-only discovery surface for planner authorship.
"""
from __future__ import annotations

import json

from common.workflow_common import CONTENT_ID_RE
from planning import ranked_promotion
from planning.planning_config import (
    ANTAGONIST_ROLES,
    CATEGORIES,
    EDITORIAL_WEIGHTS,
    EMOTIONS,
    ENDING_STYLES,
    HOOK_WEIGHTS,
    OPENING_STYLES,
    PROTAGONIST_ROLES,
    TITLE_STYLES,
    TITLE_WEIGHTS,
)
from validation import schema_v4
from validation.validate_content import SCHEMA_VERSION

ADHOC_PUBLICATION = {
    "mode": "immediate",
    "timezone": "Asia/Singapore",
    "publish_at": None,
}


def build_contract():
    """Return the current canonical fields ChatGPT must author against."""
    return {
        "request_schema_version": SCHEMA_VERSION,
        "ranked_pool_schema_version": ranked_promotion.POOL_SCHEMA_VERSION,
        "adhoc_pool_size": ranked_promotion.ADHOC_POOL_SIZE,
        "adhoc_planning_modes": sorted(ranked_promotion.ADHOC_PLANNING_MODES),
        "content_id_pattern": CONTENT_ID_RE.pattern,
        "candidate_id_pattern": ranked_promotion.CANDIDATE_ID_RE.pattern,
        "publication": ADHOC_PUBLICATION,
        "editorial_score_components": list(EDITORIAL_WEIGHTS),
        "title_score_components": list(TITLE_WEIGHTS),
        "hook_score_components": list(HOOK_WEIGHTS),
        "controlled_values": {
            "categories": sorted(CATEGORIES),
            "emotions": sorted(EMOTIONS),
            "opening_styles": sorted(OPENING_STYLES),
            "title_styles": sorted(TITLE_STYLES),
            "ending_styles": sorted(ENDING_STYLES),
            "protagonist_roles": sorted(PROTAGONIST_ROLES),
            "antagonist_roles": sorted(ANTAGONIST_ROLES),
            "voices": sorted(schema_v4.APPROVED_VOICES),
            "story_tones": sorted(schema_v4.STORY_TONES),
            "lead_genders": sorted(schema_v4.LEAD_GENDERS),
        },
        "narration": {
            "engine": "kokoro",
            "speed": 1.75,
        },
    }


def main():
    print(json.dumps(build_contract(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
