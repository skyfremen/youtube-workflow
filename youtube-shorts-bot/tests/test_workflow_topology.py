import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
PLANNER = REPO_ROOT / "youtube-shorts-bot" / "planning"


class WorkflowTopologyTests(unittest.TestCase):
    def test_adhoc_uses_single_private_entrypoint(self):
        adhoc = (WORKFLOWS / "adhoc-production.yml").read_text(encoding="utf-8")

        self.assertFalse((WORKFLOWS / "adhoc-request-dispatch.yml").exists())
        self.assertIn("name: Ad-hoc Production", adhoc)
        self.assertIn("push:", adhoc)
        self.assertIn("workflow_dispatch:", adhoc)
        self.assertIn("content/requests/wd-*-adhoc-*.json", adhoc)
        self.assertIn("[adhoc production]", adhoc)
        self.assertIn("Resolve exactly one ad-hoc request", adhoc)
        self.assertIn("actions/workflows/single.yml/dispatches", adhoc)

    def test_adhoc_prompt_matches_single_private_entrypoint(self):
        prompt = (PLANNER / "ADHOC_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn(".github/workflows/adhoc-production.yml", prompt)
        self.assertIn("public `single.yml`", prompt)
        self.assertIn("There is no separate `adhoc-request-dispatch.yml` routing workflow", prompt)
        self.assertNotIn(
            "adhoc-request-dispatch.yml` may automatically dispatch",
            prompt,
        )

    def test_daily_and_adhoc_each_have_one_private_production_entrypoint(self):
        self.assertTrue((WORKFLOWS / "daily-production.yml").is_file())
        self.assertTrue((WORKFLOWS / "adhoc-production.yml").is_file())
        self.assertFalse((WORKFLOWS / "adhoc-request-dispatch.yml").exists())


if __name__ == "__main__":
    unittest.main()
