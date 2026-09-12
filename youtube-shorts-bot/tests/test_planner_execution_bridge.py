import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
sys.path.insert(0, str(BASE))

from planning.execution_bridge import OPERATIONS, execute_envelope


class PlannerExecutionBridgeTests(unittest.TestCase):
    def test_bridge_is_mechanical_only(self):
        self.assertEqual(
            OPERATIONS,
            {
                "background.select",
                "background.audit",
                "background.treatment",
                "request.validate",
            },
        )
        self.assertFalse(any(operation.startswith("planning.") for operation in OPERATIONS))

    def test_planning_operation_fails_closed(self):
        with self.assertRaises(ValueError):
            execute_envelope({
                "schema_version": 1,
                "execution_id": "pe-test-plan-20260912",
                "operation": "planning.raw-filter",
                "payload": {},
            })

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

    def test_prompts_forbid_bridge_for_candidate_planning(self):
        daily = (BASE / "planning" / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        adhoc = (BASE / "planning" / "ADHOC_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("ChatGPT must itself perform candidate filtering", daily)
        self.assertIn("GitHub Actions must not execute", daily)
        self.assertIn("Do not call GitHub Actions", adhoc)
        self.assertIn("mechanical non-editorial operations only", adhoc)


if __name__ == "__main__":
    unittest.main()
