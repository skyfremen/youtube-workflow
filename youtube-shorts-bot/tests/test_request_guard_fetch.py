import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from validation import request_guard


class RequestGuardFetchTests(unittest.TestCase):
    def test_missing_previous_commit_is_fetched_then_checked(self):
        sha = "a" * 40
        with patch.object(
            request_guard,
            "commit_available",
            side_effect=[False, True],
        ), patch.object(
            request_guard,
            "git",
            return_value=SimpleNamespace(returncode=0, stderr="", stdout=""),
        ) as git:
            request_guard.ensure_commit_available(sha)
        git.assert_called_once_with(
            ["fetch", "--no-tags", "--depth=1", "origin", sha],
            check=False,
        )

    def test_unavailable_previous_commit_fails_closed_with_clear_message(self):
        sha = "b" * 40
        with patch.object(
            request_guard,
            "commit_available",
            return_value=False,
        ), patch.object(
            request_guard,
            "git",
            return_value=SimpleNamespace(
                returncode=128,
                stderr="fatal: not our ref",
                stdout="",
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Cannot verify immutable production history",
            ):
                request_guard.ensure_commit_available(sha)


if __name__ == "__main__":
    unittest.main()
