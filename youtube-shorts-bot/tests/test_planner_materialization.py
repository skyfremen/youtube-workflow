import json
import unittest
from pathlib import Path


BOT_ROOT = Path(__file__).resolve().parents[1]
PLANNING = BOT_ROOT / "planning"
MANIFEST = PLANNING / "PLANNER_MATERIALIZATION.json"


class PlannerMaterializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_materialization_contract_requires_no_git(self):
        self.assertEqual(self.data["contract"], "gitless_planner_materialization")
        for key in (
            "git_required",
            "git_executable_required",
            "checkout_required",
            "git_metadata_required",
        ):
            self.assertFalse(self.data[key])
        self.assertEqual(
            self.data["repository_identity"]["field"], "rules_source_sha"
        )
        self.assertIn("GitHub API/connector", self.data["repository_identity"]["source"])

    def test_declared_source_and_data_paths_exist(self):
        repo_root = BOT_ROOT.parent
        for relative in self.data["source_roots"]:
            path = repo_root / relative
            self.assertTrue(path.is_dir(), relative)
            self.assertTrue(any(path.rglob("*.py")), relative)
        for relative in self.data["required_data_files"]:
            self.assertTrue((repo_root / relative).is_file(), relative)

    def test_entrypoints_do_not_use_git_commands(self):
        for command in self.data["entrypoints"]:
            lower = command.lower()
            self.assertNotIn("git ", lower)
            self.assertNotIn(".git", lower)
            self.assertNotIn("rev-parse", lower)

    def test_prompts_bind_to_materialization_contract(self):
        for name in ("ADHOC_PLANNER_PROMPT.md", "DAILY_PLANNER_PROMPT.md"):
            prompt = (PLANNING / name).read_text(encoding="utf-8")
            self.assertIn("PLANNER_MATERIALIZATION.json", prompt)
            self.assertIn("plain temporary directory", prompt)
            self.assertIn("must not need `.git` or a Git executable", prompt)


if __name__ == "__main__":
    unittest.main()
