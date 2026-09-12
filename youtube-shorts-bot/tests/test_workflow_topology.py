import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


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

    def test_daily_and_adhoc_each_have_one_private_production_entrypoint(self):
        self.assertTrue((WORKFLOWS / "daily-production.yml").is_file())
        self.assertTrue((WORKFLOWS / "adhoc-production.yml").is_file())
        self.assertFalse((WORKFLOWS / "adhoc-request-dispatch.yml").exists())


if __name__ == "__main__":
    unittest.main()
