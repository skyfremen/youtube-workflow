import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
PLANNER = REPO_ROOT / "youtube-shorts-bot" / "planning"


class WorkflowTopologyTests(unittest.TestCase):
    def test_adhoc_uses_ranked_pool_single_private_entrypoint(self):
        adhoc = (WORKFLOWS / "adhoc-production.yml").read_text(encoding="utf-8")
        self.assertFalse((WORKFLOWS / "adhoc-request-dispatch.yml").exists())
        self.assertFalse((WORKFLOWS / "planner-execution.yml").exists())
        self.assertFalse((PLANNER / "execution_bridge.py").exists())
        self.assertIn("name: Ad-hoc Production", adhoc)
        self.assertIn("push:", adhoc)
        self.assertIn("workflow_dispatch:", adhoc)
        self.assertIn("content/candidate-pools/adhoc/*.json", adhoc)
        self.assertIn("Validate 5 ranked candidates and promote first valid one", adhoc)
        self.assertIn("[adhoc production]", adhoc)
        self.assertIn("actions/workflows/single.yml/dispatches", adhoc)

    def test_daily_uses_ranked_pool_single_private_entrypoint(self):
        daily = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        self.assertIn("content/candidate-pools/daily/*.json", daily)
        self.assertIn("Validate 36 ranked candidates and promote first valid 24", daily)
        self.assertIn("planning.candidate_pool promote-daily", daily)
        self.assertIn("validation.planning_audit", daily)
        self.assertIn("actions/workflows/run.yml/dispatches", daily)

    def test_prompts_match_ranked_pool_contract(self):
        daily = (PLANNER / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        adhoc = (PLANNER / "ADHOC_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("exactly 36 complete ranked candidates", daily)
        self.assertIn("first 24 valid candidates", daily)
        self.assertIn("exactly **5 complete ranked Ad-hoc candidates**", adhoc)
        self.assertIn("first valid candidate", adhoc)
        for prompt in (daily, adhoc):
            self.assertIn("There is no `planner-execution.yml`", prompt)

    def test_daily_and_adhoc_each_have_one_private_production_entrypoint(self):
        self.assertTrue((WORKFLOWS / "daily-production.yml").is_file())
        self.assertTrue((WORKFLOWS / "adhoc-production.yml").is_file())
        self.assertFalse((WORKFLOWS / "adhoc-request-dispatch.yml").exists())
        self.assertFalse((WORKFLOWS / "planner-execution.yml").exists())


if __name__ == "__main__":
    unittest.main()
