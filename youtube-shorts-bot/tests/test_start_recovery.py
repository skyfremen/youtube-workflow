import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from recovery import controller as recovery


NOW = datetime(2026, 9, 12, 0, 0, tzinfo=timezone.utc)
SOURCE = "a" * 40
CONTRACT = "b" * 64
DISPATCH = "d_" + "c" * 24


def snapshot(**changes):
    base = recovery.Snapshot(
        content_id="wd-20260912T080000-test-a1b2c3",
        source_commit_sha=SOURCE,
        source_started_at=NOW - timedelta(hours=5),
        publish_at=NOW + timedelta(hours=8),
        receipt_state="missing",
        has_intent=False,
        has_upload=False,
        automatic_attempts=0,
        latest_batch_id=recovery.normal_batch_id(SOURCE),
        latest_batch_started_at=NOW - timedelta(hours=5),
        latest_event="none",
        latest_event_at=None,
        latest_retryable=None,
        latest_error_code=None,
        latest_stage=None,
        terminal_exists=False,
        forced_source_failure=False,
        latest_dispatch_id=DISPATCH,
        latest_dispatch_source_sha=SOURCE,
        latest_dispatch_contract_hash=CONTRACT,
        latest_prepared_at=NOW - timedelta(minutes=30),
        latest_dispatched_at=NOW - timedelta(minutes=30),
        latest_dispatch_failed_at=None,
        latest_started_at=None,
        latest_started_dispatch_id="",
        current_dispatch_started_at=None,
    )
    return replace(base, **changes)


class FastNoStartDecisionTests(unittest.TestCase):
    def setUp(self):
        self.policy = recovery.Policy(startup_grace_minutes=25)

    def test_accepted_dispatch_waits_bounded_startup_grace(self):
        result = recovery.decide(
            snapshot(
                latest_prepared_at=NOW - timedelta(minutes=10),
                latest_dispatched_at=NOW - timedelta(minutes=10),
            ),
            NOW,
            self.policy,
        )
        self.assertEqual(result.state, "active")
        self.assertEqual(result.reason, "startup_grace_active")
        self.assertFalse(result.dispatch)

    def test_accepted_dispatch_without_start_redispatches_same_batch_after_grace(self):
        result = recovery.decide(snapshot(), NOW, self.policy)
        self.assertTrue(result.dispatch)
        self.assertTrue(result.reuse_batch)
        self.assertEqual(result.reason, "startup_timeout_without_started_evidence")

    def test_current_start_uses_existing_long_running_grace(self):
        result = recovery.decide(
            snapshot(
                latest_started_at=NOW - timedelta(minutes=40),
                latest_started_dispatch_id=DISPATCH,
                current_dispatch_started_at=NOW - timedelta(minutes=40),
            ),
            NOW,
            self.policy,
        )
        self.assertEqual(result.state, "active")
        self.assertEqual(result.reason, "started_production_within_long_grace")
        self.assertFalse(result.dispatch)

    def test_recent_delayed_original_start_suppresses_further_fast_redispatch(self):
        result = recovery.decide(
            snapshot(
                latest_started_at=NOW - timedelta(minutes=5),
                latest_started_dispatch_id="d_" + "e" * 24,
                current_dispatch_started_at=None,
            ),
            NOW,
            self.policy,
        )
        self.assertEqual(result.state, "active")
        self.assertEqual(result.reason, "started_production_within_long_grace")

    def test_stale_start_from_old_attempt_does_not_satisfy_current_dispatch(self):
        stale = self.policy.active_grace_minutes + 1
        result = recovery.decide(
            snapshot(
                latest_started_at=NOW - timedelta(minutes=stale),
                latest_started_dispatch_id="d_" + "e" * 24,
                current_dispatch_started_at=None,
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)
        self.assertTrue(result.reuse_batch)
        self.assertEqual(result.reason, "startup_timeout_without_started_evidence")

    def test_current_started_but_stale_uses_normal_recovery_not_fast_no_start(self):
        stale = self.policy.active_grace_minutes + 1
        result = recovery.decide(
            snapshot(
                latest_started_at=NOW - timedelta(minutes=stale),
                latest_started_dispatch_id=DISPATCH,
                current_dispatch_started_at=NOW - timedelta(minutes=stale),
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)
        self.assertFalse(result.reuse_batch)
        self.assertEqual(result.reason, "stale_unresolved_request")

    def test_upload_evidence_outranks_no_start_redispatch(self):
        stale = self.policy.active_grace_minutes + 1
        result = recovery.decide(
            snapshot(
                has_intent=True,
                latest_prepared_at=NOW - timedelta(minutes=stale),
                latest_dispatched_at=NOW - timedelta(minutes=stale),
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)
        self.assertFalse(result.reuse_batch)
        self.assertEqual(result.reason, "durable_upload_state_needs_reconciliation")

    def test_completion_already_present_never_uses_no_start_path(self):
        result = recovery.decide(snapshot(receipt_state="valid"), NOW, self.policy)
        self.assertEqual(result.state, "completed")
        self.assertFalse(result.dispatch)

    def test_retry_exhaustion_stops_no_start_loop(self):
        result = recovery.decide(snapshot(automatic_attempts=3), NOW, self.policy)
        self.assertTrue(result.terminal)
        self.assertFalse(result.dispatch)
        self.assertEqual(result.reason, "maximum_automatic_attempts_reached")

    def test_explicit_dispatch_failure_can_retry_same_immutable_batch_immediately(self):
        result = recovery.decide(
            snapshot(
                latest_prepared_at=NOW - timedelta(minutes=1),
                latest_dispatched_at=None,
                latest_dispatch_failed_at=NOW - timedelta(minutes=1),
            ),
            NOW,
            self.policy,
        )
        self.assertTrue(result.dispatch)
        self.assertTrue(result.reuse_batch)
        self.assertEqual(result.reason, "private_dispatch_failed")

    def test_prepared_but_unacknowledged_dispatch_remains_conservative(self):
        result = recovery.decide(
            snapshot(
                latest_prepared_at=NOW - timedelta(minutes=30),
                latest_dispatched_at=None,
                latest_dispatch_failed_at=None,
            ),
            NOW,
            self.policy,
        )
        self.assertEqual(result.state, "active")
        self.assertEqual(result.reason, "dispatch_outcome_uncertain_within_long_grace")


if __name__ == "__main__":
    unittest.main()
