import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from recovery import controller as recovery


BATCH = "b_" + "a" * 30
DISPATCH = "d_" + "b" * 24
SOURCE = "c" * 40
CONTRACT = "d" * 64
RUNTIME = "e" * 40


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


class ProgressRecoveryCompatibilityTests(unittest.TestCase):
    def test_newest_start_compatible_progress_refreshes_recovery_liveness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "youtube-shorts-bot"
            intent = {
                "schema_version": 1,
                "state": "prepared",
                "batch_id": BATCH,
                "dispatch_id": DISPATCH,
                "source_sha": SOURCE,
                "contract_hash": CONTRACT,
                "dispatch_kind": "production",
                "prepared_at": "2026-09-12T00:00:00Z",
            }
            accepted = {
                **intent,
                "state": "dispatched",
                "dispatched_at": "2026-09-12T00:01:00Z",
            }
            original_start = {
                "schema_version": 1,
                "state": "started",
                "batch_id": BATCH,
                "dispatch_id": DISPATCH,
                "source_sha": SOURCE,
                "contract_hash": CONTRACT,
                "runtime_commit_sha": RUNTIME,
                "workflow_run_id": "123",
                "workflow_run_attempt": "1",
                "started_at": "2026-09-12T00:02:00Z",
            }
            progress = {
                **original_start,
                "started_at": "2026-09-12T02:30:00Z",
                "progress_stage": "unit_produced",
                "shard_index": 0,
            }
            base = root / "content" / "recovery"
            write_json(base / "dispatch-intents" / BATCH / f"{DISPATCH}.json", intent)
            write_json(base / "dispatches" / BATCH / f"{DISPATCH}.json", accepted)
            write_json(base / "starts" / BATCH / DISPATCH / "123-1.json", original_start)
            write_json(
                base / "starts" / BATCH / DISPATCH / "123-1-unit_produced-00.json",
                progress,
            )

            state = recovery.Repository(root=root).dispatch_state(BATCH)

        expected = datetime(2026, 9, 12, 2, 30, tzinfo=timezone.utc)
        self.assertEqual(state["latest_start"]["at"], expected)
        self.assertEqual(state["current_start"]["at"], expected)
        self.assertEqual(state["latest_start"]["dispatch_id"], DISPATCH)

    def test_progress_for_unknown_dispatch_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "youtube-shorts-bot"
            other_dispatch = "d_" + "f" * 24
            base = root / "content" / "recovery"
            write_json(
                base / "starts" / BATCH / other_dispatch / "123-1-unit_started-00.json",
                {
                    "schema_version": 1,
                    "state": "started",
                    "batch_id": BATCH,
                    "dispatch_id": other_dispatch,
                    "source_sha": SOURCE,
                    "contract_hash": CONTRACT,
                    "runtime_commit_sha": RUNTIME,
                    "workflow_run_id": "123",
                    "workflow_run_attempt": "1",
                    "started_at": "2026-09-12T02:30:00Z",
                    "progress_stage": "unit_started",
                    "shard_index": 0,
                },
            )
            state = recovery.Repository(root=root).dispatch_state(BATCH)

        self.assertIsNone(state["latest_start"])
        self.assertIsNone(state["current_start"])


if __name__ == "__main__":
    unittest.main()
