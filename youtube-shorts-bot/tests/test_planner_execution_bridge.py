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

    def test_bridge_exposes_new_editorial_ownership_stages(self):
        required = {
            "planning.raw-filter",
            "planning.candidate-evaluation",
            "planning.validate-selection",
            "background.select",
            "background.audit",
            "background.treatment",
            "request.validate",
        }
        self.assertTrue(required.issubset(OPERATIONS))
        self.assertIn("planning.final-select", OPERATIONS)  # legacy recovery only

    def test_candidate_evaluation_does_not_return_authoritative_winner(self):
        raw, semifinalists = build_acceptance_fixture("2026-09-12")
        envelope = execute_envelope({
            "schema_version": 1,
            "execution_id": "pe-test-eval-20260912",
            "operation": "planning.candidate-evaluation",
            "payload": {
                "raw_candidates": raw,
                "semifinalists": semifinalists,
                "plan_date": "2026-09-12",
                "recent": [],
                "analytics_evidence_count": 0,
            },
        })
        result = envelope["result"]["result"]
        self.assertIn("evaluated_candidates", result)
        self.assertNotIn("selected", result)

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
