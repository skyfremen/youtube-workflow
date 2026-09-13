from planning.planner_contract import build_contract


def test_media_replenishment_is_resumable_for_all_planners():
    readiness = build_contract()["media_readiness"]

    assert readiness["required_before_daily"] is True
    assert readiness["required_before_adhoc"] is True
    assert readiness["replenish_is_terminal"] is False
    assert readiness["automatic_continuation_required"] is True
    assert readiness["max_replenishment_attempts"] == 5
    assert readiness["resume_same_planner_invocation"] is True
    assert readiness["rejected_candidates_are_excluded_from_retry"] is True
    assert readiness["targeted_deficit_discovery"] is True
    assert readiness["replenishment_state_implementation"] == "media.replenishment_state"
    assert readiness["replenishment_manifest_is_allowed_prerequisite_commit"] is True
    assert readiness["pool_only_commit_rule_applies_after_readiness_pass"] is True

    sequence = readiness["replenishment_sequence"]
    assert sequence[0] == "audit returns REPLENISH"
    assert any("Background Management" in step for step in sequence)
    assert any("rerun media.media_readiness" in step for step in sequence)
    assert any("resume Daily or Ad-hoc ranked-pool authorship" in step for step in sequence)

    rules = readiness["rules"]
    assert any("resumable prerequisite state" in rule for rule in rules)
    assert any("commit only the ranked-pool JSON" in rule for rule in rules)
    assert any("Do not end a planning invocation" in rule for rule in rules)
    assert readiness["exhausted_error_code"] == "E_MEDIA_REPLENISH_EXHAUSTED"
