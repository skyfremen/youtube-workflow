import shutil
import subprocess

import pytest

from planning import planner_drift


def test_rules_drift_requires_full_refresh():
    result = planner_drift.classify_paths(
        ["youtube-shorts-bot/planning/planner_core.py"]
    )
    assert result["refresh"] == "full_refresh"
    assert result["changed_paths"]["rules"]


def test_media_drift_refreshes_media_without_full_rules_restart():
    result = planner_drift.classify_paths(
        ["youtube-shorts-bot/media-library/backgrounds.json"]
    )
    assert result["refresh"] == "media_refresh"
    assert result["changed_paths"]["media"]


def test_history_drift_refreshes_creative_history():
    result = planner_drift.classify_paths(
        ["youtube-shorts-bot/content/requests/wd-example.json"]
    )
    assert result["refresh"] == "history_refresh"
    assert result["changed_paths"]["history"]


def test_operational_only_drift_does_not_restart_planner():
    result = planner_drift.classify_paths(
        [
            "youtube-shorts-bot/content/recovery/example.json",
            ".state/observations/latest.json",
        ]
    )
    assert result["refresh"] == "operational_only"
    assert result["changed_paths"]["operational"]


def test_unknown_path_is_conservative_full_refresh():
    result = planner_drift.classify_paths(["unexpected/new-input.json"])
    assert result["refresh"] == "full_refresh"
    assert result["changed_paths"]["unknown"]


def test_precedence_rules_then_media_then_history_then_operational():
    assert planner_drift.classify_paths(
        [
            "youtube-shorts-bot/content/recovery/example.json",
            "youtube-shorts-bot/content/requests/example.json",
        ]
    )["refresh"] == "history_refresh"
    assert planner_drift.classify_paths(
        [
            "youtube-shorts-bot/content/requests/example.json",
            "youtube-shorts-bot/media-library/backgrounds.json",
        ]
    )["refresh"] == "media_refresh"
    assert planner_drift.classify_paths(
        [
            "youtube-shorts-bot/media-library/backgrounds.json",
            "youtube-shorts-bot/validation/schema_v4.py",
        ]
    )["refresh"] == "full_refresh"


def test_dot_state_path_normalization_is_not_lost():
    result = planner_drift.classify_paths(["./.state/observations/latest.json"])
    assert result["refresh"] == "operational_only"


def _git(cwd, *args):
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_git_compare_ignores_operational_only_head_movement(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "test")

    planning = tmp_path / "youtube-shorts-bot" / "planning"
    planning.mkdir(parents=True)
    (planning / "rule.txt").write_text("rules\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")

    recovery = tmp_path / "youtube-shorts-bot" / "content" / "recovery"
    recovery.mkdir(parents=True)
    (recovery / "event.json").write_text("{}\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "operational")
    head = _git(tmp_path, "rev-parse", "HEAD")

    monkeypatch.chdir(tmp_path)
    result = planner_drift.compare(base, head)
    assert result["refresh"] == "operational_only"
    assert (
        result["base_fingerprints"]["planner_contract_digest"]
        == result["head_fingerprints"]["planner_contract_digest"]
    )
    assert (
        result["base_fingerprints"]["media_state_digest"]
        == result["head_fingerprints"]["media_state_digest"]
    )
    assert (
        result["base_fingerprints"]["creative_history_digest"]
        == result["head_fingerprints"]["creative_history_digest"]
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_git_compare_detects_media_fingerprint_change(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "test")

    backgrounds = tmp_path / "youtube-shorts-bot" / "media-library"
    backgrounds.mkdir(parents=True)
    (backgrounds / "backgrounds.json").write_text("[]\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")

    (backgrounds / "backgrounds.json").write_text("[1]\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "media")
    head = _git(tmp_path, "rev-parse", "HEAD")

    monkeypatch.chdir(tmp_path)
    result = planner_drift.compare(base, head)
    assert result["refresh"] == "media_refresh"
    assert (
        result["base_fingerprints"]["media_state_digest"]
        != result["head_fingerprints"]["media_state_digest"]
    )
