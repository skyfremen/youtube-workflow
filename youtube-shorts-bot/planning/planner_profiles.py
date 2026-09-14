"""Declarative Daily and Ad-hoc planner profiles.

Profiles describe new-planning policy only. Historical immutable pool compatibility
is handled explicitly by downstream promotion code; it is not part of the current
planner contract.
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
    candidate_count_policy: str
    global_media_readiness_required: bool
    automatic_replenishment_enabled: bool
    selected_background_validation_required: bool
    background_same_category_required: bool
    reserve_candidate_count: int
    post_commit_planner_monitoring: bool

    def expected_candidate_count(self, target_count: Optional[int]) -> int:
        if self.candidate_count_policy == "target_count":
            if isinstance(target_count, bool) or not isinstance(target_count, int):
                return 0
            return target_count
        return self.pool_size

    def contract_dict(self):
        payload = asdict(self)
        payload["planning_modes"] = sorted(self.planning_modes)
        return payload


DAILY = PlannerProfile(
    name="daily",
    pool_type="daily",
    pool_size=24,
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
    promotion_policy="all_required_candidates_must_validate_and_map_one_to_one_to_slots",
    scheduling_policy="canonical_hourly_slots_or_same_day_catch_up",
    diversity_policy="daily_batch_diversity_constraints",
    candidate_count_policy="target_count",
    global_media_readiness_required=False,
    automatic_replenishment_enabled=False,
    selected_background_validation_required=True,
    background_same_category_required=True,
    reserve_candidate_count=0,
    post_commit_planner_monitoring=False,
)

ADHOC = PlannerProfile(
    name="adhoc",
    pool_type="adhoc",
    pool_size=1,
    planning_modes=frozenset({"manual_on_demand"}),
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
    identity_policy="distinct_manual_invocation_namespace",
    uniqueness_policy="manual_on_demand_exact_identity_only",
    promotion_policy="single_required_candidate_must_validate",
    scheduling_policy="immediate_public",
    diversity_policy="single_candidate_semantic_quality",
    candidate_count_policy="fixed",
    global_media_readiness_required=False,
    automatic_replenishment_enabled=False,
    selected_background_validation_required=True,
    background_same_category_required=True,
    reserve_candidate_count=0,
    post_commit_planner_monitoring=False,
)

PROFILES = {"daily": DAILY, "adhoc": ADHOC}


def get_profile(name: str) -> PlannerProfile:
    try:
        return PROFILES[str(name).strip().lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported planner profile: {name}") from exc


def assert_profiles_do_not_override_shared_contract():
    """Structural drift guard: profiles must not own shared schema/creative contracts."""
    forbidden_fragments = {
        "schema",
        "voice",
        "narration",
        "punchline",
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
