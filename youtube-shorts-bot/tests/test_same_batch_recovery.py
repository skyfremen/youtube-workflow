import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from recovery import controller as recovery


NOW = datetime(2026, 9, 12, 0, 0, tzinfo=timezone.utc)
SOURCE = "a" * 40
CONTRACT = "b" * 64
DISPATCH = "d_" + "c" * 24
BATCH = recovery.normal_batch_id(SOURCE)


class FakeRepo:
    def __init__(self, snapshot):
        self.snapshot_value = snapshot
        self.root = Path(tempfile.mkdtemp())
        self.requests = self.root / "requests"
        self.requests.mkdir(parents=True)
        (self.requests / f"{snapshot.content_id}.json").write_text("{}")
        self.write_batch_called = False

    def snapshot(self, _path, *, now, failed_source_sha=""):
        return self.snapshot_value

    def write_batch(self, *_args, **_kwargs):
        self.write_batch_called = True
        raise AssertionError("same-batch no-start recovery must not create a replacement batch")

    def write_terminal(self, *_args, **_kwargs):
        raise AssertionError("unexpected terminal write")


class SameBatchRecoveryTests(unittest.TestCase):
    def test_no_start_recovery_preserves_exact_immutable_dispatch_identity(self):
        snap = recovery.Snapshot(
            content_id="wd-20260912T080000-test-a1b2c3",
            source_commit_sha=SOURCE,
            source_started_at=NOW - timedelta(hours=5),
            publish_at=NOW + timedelta(hours=8),
            receipt_state="missing",
            has_intent=False,
            has_upload=False,
            automatic_attempts=0,
            latest_batch_id=BATCH,
            latest_batch_started_at=NOW - timedelta(hours=5),
            latest_event="none",
            latest_event_at=None,
            latest_retryable=None,
            latest_error_code=None,
            latest_stage=None,
            latest_dispatch_id=DISPATCH,
            latest_dispatch_source_sha=SOURCE,
            latest_dispatch_contract_hash=CONTRACT,
            latest_prepared_at=NOW - timedelta(minutes=30),
            latest_dispatched_at=NOW - timedelta(minutes=30),
        )
        repo = FakeRepo(snap)
        result = recovery.reconcile(
            repo,
            now=NOW,
            policy=recovery.Policy(startup_grace_minutes=25),
            write=True,
        )
        self.assertTrue(result["dispatch"])
        self.assertEqual(result["dispatch_mode"], "same_batch")
        self.assertEqual(result["batch_id"], BATCH)
        self.assertEqual(result["dispatch_source_sha"], SOURCE)
        self.assertEqual(result["dispatch_contract_hash"], CONTRACT)
        self.assertEqual(result["content_ids"], [snap.content_id])
        self.assertFalse(repo.write_batch_called)


if __name__ == "__main__":
    unittest.main()
