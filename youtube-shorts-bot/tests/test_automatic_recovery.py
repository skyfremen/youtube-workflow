import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from recovery import controller as recovery

NOW = datetime(2026, 9, 11, 10, 0, tzinfo=timezone.utc)
SOURCE = 'a' * 40


def snapshot(**changes):
    base = recovery.Snapshot(
        content_id='wd-20260912T000000-test-a1b2c3',
        source_commit_sha=SOURCE,
        source_started_at=NOW - timedelta(hours=5),
        publish_at=NOW + timedelta(hours=8),
        receipt_state='missing',
        has_intent=False,
        has_upload=False,
        automatic_attempts=0,
        latest_batch_id=recovery.normal_batch_id(SOURCE),
        latest_batch_started_at=NOW - timedelta(hours=5),
        latest_event='none',
        latest_event_at=None,
        latest_retryable=None,
        latest_error_code=None,
        latest_stage=None,
        publication_mode='scheduled',
        terminal_exists=False,
        forced_source_failure=False,
    )
    return replace(base, **changes)


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.policy = recovery.Policy()

    def test_authoritative_receipt_is_complete(self):
        result = recovery.decide(snapshot(receipt_state='valid'), NOW, self.policy)
        self.assertEqual(result.state, 'completed')
        self.assertFalse(result.dispatch)

    def test_invalid_receipt_is_terminal(self):
        result = recovery.decide(snapshot(receipt_state='invalid'), NOW, self.policy)
        self.assertTrue(result.terminal)
        self.assertEqual(result.reason, 'invalid_immutable_receipt')

    def test_active_normal_run_is_not_recovered(self):
        result = recovery.decide(
            snapshot(latest_batch_started_at=NOW - timedelta(minutes=30)), NOW, self.policy
        )
        self.assertEqual(result.state, 'active')

    def test_stale_silent_run_is_recoverable(self):
        result = recovery.decide(snapshot(), NOW, self.policy)
        self.assertTrue(result.dispatch)
        self.assertEqual(result.reason, 'stale_unresolved_request')

    def test_stale_immediate_public_run_is_recoverable_without_schedule_expiry(self):
        result = recovery.decide(
            snapshot(publication_mode='immediate', publish_at=None), NOW, self.policy
        )
        self.assertTrue(result.dispatch)
        self.assertEqual(result.reason, 'stale_unresolved_request')

    def test_failed_private_dispatch_bypasses_grace(self):
        result = recovery.decide(
            snapshot(
                forced_source_failure=True,
                latest_batch_started_at=NOW - timedelta(minutes=1),
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)
        self.assertEqual(result.reason, 'private_dispatch_failed')

    def test_failed_immediate_private_dispatch_bypasses_grace(self):
        result = recovery.decide(
            snapshot(
                publication_mode='immediate',
                publish_at=None,
                forced_source_failure=True,
                latest_batch_started_at=NOW - timedelta(minutes=1),
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)
        self.assertEqual(result.reason, 'private_dispatch_failed')

    def test_retryable_failure_recovers_immediately_on_first_attempt(self):
        result = recovery.decide(
            snapshot(
                latest_event='diagnostic',
                latest_event_at=NOW - timedelta(minutes=1),
                latest_retryable=True,
                latest_error_code='E_EXEC_001',
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)
        self.assertEqual(result.reason, 'retryable_runtime_failure')

    def test_nonretryable_failure_is_terminal(self):
        result = recovery.decide(
            snapshot(
                latest_event='diagnostic',
                latest_event_at=NOW,
                latest_retryable=False,
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.terminal)
        self.assertEqual(result.reason, 'latest_failure_is_non_retryable')

    def test_unknown_retryability_is_terminal(self):
        result = recovery.decide(
            snapshot(
                latest_event='diagnostic',
                latest_event_at=NOW,
                latest_retryable=None,
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.terminal)
        self.assertEqual(result.reason, 'latest_failure_retryability_unknown')

    def test_second_attempt_obeys_backoff(self):
        result = recovery.decide(
            snapshot(
                automatic_attempts=1,
                latest_event='diagnostic',
                latest_event_at=NOW - timedelta(minutes=30),
                latest_retryable=True,
            ),
            NOW,
            self.policy,
        )
        self.assertEqual(result.state, 'pending')
        self.assertFalse(result.dispatch)

    def test_second_attempt_runs_after_backoff(self):
        result = recovery.decide(
            snapshot(
                automatic_attempts=1,
                latest_event='diagnostic',
                latest_event_at=NOW - timedelta(minutes=121),
                latest_retryable=True,
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)

    def test_max_attempts_is_terminal(self):
        result = recovery.decide(snapshot(automatic_attempts=3), NOW, self.policy)
        self.assertTrue(result.terminal)
        self.assertEqual(result.reason, 'maximum_automatic_attempts_reached')

    def test_recovery_in_progress_is_active(self):
        result = recovery.decide(
            snapshot(
                automatic_attempts=1,
                latest_batch_id='r_' + 'b' * 30,
                latest_batch_started_at=NOW - timedelta(minutes=20),
            ),
            NOW,
            self.policy,
        )
        self.assertEqual(result.state, 'active')

    def test_dispatch_or_runner_loss_becomes_recoverable_after_grace(self):
        result = recovery.decide(
            snapshot(
                automatic_attempts=1,
                latest_batch_id='r_' + 'b' * 30,
                latest_batch_started_at=NOW - timedelta(minutes=211),
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)

    def test_upload_evidence_allows_reconciliation_after_publish_window(self):
        result = recovery.decide(
            snapshot(has_upload=True, publish_at=NOW - timedelta(hours=1)),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)
        self.assertEqual(result.reason, 'durable_upload_state_needs_reconciliation')

    def test_immediate_upload_evidence_allows_reconciliation(self):
        result = recovery.decide(
            snapshot(
                publication_mode='immediate',
                publish_at=None,
                has_upload=True,
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)
        self.assertEqual(result.reason, 'durable_upload_state_needs_reconciliation')

    def test_intent_allows_crash_after_insert_reconciliation(self):
        result = recovery.decide(
            snapshot(has_intent=True, publish_at=NOW - timedelta(minutes=1)),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)

    def test_closed_slot_without_durable_evidence_is_terminal(self):
        result = recovery.decide(
            snapshot(publish_at=NOW + timedelta(minutes=5)), NOW, self.policy
        )
        self.assertTrue(result.terminal)
        self.assertEqual(
            result.reason, 'scheduled_window_closed_without_upload_evidence'
        )

    def test_immediate_request_never_uses_scheduled_window_terminal_rule(self):
        result = recovery.decide(
            snapshot(publication_mode='immediate', publish_at=None), NOW, self.policy
        )
        self.assertFalse(result.terminal)
        self.assertTrue(result.dispatch)

    def test_completed_batch_without_receipt_is_recoverable(self):
        result = recovery.decide(
            snapshot(
                latest_event='completion',
                latest_event_at=NOW - timedelta(minutes=1),
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)
        self.assertEqual(
            result.reason, 'batch_completed_without_authoritative_receipt'
        )

    def test_retryable_verification_failure_is_recoverable(self):
        result = recovery.decide(
            snapshot(
                latest_event='diagnostic',
                latest_event_at=NOW - timedelta(minutes=1),
                latest_retryable=True,
                latest_error_code='E_VERIFY_001',
                latest_stage='verify',
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)


class IdentityTests(unittest.TestCase):
    def test_duplicate_watchdog_invocations_resolve_same_batch(self):
        items = [
            {
                'content_id': 'wd-a',
                'source_commit_sha': 'a' * 40,
                'automatic_attempt': 1,
            },
            {
                'content_id': 'wd-b',
                'source_commit_sha': 'b' * 40,
                'automatic_attempt': 2,
            },
        ]
        self.assertEqual(
            recovery.automatic_batch_id(items),
            recovery.automatic_batch_id(list(reversed(items))),
        )

    def test_attempt_number_changes_recovery_identity(self):
        one = [
            {
                'content_id': 'wd-a',
                'source_commit_sha': 'a' * 40,
                'automatic_attempt': 1,
            }
        ]
        two = [
            {
                'content_id': 'wd-a',
                'source_commit_sha': 'a' * 40,
                'automatic_attempt': 2,
            }
        ]
        self.assertNotEqual(
            recovery.automatic_batch_id(one), recovery.automatic_batch_id(two)
        )


class FakeRepo:
    def __init__(self, root, snapshots):
        self.requests = Path(root) / 'requests'
        self.requests.mkdir(parents=True)
        self.snapshots = snapshots
        self.written_batches = []
        self.written_terminal = []
        for content_id in snapshots:
            (self.requests / f'{content_id}.json').write_text('{}')

    def snapshot(self, path, **_kwargs):
        return self.snapshots[path.stem]

    def write_terminal(self, snap, decision, **_kwargs):
        self.written_terminal.append((snap.content_id, decision.reason))
        return Path('/tmp') / f'{snap.content_id}.terminal.json'

    def write_batch(self, recoverable, **_kwargs):
        ids = [item[0].content_id for item in recoverable]
        self.written_batches.append(ids)
        return 'r_' + 'c' * 30, Path('/tmp/batch.json')


class ReconciliationTests(unittest.TestCase):
    def test_23_of_24_success_recovers_only_missing_item(self):
        snapshots = {}
        for index in range(24):
            content_id = f'wd-item-{index:02d}'
            snapshots[content_id] = snapshot(
                content_id=content_id,
                receipt_state='valid' if index < 23 else 'missing',
            )
        with tempfile.TemporaryDirectory() as tmp:
            repo = FakeRepo(tmp, snapshots)
            result = recovery.reconcile(
                repo, now=NOW, policy=recovery.Policy(), write=True
            )
        self.assertEqual(result['item_count'], 1)
        self.assertEqual(result['content_ids'], ['wd-item-23'])
        self.assertEqual(repo.written_batches, [['wd-item-23']])

    def test_24_of_24_success_dispatches_nothing(self):
        snapshots = {
            f'wd-item-{index:02d}': snapshot(
                content_id=f'wd-item-{index:02d}', receipt_state='valid'
            )
            for index in range(24)
        }
        with tempfile.TemporaryDirectory() as tmp:
            repo = FakeRepo(tmp, snapshots)
            result = recovery.reconcile(
                repo, now=NOW, policy=recovery.Policy(), write=True
            )
        self.assertFalse(result['dispatch'])
        self.assertEqual(result['item_count'], 0)
        self.assertEqual(repo.written_batches, [])


if __name__ == '__main__':
    unittest.main()
