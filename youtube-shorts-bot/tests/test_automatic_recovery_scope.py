import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from recovery import controller as recovery


class ManualOnlyRepo:
    def __init__(self, root):
        self.requests = Path(root) / "requests"
        self.requests.mkdir(parents=True)
        (self.requests / "wd-legacy-v3.json").write_text("{}", encoding="utf-8")
        self.write_batch_called = False
        self.write_terminal_called = False

    def snapshot(self, _path, **_kwargs):
        raise recovery.ManualOnly("non_current_request_schema")

    def write_batch(self, *_args, **_kwargs):
        self.write_batch_called = True
        raise AssertionError("legacy request must not be automatically dispatched")

    def write_terminal(self, *_args, **_kwargs):
        self.write_terminal_called = True
        raise AssertionError("legacy request must not create automatic terminal state")


class AutomaticRecoveryScopeTests(unittest.TestCase):
    def test_legacy_request_is_manual_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = ManualOnlyRepo(tmp)
            result = recovery.reconcile(
                repo,
                now=datetime(2026, 9, 11, 10, 0, tzinfo=timezone.utc),
                policy=recovery.Policy(),
                write=True,
            )
        self.assertFalse(result["dispatch"])
        self.assertEqual(result["item_count"], 0)
        self.assertEqual(result["terminal_count"], 0)
        self.assertEqual(result["decisions"][0]["state"], "manual_only")
        self.assertEqual(result["decisions"][0]["reason"], "non_current_request_schema")
        self.assertFalse(repo.write_batch_called)
        self.assertFalse(repo.write_terminal_called)


if __name__ == "__main__":
    unittest.main()
