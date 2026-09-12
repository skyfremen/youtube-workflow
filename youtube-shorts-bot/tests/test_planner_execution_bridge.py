import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
sys.path.insert(0, str(BASE))

from planning.execution_bridge import OPERATIONS, execute_envelope
from planning.planning_engine import build_acceptance_fixture


class PlannerExecutionBridgeTests(unittest.TestCase):
    def test_raw_filter_executes_canonical_runner_with_source_provenance(self):
        raw, _ = build_acceptance_fixture("2026-09-12")
        envelope = execute_envelope({
            "schema_version": 1,
            "execution_id": "pe-test-raw-20260912",
            "operation": "planning.raw-filter",
            "payload": {"raw_candidates": raw, "recent": []},
        })
        self.assertEqual(envelope["operation"], "planning.raw-filter")
        self.assertRegex(envelope["source_sha"], r"^[0-9a-f]{40}$")
        self.assertGreaterEqual(envelope["result"]["result"]["qualified"], 1)
        self.assertEqual(
            envelope["result"]["execution"]["source_sha"],
            envelope["source_sha"],
        )

    def test_bridge_covers_all_adhoc_repository_side_deterministic_steps(self):
        required = {
            "planning.raw-filter",
            "planning.final-select",
            "background.select",
            "background.audit",
            "background.treatment",
            "request.validate",
        }
        self.assertTrue(required.issubset(OPERATIONS))

    def test_unknown_operation_fails_closed(self):
        with self.assertRaises(ValueError):
            execute_envelope({
                "schema_version": 1,
                "execution_id": "pe-test-invalid-20260912",
                "operation": "render.video",
                "payload": {},
            })

    def test_workflow_bridge_preserves_private_production_boundary(self):
        planner = (ROOT / ".github/workflows/planner-execution.yml").read_text(encoding="utf-8")
        auto = (ROOT / ".github/workflows/adhoc-request-dispatch.yml").read_text(encoding="utf-8")
        adhoc = (ROOT / ".github/workflows/adhoc-production.yml").read_text(encoding="utf-8")

        self.assertIn("planning/execution_bridge.py", planner)
        self.assertNotIn("production-runtime", planner)
        self.assertIn("adhoc-production.yml/dispatches", auto)
        self.assertNotIn("production-runtime", auto)
        self.assertIn("production-runtime/actions/workflows/single.yml/dispatches", adhoc)
        self.assertIn("publication", auto)
        self.assertIn("publish_at", auto)


if __name__ == "__main__":
    unittest.main()
