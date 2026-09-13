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

    def test_connector_is_canonical_and_shell_git_is_not_chatgpt_bootstrap(self):
        self.assertEqual(self.data["schema_version"], 7)
        self.assertEqual(
            self.data["contract"],
            "connector_first_shared_planner_materialization",
        )
        self.assertEqual(self.data["materialization_mode"], "shared_plus_selected_profile")
        bootstrap = self.data["planner_bootstrap"]
        self.assertEqual(bootstrap["preferred"], "connector_materialization")
        self.assertEqual(bootstrap["fallback"], "none")
        self.assertEqual(
            bootstrap["chatgpt_work_source"], "authorized_github_connector_api"
        )
        self.assertFalse(bootstrap["github_actions_planning"])
        self.assertTrue(bootstrap["exact_sha_required"])
        self.assertFalse(bootstrap["shell_git_attempted_in_chatgpt_work"])
        self.assertFalse(bootstrap["persistence_is_correctness_dependency"])

        git_checkout = self.data["git_checkout"]
        self.assertTrue(git_checkout["allowed"])
        self.assertFalse(git_checkout["preferred"])
        self.assertFalse(git_checkout["chatgpt_work_allowed"])
        self.assertIn("developer", git_checkout["scope"])
        self.assertIn("git fetch origin main --prune", git_checkout["fetch_command"])
        self.assertIn("git rev-parse origin/main", git_checkout["resolve_sha_command"])
        self.assertIn("--detach", git_checkout["worktree_command"])

        for key in (
            "git_required",
            "git_executable_required",
            "checkout_required",
            "git_metadata_required",
        ):
            self.assertFalse(self.data[key])
        self.assertEqual(self.data["repository_identity"]["field"], "rules_source_sha")
        self.assertIn("connector/API", self.data["repository_identity"]["source"])
        self.assertFalse(self.data["immutable_cache"]["correctness_dependency"])

    def test_declared_connector_paths_exist(self):
        required = list(self.data["shared_required_python_files"])
        required += list(self.data["shared_required_data_files"])
        for profile in ("daily", "adhoc"):
            entry = self.data["profile_required_files"][profile]
            required.extend(entry["python_files"])
            required.extend(entry["data_files"])
        for relative in required:
            self.assertTrue((REPO_ROOT / relative).is_file(), relative)

    def test_connector_completion_gate_is_machine_verified(self):
        connector = self.data["connector_materialization"]
        self.assertEqual(
            connector["role"], "canonical_chatgpt_work_repository_source_acquisition"
        )
        gate = connector["completion_gate"]
        self.assertTrue(gate["required"])
        self.assertEqual(gate["blocked_status"], "MATERIALIZATION_BLOCKED")
        self.assertIn("planning.materialization_verify", gate["entrypoint"])
        self.assertIn("Do not return merely because", gate["early_return_rule"])
        self.assertIn("exact-SHA connector", gate["blocked_status_rule"])
        self.assertIn("Git/DNS/checkout", gate["blocked_status_rule"])
        self.assertEqual(connector["evidence_file"]["schema_version"], 1)
        self.assertEqual(
            connector["manifest_path"],
            "youtube-shorts-bot/planning/PLANNER_MATERIALIZATION.json",
        )

    def test_local_validation_entrypoints_remain_shared(self):
        entrypoints = self.data["entrypoints"]
        for name in (
            "materialization_verify",
            "contract",
            "media_readiness",
            "precommit",
            "connector_drift",
        ):
            self.assertNotIn("github actions", entrypoints[name].lower())
        self.assertIn("planning.materialization_verify", entrypoints["materialization_verify"])
        self.assertIn("planning.planner_precommit", entrypoints["precommit"])
        self.assertNotIn("--verify-git-head", entrypoints["precommit"])
        self.assertIn("--connector-current-main-sha", entrypoints["connector_drift"])
        self.assertIn("--verify-git-head", entrypoints["git_precommit"])
        self.assertIn("planning.planner_drift", entrypoints["git_drift"])

    def test_profiles_share_the_same_connector_core(self):
        shared = set(self.data["shared_required_python_files"])
        self.assertEqual(len(shared), 19)
        for path in (
            "youtube-shorts-bot/planning/materialization_verify.py",
            "youtube-shorts-bot/planning/planner_precommit.py",
            "youtube-shorts-bot/planning/planner_core.py",
            "youtube-shorts-bot/planning/planner_profiles.py",
            "youtube-shorts-bot/planning/planner_contract_base.py",
            "youtube-shorts-bot/media/continuous_background.py",
            "youtube-shorts-bot/validation/validate_content_v5.py",
        ):
            self.assertIn(path, shared)
        self.assertNotIn("youtube-shorts-bot/planning/ranked_promotion.py", shared)
        self.assertNotIn("youtube-shorts-bot/publishing/upload.py", shared)
        self.assertEqual(self.data["profile_required_files"]["daily"]["python_files"], [])
        self.assertEqual(self.data["profile_required_files"]["adhoc"]["python_files"], [])

    def test_forbidden_requirements_keep_git_first_out_of_chatgpt(self):
        forbidden = self.data["forbidden_bootstrap_requirements"]
        self.assertIn("GitHub Actions planner execution", forbidden)
        self.assertIn("synthetic HEAD", forbidden)
        self.assertIn("fake repository identity", forbidden)
        for expected in (
            "ChatGPT/Work git fetch before connector/API acquisition",
            "ChatGPT/Work git clone before connector/API acquisition",
            "ChatGPT/Work git pull before connector/API acquisition",
            "ChatGPT/Work git ls-remote before connector/API acquisition",
            "ChatGPT/Work git rev-parse origin/main before connector/API acquisition",
            "ChatGPT/Work Git worktree creation",
            "ChatGPT/Work github.com DNS/proxy/network repair",
            "requiring .git metadata for ChatGPT/Work",
            "returning a Git/DNS/checkout failure before connector/API materialization",
        ):
            self.assertIn(expected, forbidden)
        self.assertTrue(any("returning early" in item.lower() for item in forbidden))
        self.assertTrue(any("MATERIALIZATION_BLOCKED" in item for item in forbidden))

    def test_prompts_bind_to_connector_first_shared_contract(self):
        shared = SHARED_PROMPT.read_text(encoding="utf-8")
        self.assertIn(
            "authorized GitHub connector/API is the canonical repository source-acquisition mechanism",
            shared,
        )
        self.assertIn("Shell Git access to github.com is neither attempted nor required", shared)
        self.assertIn("planning.materialization_verify", shared)
        self.assertIn("MATERIALIZATION_BLOCKED", shared)
        self.assertIn("--connector-current-main-sha", shared)
        self.assertIn("GitHub Actions planner execution remains prohibited", shared)

        prohibited_profile_text = (
            "git fetch origin main",
            "git clone",
            "git ls-remote",
            "git rev-parse origin/main",
            "git worktree",
            "--verify-git-head",
        )
        for name in ("ADHOC_PLANNER_PROMPT.md", "DAILY_PLANNER_PROMPT.md"):
            prompt = (PLANNING / name).read_text(encoding="utf-8")
            self.assertIn("docs/private/PLANNER_PROMPT.md", prompt)
            self.assertIn("canonical shared connector-first bootstrap", prompt)
            self.assertIn("Shared materialization completion gate", prompt)
            self.assertIn("MATERIALIZATION_BLOCKED", prompt)
            for forbidden_text in prohibited_profile_text:
                self.assertNotIn(forbidden_text, prompt)


if __name__ == "__main__":
    unittest.main()
