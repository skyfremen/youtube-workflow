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

    def test_git_is_preferred_but_connector_fallback_keeps_git_optional(self):
        self.assertEqual(self.data["schema_version"], 6)
        self.assertEqual(
            self.data["materialization_mode"],
            "shared_plus_selected_profile",
        )
        bootstrap = self.data["planner_bootstrap"]
        self.assertEqual(bootstrap["preferred"], "git")
        self.assertEqual(bootstrap["fallback"], "connector_materialization")
        self.assertFalse(bootstrap["github_actions_planning"])
        self.assertTrue(bootstrap["exact_sha_required"])
        self.assertTrue(bootstrap["reuse_existing_clone_when_available"])
        self.assertFalse(bootstrap["persistence_is_correctness_dependency"])

        git_checkout = self.data["git_checkout"]
        self.assertTrue(git_checkout["allowed"])
        self.assertTrue(git_checkout["preferred"])
        self.assertIn("git fetch origin main --prune", git_checkout["fetch_command"])
        self.assertIn("git rev-parse origin/main", git_checkout["resolve_sha_command"])
        self.assertIn("--detach", git_checkout["worktree_command"])

        # Git is preferred, but connector fallback means it is not a correctness dependency.
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
        self.assertIn("Git", self.data["repository_identity"]["source"])
        self.assertIn("connector", self.data["repository_identity"]["source"])
        self.assertEqual(
            self.data["immutable_cache"]["primary_key"], "rules_source_sha"
        )
        self.assertFalse(
            self.data["immutable_cache"]["correctness_dependency"]
        )

    def test_declared_connector_fallback_paths_exist(self):
        required = list(self.data["shared_required_python_files"])
        required += list(self.data["shared_required_data_files"])
        for profile in ("daily", "adhoc"):
            entry = self.data["profile_required_files"][profile]
            required.extend(entry["python_files"])
            required.extend(entry["data_files"])
        for relative in required:
            self.assertTrue((REPO_ROOT / relative).is_file(), relative)

    def test_local_validation_entrypoints_remain_shared(self):
        entrypoints = self.data["entrypoints"]
        for name in ("contract", "media_readiness", "precommit"):
            lower = entrypoints[name].lower()
            self.assertNotIn("github actions", lower)
        self.assertIn("planning.planner_precommit", entrypoints["precommit"])
        self.assertIn("--verify-git-head", entrypoints["git_precommit"])
        self.assertIn("planning.planner_drift", entrypoints["git_drift"])

    def test_profiles_share_the_same_connector_fallback_core(self):
        shared = set(self.data["shared_required_python_files"])
        self.assertEqual(len(shared), 14)
        self.assertIn(
            "youtube-shorts-bot/planning/planner_precommit.py", shared
        )
        self.assertIn("youtube-shorts-bot/planning/planner_core.py", shared)
        self.assertIn(
            "youtube-shorts-bot/planning/planner_profiles.py", shared
        )
        self.assertNotIn(
            "youtube-shorts-bot/planning/ranked_promotion.py", shared
        )
        self.assertNotIn("youtube-shorts-bot/publishing/upload.py", shared)
        self.assertEqual(
            self.data["profile_required_files"]["daily"]["python_files"], []
        )
        self.assertEqual(
            self.data["profile_required_files"]["adhoc"]["python_files"], []
        )

    def test_forbidden_requirements_keep_actions_and_synthetic_identity_out(self):
        forbidden = self.data["forbidden_bootstrap_requirements"]
        self.assertIn("GitHub Actions planner execution", forbidden)
        self.assertIn("synthetic HEAD", forbidden)
        self.assertIn("fake repository identity", forbidden)
        self.assertNotIn("git clone", forbidden)
        self.assertNotIn("git rev-parse", forbidden)
        self.assertNotIn(".git", forbidden)

    def test_prompts_bind_to_git_first_shared_contract(self):
        shared = SHARED_PROMPT.read_text(encoding="utf-8")
        self.assertIn("Git is now the **preferred source-acquisition path**", shared)
        self.assertIn("git fetch origin main --prune", shared)
        self.assertIn("git worktree add --detach", shared)
        self.assertIn("Connector/API fallback", shared)
        self.assertIn("planning.planner_drift", shared)
        self.assertIn("GitHub Actions planner execution remains prohibited", shared)
        for name in ("ADHOC_PLANNER_PROMPT.md", "DAILY_PLANNER_PROMPT.md"):
            prompt = (PLANNING / name).read_text(encoding="utf-8")
            self.assertIn("docs/private/PLANNER_PROMPT.md", prompt)
            self.assertIn("Git-first exact detached snapshot", prompt)
            self.assertIn("connector/API fallback", prompt)
            self.assertIn("--verify-git-head", prompt)


if __name__ == "__main__":
    unittest.main()
