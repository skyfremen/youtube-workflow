import json
from pathlib import Path


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent


def test_machine_contract_requires_durable_bounded_replenishment():
    manifest = json.loads(
        (BOT_ROOT / "planning" / "PLANNER_MATERIALIZATION.json").read_text(
            encoding="utf-8"
        )
    )
    continuation = manifest["background_replenishment_continuation"]
    assert continuation["state"] == "recoverable_intermediate"
    assert continuation["discovery_request_schema_version"] == 2
    assert continuation["review_decision_schema_version"] == 1
    assert continuation["session_identity_field"] == "replenishment_session_id"
    assert continuation["max_attempts"] == 5
    assert continuation["terminal_exhausted_code"] == "E_MEDIA_REPLENISH_EXHAUSTED"
    assert continuation["durable_review_exclusion"]["enabled"] is True
    rules = " ".join(continuation["rules"])
    assert "same original Daily or Ad-hoc planner invocation" in rules
    assert "same-session reviewed provider IDs" in rules
    assert "next immutable targeted attempt automatically" in rules


def test_shared_prompt_requires_repository_backed_review_memory():
    shared = (REPO_ROOT / "docs" / "private" / "PLANNER_PROMPT.md").read_text(
        encoding="utf-8"
    )
    assert "review-decisions/<request_id>.json" in shared
    assert "authoritative session memory" in shared
    assert "automatically unions all provider IDs already reviewed" in shared
    assert "attempt < 5" in shared
    assert "E_MEDIA_REPLENISH_EXHAUSTED" in shared
