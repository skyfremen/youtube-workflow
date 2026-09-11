import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from recovery import evidence


NOW = datetime(2026, 9, 12, 0, 0, tzinfo=timezone.utc)
BATCH = "b_" + "a" * 30
SOURCE = "b" * 40
CONTRACT = "c" * 64


class DispatchEvidenceTests(unittest.TestCase):
    def test_dispatch_identity_is_deterministic_and_attempt_scoped(self):
        first = evidence.make_dispatch_id(BATCH, SOURCE, CONTRACT, "101", "1", "initial")
        same = evidence.make_dispatch_id(BATCH, SOURCE, CONTRACT, "101", "1", "initial")
        retry = evidence.make_dispatch_id(BATCH, SOURCE, CONTRACT, "102", "1", "no-start-retry")
        self.assertEqual(first, same)
        self.assertNotEqual(first, retry)
        self.assertRegex(first, r"^d_[0-9a-f]{24}$")

    def test_prepared_and_accepted_are_separate_append_only_evidence(self):
        dispatch_id = evidence.make_dispatch_id(BATCH, SOURCE, CONTRACT, "101", "1", "initial")
        with tempfile.TemporaryDirectory() as directory, patch.object(
            evidence, "RECOVERY", Path(directory)
        ):
            prepared = evidence.write_evidence(
                "prepared",
                batch_id=BATCH,
                source_sha=SOURCE,
                contract_hash=CONTRACT,
                dispatch_id=dispatch_id,
                dispatch_kind="initial",
                private_run_id="101",
                private_run_attempt="1",
                now=NOW,
            )
            self.assertTrue(prepared.is_file())
            self.assertFalse(
                (Path(directory) / "dispatches" / BATCH / f"{dispatch_id}.json").exists()
            )
            accepted = evidence.write_evidence(
                "dispatched",
                batch_id=BATCH,
                source_sha=SOURCE,
                contract_hash=CONTRACT,
                dispatch_id=dispatch_id,
                dispatch_kind="initial",
                private_run_id="101",
                private_run_attempt="1",
                now=NOW,
            )
            self.assertTrue(accepted.is_file())
            self.assertEqual(json.loads(prepared.read_text())["state"], "prepared")
            self.assertEqual(json.loads(accepted.read_text())["state"], "dispatched")

    def test_existing_evidence_cannot_be_rewritten_with_different_identity(self):
        dispatch_id = evidence.make_dispatch_id(BATCH, SOURCE, CONTRACT, "101", "1", "initial")
        with tempfile.TemporaryDirectory() as directory, patch.object(
            evidence, "RECOVERY", Path(directory)
        ):
            evidence.write_evidence(
                "prepared",
                batch_id=BATCH,
                source_sha=SOURCE,
                contract_hash=CONTRACT,
                dispatch_id=dispatch_id,
                dispatch_kind="initial",
                private_run_id="101",
                private_run_attempt="1",
                now=NOW,
            )
            with self.assertRaises(ValueError):
                evidence.write_evidence(
                    "prepared",
                    batch_id=BATCH,
                    source_sha=SOURCE,
                    contract_hash="d" * 64,
                    dispatch_id=dispatch_id,
                    dispatch_kind="initial",
                    private_run_id="101",
                    private_run_attempt="1",
                    now=NOW,
                )


if __name__ == "__main__":
    unittest.main()
