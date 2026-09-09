import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import request_guard


class RequestImmutabilityTests(unittest.TestCase):
    def test_new_request_is_accepted(self):
        request = "youtube-shorts-bot/content/requests/wd-20260908T161000-test-story-abc123.json"
        with patch.object(request_guard, "changed_files", return_value=[("A", request)]), \
             patch.object(request_guard, "parent_has_path", return_value=False):
            self.assertEqual(request_guard.resolve_push_request("deadbeef"), request)

    def test_modified_existing_request_is_rejected(self):
        request = "youtube-shorts-bot/content/requests/wd-20260908T161000-test-story-abc123.json"
        with patch.object(request_guard, "changed_files", return_value=[("M", request)]):
            with self.assertRaisesRegex(ValueError, "exactly one newly added"):
                request_guard.resolve_push_request("deadbeef")

    def test_added_request_existing_in_parent_is_rejected(self):
        request = "youtube-shorts-bot/content/requests/wd-20260908T161000-test-story-abc123.json"
        with patch.object(request_guard, "changed_files", return_value=[("A", request)]), \
             patch.object(request_guard, "parent_has_path", return_value=True):
            with self.assertRaisesRegex(ValueError, "immutable"):
                request_guard.resolve_push_request("deadbeef")

    def test_sensitive_change_with_request_is_rejected(self):
        request = "youtube-shorts-bot/content/requests/wd-20260908T161000-test-story-abc123.json"
        rows = [("A", request), ("M", "youtube-shorts-bot/render.py")]
        with patch.object(request_guard, "changed_files", return_value=rows), \
             patch.object(request_guard, "parent_has_path", return_value=False):
            with self.assertRaisesRegex(ValueError, "sensitive"):
                request_guard.resolve_push_request("deadbeef")

    def test_result_recovery_planning_and_sourcing_edits_are_rejected(self):
        from types import SimpleNamespace
        protected = (
            'youtube-shorts-bot/content/results/test.json',
            'youtube-shorts-bot/content/recovery/test/upload.json',
            'youtube-shorts-bot/content/planning/2099-01-01.json',
            'youtube-shorts-bot/content/background-sourcing/2099-01-01.json',
        )
        for status in ('M', 'D'):
            for path in protected:
                with patch.object(request_guard, 'git', return_value=SimpleNamespace(stdout=f"{status}\t{path}\n")):
                    with self.assertRaisesRegex(ValueError, 'Immutable'):
                        request_guard.check_immutable_changes('base', 'head')

    def test_new_recovery_and_sourcing_evidence_is_allowed(self):
        from types import SimpleNamespace
        for path in (
            'youtube-shorts-bot/content/recovery/test/upload.json',
            'youtube-shorts-bot/content/background-sourcing/2099-01-01.json',
        ):
            with patch.object(request_guard, 'git', return_value=SimpleNamespace(stdout=f'A\t{path}\n')):
                request_guard.check_immutable_changes('base', 'head')


if __name__ == "__main__":
    unittest.main()
