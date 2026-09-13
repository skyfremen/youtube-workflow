import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from planning import planner_drift


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


class PlannerDriftTests(unittest.TestCase):
    def test_rules_drift_requires_full_refresh(self):
        result = planner_drift.classify_paths(
            ["youtube-shorts-bot/planning/planner_core.py"]
        )
        self.assertEqual(result["refresh"], "full_refresh")
        self.assertTrue(result["changed_paths"]["rules"])

    def test_media_drift_refreshes_media_without_full_rules_restart(self):
        result = planner_drift.classify_paths(
            ["youtube-shorts-bot/media-library/backgrounds.json"]
        )
        self.assertEqual(result["refresh"], "media_refresh")
        self.assertTrue(result["changed_paths"]["media"])

    def test_history_drift_refreshes_creative_history(self):
        result = planner_drift.classify_paths(
            ["youtube-shorts-bot/content/requests/wd-example.json"]
        )
        self.assertEqual(result["refresh"], "history_refresh")
        self.assertTrue(result["changed_paths"]["history"])

    def test_operational_only_drift_does_not_restart_planner(self):
        result = planner_drift.classify_paths(
            [
                "youtube-shorts-bot/content/recovery/example.json",
                ".state/observations/latest.json",
            ]
        )
        self.assertEqual(result["refresh"], "operational_only")
        self.assertTrue(result["changed_paths"]["operational"])

    def test_unknown_path_is_conservative_full_refresh(self):
        result = planner_drift.classify_paths(["unexpected/new-input.json"])
        self.assertEqual(result["refresh"], "full_refresh")
        self.assertTrue(result["changed_paths"]["unknown"])

    def test_precedence_rules_then_media_then_history_then_operational(self):
        self.assertEqual(
            planner_drift.classify_paths(
                [
                    "youtube-shorts-bot/content/recovery/example.json",
                    "youtube-shorts-bot/content/requests/example.json",
                ]
            )["refresh"],
            "history_refresh",
        )
        self.assertEqual(
            planner_drift.classify_paths(
                [
                    "youtube-shorts-bot/content/requests/example.json",
                    "youtube-shorts-bot/media-library/backgrounds.json",
                ]
            )["refresh"],
            "media_refresh",
        )
        self.assertEqual(
            planner_drift.classify_paths(
                [
                    "youtube-shorts-bot/media-library/backgrounds.json",
                    "youtube-shorts-bot/validation/schema_v4.py",
                ]
            )["refresh"],
            "full_refresh",
        )

    def test_dot_state_path_normalization_is_not_lost(self):
        result = planner_drift.classify_paths(
            ["./.state/observations/latest.json"]
        )
        self.assertEqual(result["refresh"], "operational_only")

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_git_compare_ignores_operational_only_head_movement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "test@example.invalid")
            _git(root, "config", "user.name", "test")

            planning = root / "youtube-shorts-bot" / "planning"
            planning.mkdir(parents=True)
            (planning / "rule.txt").write_text("rules\n", encoding="utf-8")
            _git(root, "add", ".")
            _git(root, "commit", "-qm", "base")
            base = _git(root, "rev-parse", "HEAD")

            recovery = root / "youtube-shorts-bot" / "content" / "recovery"
            recovery.mkdir(parents=True)
            (recovery / "event.json").write_text("{}\n", encoding="utf-8")
            _git(root, "add", ".")
            _git(root, "commit", "-qm", "operational")
            head = _git(root, "rev-parse", "HEAD")

            previous = os.getcwd()
            try:
                os.chdir(root)
                result = planner_drift.compare(base, head)
            finally:
                os.chdir(previous)

            self.assertEqual(result["refresh"], "operational_only")
            for digest in (
                "planner_contract_digest",
                "media_state_digest",
                "creative_history_digest",
            ):
                self.assertEqual(
                    result["base_fingerprints"][digest],
                    result["head_fingerprints"][digest],
                )

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_git_compare_detects_media_fingerprint_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "test@example.invalid")
            _git(root, "config", "user.name", "test")

            backgrounds = root / "youtube-shorts-bot" / "media-library"
            backgrounds.mkdir(parents=True)
            (backgrounds / "backgrounds.json").write_text(
                "[]\n", encoding="utf-8"
            )
            _git(root, "add", ".")
            _git(root, "commit", "-qm", "base")
            base = _git(root, "rev-parse", "HEAD")

            (backgrounds / "backgrounds.json").write_text(
                "[1]\n", encoding="utf-8"
            )
            _git(root, "add", ".")
            _git(root, "commit", "-qm", "media")
            head = _git(root, "rev-parse", "HEAD")

            previous = os.getcwd()
            try:
                os.chdir(root)
                result = planner_drift.compare(base, head)
            finally:
                os.chdir(previous)

            self.assertEqual(result["refresh"], "media_refresh")
            self.assertNotEqual(
                result["base_fingerprints"]["media_state_digest"],
                result["head_fingerprints"]["media_state_digest"],
            )


if __name__ == "__main__":
    unittest.main()
