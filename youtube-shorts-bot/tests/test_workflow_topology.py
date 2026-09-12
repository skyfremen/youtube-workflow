import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
PLANNER = BOT_ROOT / "planning"
DOCS = BOT_ROOT / "docs"


class WorkflowTopologyTests(unittest.TestCase):
    def test_planner_execution_bridge_is_retired(self):
        self.assertFalse((WORKFLOWS / "planner-execution.yml").exists())
        self.assertFalse((PLANNER / "execution_bridge.py").exists())
        self.assertFalse((WORKFLOWS / "adhoc-request-dispatch.yml").exists())

    def test_v4_planner_base_docs_are_retired(self):
        self.assertFalse((DOCS / "DAILY_PLANNER_V4_BASE.md").exists())
        self.assertFalse((DOCS / "ADHOC_PLANNER_V4_BASE.md").exists())

    def test_daily_uses_retryable_ranked_pool_entrypoint(self):
        daily = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        prompt = (PLANNER / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")

        self.assertIn("content/planning-pools/daily/**/*.json", daily)
        self.assertIn("[daily pool]", daily)
        self.assertIn("planning.ranked_promotion daily", daily)
        self.assertIn("[daily production] ${plan_date}", daily)
        self.assertIn("validation.planning_audit", daily)
        self.assertIn("actions/workflows/run.yml/dispatches", daily)
        self.assertIn("exactly 36", prompt)
        self.assertIn("first 24 valid", prompt)
        self.assertIn("content/planning-pools/daily/YYYY-MM-DD/dp-<attempt-id>.json", prompt)
        self.assertIn("new immutable attempt", prompt)

    def test_adhoc_uses_ranked_pool_entrypoint_and_scheduled_idempotency(self):
        adhoc = (WORKFLOWS / "adhoc-production.yml").read_text(encoding="utf-8")
        prompt = (PLANNER / "ADHOC_PLANNER_PROMPT.md").read_text(encoding="utf-8")

        self.assertIn("content/planning-pools/adhoc/*.json", adhoc)
        self.assertIn("[adhoc pool]", adhoc)
        self.assertIn("planning.ranked_promotion adhoc", adhoc)
        self.assertIn("planning.ranked_promotion verify-adhoc", adhoc)
        self.assertIn("validation.validate_content --request", adhoc)
        self.assertIn("actions/workflows/single.yml/dispatches", adhoc)
        self.assertIn("exactly **5** candidates", prompt)
        self.assertIn("first valid candidate", prompt)
        self.assertIn("scheduled_daily", prompt)
        self.assertIn("manual_on_demand", prompt)

    def test_daily_and_adhoc_each_keep_manual_execution_path(self):
        daily = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        adhoc = (WORKFLOWS / "adhoc-production.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", daily)
        self.assertIn("content_ids:", daily)
        self.assertIn("workflow_dispatch:", adhoc)
        self.assertIn("content_id:", adhoc)


if __name__ == "__main__":
    unittest.main()
