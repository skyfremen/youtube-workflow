import json
import unittest
from pathlib import Path


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent
PLANNING = BOT_ROOT / "planning"
MANIFEST = PLANNING / "PLANNER_MATERIALIZATION.json"
SHARED_PROMPT = REPO_ROOT / "docs" / "private" / "PLANNER_PROMPT.md"


class PlannerMaterializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_materialization_contract_requires_no_git(self):
        self.assertEqual(
            self.data["materialization_mode"],
            "shared_plus_selected_profile",
        )
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
        self.assertEqual(self.data["immutable_cache"]["primary_key"], "rules_source_sha")
        self.assertFalse(self.data["immutable_cache"]["correctness_dependency"])

    def test_declared_source_and_data_paths_exist(self):
        required = (
            self.data["shared_required_python_files"]
            + self.data["shared_required_data_files"]
        )
        for profile in ("daily", "adhoc"):
            entry = self.data["profile_required_files"][profile]
            required.extend(entry["python_files"])
            required.extend(entry["data_files"])
        for relative in required:
            self.assertTrue((REPO_ROOT / relative).is_file(), relative)

    def test_entrypoints_do_not_use_git_commands(self):
        for command in self.data["entrypoints"].values():
            lower = command.lower()
            self.assertNotIn("git ", lower)
            self.assertNotIn(".git", lower)
            self.assertNotIn("rev-parse", lower)

    def test_profiles_share_the_same_materialized_core(self):
        shared = set(self.data["shared_required_python_files"])
        self.assertIn("youtube-shorts-bot/planning/planner_precommit.py", shared)
        self.assertIn("youtube-shorts-bot/planning/planner_core.py", shared)
        self.assertIn("youtube-shorts-bot/planning/planner_profiles.py", shared)
        self.assertNotIn("youtube-shorts-bot/planning/ranked_promotion.py", shared)
        self.assertNotIn("youtube-shorts-bot/publishing/upload.py", shared)
        self.assertEqual(
            self.data["profile_required_files"]["daily"]["python_files"], []
        )
        self.assertEqual(
            self.data["profile_required_files"]["adhoc"]["python_files"], []
        )

    def test_prompts_bind_to_materialization_contract(self):
        shared = SHARED_PROMPT.read_text(encoding="utf-8")
        self.assertIn("PLANNER_MATERIALIZATION.json", shared)
        self.assertIn("ordinary temporary directory", shared)
        self.assertIn("A Git checkout, Git executable, `.git` directory", shared)
        for name in ("ADHOC_PLANNER_PROMPT.md", "DAILY_PLANNER_PROMPT.md"):
            prompt = (PLANNING / name).read_text(encoding="utf-8")
            self.assertIn("docs/private/PLANNER_PROMPT.md", prompt)
            self.assertIn("PLANNER_MATERIALIZATION.json", prompt)
            self.assertIn("plain temporary directory", prompt)
            self.assertIn("must not need `.git` or a Git executable", prompt)


if __name__ == "__main__":
    unittest.main()
