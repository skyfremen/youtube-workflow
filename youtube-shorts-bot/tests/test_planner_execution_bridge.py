import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
sys.path.insert(0, str(BASE))

from media.background_selector import (
    DEFAULT_BACKGROUND_BACKUP_ID,
    DEFAULT_BACKGROUND_PRIMARY_ID,
    audit_ai_selection,
)
from media.validate_media_library import load_registry
from planning.execution_bridge import OPERATIONS, execute_envelope


class PlannerExecutionBridgeTests(unittest.TestCase):
    def test_bridge_is_mechanical_only(self):
        self.assertEqual(
            OPERATIONS,
            {
                "background.audit",
                "background.treatment",
                "request.validate",
            },
        )
        self.assertFalse(any(operation.startswith("planning.") for operation in OPERATIONS))
        self.assertNotIn("background.select", OPERATIONS)

    def test_planning_operation_fails_closed(self):
        with self.assertRaises(ValueError):
            execute_envelope({
                "schema_version": 1,
                "execution_id": "pe-test-plan-20260912",
                "operation": "planning.raw-filter",
                "payload": {},
            })

    def test_background_selection_operation_fails_closed(self):
        with self.assertRaises(ValueError):
            execute_envelope({
                "schema_version": 1,
                "execution_id": "pe-test-bg-select-20260912",
                "operation": "background.select",
                "payload": {},
            })

    def test_background_audit_uses_fixed_default_pair_on_rejection(self):
        registry = load_registry()
        result = audit_ai_selection(
            registry,
            "missing-primary",
            "missing-backup",
            [],
            {},
        )
        self.assertTrue(result["passed"])
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["resolved_primary_id"], DEFAULT_BACKGROUND_PRIMARY_ID)
        self.assertEqual(result["resolved_backup_id"], DEFAULT_BACKGROUND_BACKUP_ID)
        self.assertTrue(result["selection_errors"])
        self.assertEqual(result["errors"], result["selection_errors"])
        self.assertEqual(result["fallback_errors"], [])
        self.assertTrue(result["primary"]["fallback_default"])
        self.assertTrue(result["backup"]["fallback_default"])

    def test_background_defaults_are_distinct(self):
        self.assertNotEqual(DEFAULT_BACKGROUND_PRIMARY_ID, DEFAULT_BACKGROUND_BACKUP_ID)

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

    def test_prompts_make_chatgpt_background_owner(self):
        daily = (BASE / "planning" / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        adhoc = (BASE / "planning" / "ADHOC_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("ChatGPT must itself perform candidate filtering", daily)
        self.assertIn("exact primary/backup logical background selection", daily)
        self.assertIn("GitHub Actions must not execute", daily)
        self.assertIn("background.select", daily)
        self.assertIn("configured default background pair", daily)
        self.assertIn("chooses the requested primary and backup logical asset IDs itself", adhoc)
        self.assertIn("background.audit", adhoc)
        self.assertIn("configured default background pair", adhoc)
        self.assertNotIn("- `background.select`", adhoc)


if __name__ == "__main__":
    unittest.main()
