import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
PLANNER = BOT_ROOT / "planning"
DOCS = BOT_ROOT / "docs"


def canonical_planner_text(prefix):
    return (
        (PLANNER / f"{prefix}_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        + "\n"
        + (PLANNER / f"{prefix}_PLANNER_RULES.md").read_text(encoding="utf-8")
    )


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
        planner = canonical_planner_text("DAILY")

        self.assertIn("content/planning-pools/daily/**/*.json", daily)
        self.assertIn("[daily pool]", daily)
        self.assertIn("planning.pool_admission daily", daily)
        self.assertIn("planning.ranked_promotion daily", daily)
        self.assertIn("[daily production] ${plan_date}", daily)
        self.assertIn("validation.planning_audit", daily)
        self.assertIn("actions/workflows/run.yml/dispatches", daily)
        self.assertIn("exactly 36", planner)
        self.assertIn("first `target_count` candidates", planner)
        self.assertIn("content/planning-pools/daily/YYYY-MM-DD/dp-<attempt-id>.json", planner)
        self.assertIn("new immutable attempt", planner)

    def test_adhoc_uses_ranked_pool_entrypoint_and_scheduled_idempotency(self):
        adhoc = (WORKFLOWS / "adhoc-production.yml").read_text(encoding="utf-8")
        planner = canonical_planner_text("ADHOC")

        self.assertIn("content/planning-pools/adhoc/*.json", adhoc)
        self.assertIn("[adhoc pool]", adhoc)
        self.assertIn("planning.pool_admission adhoc", adhoc)
        self.assertIn("planning.ranked_promotion adhoc", adhoc)
        self.assertIn("planning.ranked_promotion verify-adhoc", adhoc)
        self.assertIn("validation.validate_content --request", adhoc)
        self.assertIn("actions/workflows/single.yml/dispatches", adhoc)
        self.assertIn("exactly **5** candidates", planner)
        self.assertIn("first valid candidate", planner)
        self.assertIn("scheduled_daily", planner)
        self.assertIn("manual_on_demand", planner)

    def test_daily_and_adhoc_each_keep_manual_execution_path(self):
        daily = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        adhoc = (WORKFLOWS / "adhoc-production.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", daily)
        self.assertIn("content_ids:", daily)
        self.assertIn("workflow_dispatch:", adhoc)
        self.assertIn("content_id:", adhoc)


if __name__ == "__main__":
    unittest.main()
