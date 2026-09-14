from planning.planner_contract import build_contract


def test_global_readiness_and_replenishment_are_not_planner_prerequisites():
    contract = build_contract()
    readiness = contract["media_readiness"]

    assert readiness["planner_uses_global_readiness"] is False
    assert readiness["required_before_daily"] is False
    assert readiness["required_before_adhoc"] is False
    assert readiness["automatic_continuation_required"] is False
    assert readiness["automatic_replenishment_enabled"] is False
    assert readiness["maintenance_only"] is True

    selected = contract["selected_background_validation"]
    assert selected["required"] is True
    assert selected["same_category_primary_backup"] is True
    assert selected["global_registry_readiness_required"] is False
    assert selected["validate_only_referenced_assets"] is True

    treatment = contract["background_treatment"]
    assert treatment["global_inventory_gate"] is False
    assert treatment["automatic_planner_replenishment"] is False
    assert treatment["same_category_primary_and_backup_required"] is True
    assert treatment["planner_freezes_playback_rate"] is False
    assert treatment["runtime_derives_playback_rate_after_tts"] is True
    assert treatment["canonical_fallback_category"]


def test_planner_recovery_is_repair_retry_not_replenishment():
    recovery = build_contract()["planner_recovery"]
    assert recovery["recoverable_failures_are_terminal"] is False
    assert recovery["repair_scope"] == "affected candidate or field only"
    assert "rerun same canonical checkpoint" in recovery["checkpoint_failure"]
    assert "alternate/fallback category" in recovery["background_failure"]
    assert recovery["post_commit"] == "end_planner"
