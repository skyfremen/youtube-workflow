"""Declarative Daily and Ad-hoc planner profiles.

Profiles contain only mode-specific policy. Shared schema, semantic, media,
background, narration and candidate validation live in the shared planner core.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import FrozenSet, Optional

from planning.planning_config import CANONICAL_TIMEZONE


@dataclass(frozen=True)
class PlannerProfile:
    name: str
    pool_type: str
    pool_size: int
    planning_modes: FrozenSet[str]
    publication_template: dict
    date_field: str
    fixed_target_count: Optional[int]
    normal_mode: Optional[str]
    normal_target_count: Optional[int]
    has_publication_slots: bool
    identity_policy: str
    uniqueness_policy: str
    promotion_policy: str
    scheduling_policy: str
    diversity_policy: str

    def contract_dict(self):
        payload = asdict(self)
        payload["planning_modes"] = sorted(self.planning_modes)
        return payload


DAILY = PlannerProfile(
    name="daily",
    pool_type="daily",
    pool_size=36,
    planning_modes=frozenset({"normal_next_day", "same_day_catch_up"}),
    publication_template={
        "mode": "scheduled",
        "timezone": CANONICAL_TIMEZONE,
        "publish_at": None,
    },
    date_field="plan_date",
    fixed_target_count=None,
    normal_mode="normal_next_day",
    normal_target_count=24,
    has_publication_slots=True,
    identity_policy="date_scoped_daily_content_ids",
    uniqueness_policy="one_canonical_plan_per_plan_date_and_immutable_pool_attempt_ids",
    promotion_policy="preserve_frozen_rank_order_select_first_target_valid_candidates",
    scheduling_policy="canonical_hourly_slots_or_same_day_catch_up",
    diversity_policy="daily_batch_diversity_constraints",
)

ADHOC = PlannerProfile(
    name="adhoc",
    pool_type="adhoc",
    pool_size=5,
    planning_modes=frozenset({"scheduled_daily", "manual_on_demand"}),
    publication_template={
        "mode": "immediate",
        "timezone": CANONICAL_TIMEZONE,
        "publish_at": None,
    },
    date_field="singapore_date",
    fixed_target_count=1,
    normal_mode=None,
    normal_target_count=None,
    has_publication_slots=False,
    identity_policy="scheduled_010000_namespace_or_distinct_manual_invocation_namespace",
    uniqueness_policy="scheduled_daily_unique_per_singapore_date_manual_on_demand_exact_identity_only",
    promotion_policy="preserve_frozen_rank_order_select_first_valid_candidate",
    scheduling_policy="immediate_public",
    diversity_policy="ranked_pool_candidate_diversity",
)

PROFILES = {"daily": DAILY, "adhoc": ADHOC}


def get_profile(name: str) -> PlannerProfile:
    try:
        return PROFILES[str(name).strip().lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported planner profile: {name}") from exc


def assert_profiles_do_not_override_shared_contract():
    """Structural drift guard: profiles must not own shared contracts."""
    forbidden_fragments = {
        "schema",
        "semantic",
        "background",
        "voice",
        "narration",
        "punchline",
        "media_readiness",
        "request_validator",
    }
    fields = set(PlannerProfile.__dataclass_fields__)
    offenders = sorted(
        field for field in fields
        if any(fragment in field for fragment in forbidden_fragments)
    )
    if offenders:
        raise RuntimeError(
            "planner profile illegally overrides shared contract fields: "
            + ", ".join(offenders)
        )
    return True
