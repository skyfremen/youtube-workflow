import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from validation import request_guard


class RequestImmutabilityTests(unittest.TestCase):
    def test_existing_immutable_json_edits_and_deletions_are_rejected(self):
        protected = (
            "youtube-shorts-bot/content/requests/test.json",
            "youtube-shorts-bot/content/results/test.json",
            "youtube-shorts-bot/content/recovery/test/upload.json",
            "youtube-shorts-bot/content/recovery/index/test.json",
            "youtube-shorts-bot/content/recovery/index/bootstrap.json",
            "youtube-shorts-bot/content/planning/2099-01-01.json",
            "youtube-shorts-bot/content/background-sourcing/2099-01-01.json",
        )
        for status in ("M", "D"):
            for path in protected:
                with self.subTest(status=status, path=path):
                    with patch.object(
                        request_guard,
                        "git",
                        return_value=SimpleNamespace(stdout=f"{status}\t{path}\n"),
                    ):
                        with self.assertRaisesRegex(ValueError, "Immutable"):
                            request_guard.check_immutable_changes("base", "head")

    def test_new_immutable_json_is_allowed(self):
        protected = (
            "youtube-shorts-bot/content/requests/test.json",
            "youtube-shorts-bot/content/results/test.json",
            "youtube-shorts-bot/content/recovery/test/upload.json",
            "youtube-shorts-bot/content/recovery/index/test.json",
            "youtube-shorts-bot/content/recovery/index/bootstrap.json",
            "youtube-shorts-bot/content/planning/2099-01-01.json",
            "youtube-shorts-bot/content/background-sourcing/2099-01-01.json",
        )
        for path in protected:
            with self.subTest(path=path):
                with patch.object(
                    request_guard,
                    "git",
                    return_value=SimpleNamespace(stdout=f"A\t{path}\n"),
                ):
                    request_guard.check_immutable_changes("base", "head")

    def test_non_json_changes_are_ignored_by_immutable_guard(self):
        with patch.object(
            request_guard,
            "git",
            return_value=SimpleNamespace(
                stdout="M\tyoutube-shorts-bot/content/requests/.gitkeep\n"
            ),
        ):
            request_guard.check_immutable_changes("base", "head")


if __name__ == "__main__":
    unittest.main()
