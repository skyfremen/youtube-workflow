import inspect
import unittest
from pathlib import Path

from planning import adhoc_precommit, daily_precommit
from planning.planner_contract import build_contract


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent


class PrecommitExecutionEnvironmentTests(unittest.TestCase):
    def test_adhoc_default_does_not_require_checkout_head(self):
        default = inspect.signature(adhoc_precommit.validate_draft).parameters[
            "check_checkout_head"
        ].default
        self.assertFalse(default)

    def test_daily_default_does_not_require_checkout_head(self):
        default = inspect.signature(daily_precommit.validate_draft).parameters[
            "check_checkout_head"
        ].default
        self.assertFalse(default)

    def test_contract_declares_connector_native_checkpoint_canonical(self):
        execution = build_contract()["execution_environment"]
        self.assertEqual(
            execution["canonical_chatgpt_work_mode"], "connector_native_checkpoint"
        )
        self.assertEqual(execution["preferred_bootstrap"], "connector_native_checkpoint")
        self.assertEqual(execution["fallback_bootstrap"], "none")
        self.assertEqual(
            execution["chatgpt_work_repository_source"],
            "authorized_github_connector_api",
        )
        self.assertEqual(
            execution["checkpoint_path"], "planning/connector_checkpoint.py"
        )
        self.assertFalse(execution["git_preferred"])
        self.assertFalse(execution["git_reuse_preferred"])
        self.assertFalse(execution["chatgpt_work_shell_git_allowed"])
        self.assertTrue(execution["developer_git_checkout_supported"])
        self.assertFalse(execution["authenticated_checkout_required"])
        self.assertFalse(execution["git_metadata_required"])
        self.assertFalse(execution["repository_archive_required"])
        self.assertFalse(execution["repository_tree_materialization_required"])
        self.assertFalse(execution["full_background_registry_local_copy_required"])
        self.assertFalse(execution["materialization_verify_required"])
        self.assertFalse(execution["github_actions_planner_execution_required"])
        self.assertEqual(
            execution["repository_identity_source"],
            "connector_resolved_current_main_sha",
        )
        self.assertIn(
            "connector_checkpoint.py", execution["canonical_chatgpt_work_command"]
        )
        self.assertIn("--verify-git-head", execution["developer_ci_precommit_command"])
        self.assertIn("--connector-current-main-sha", execution["drift_command"])

    def test_canonical_prompts_do_not_require_shell_git(self):
        shared = (
            REPO_ROOT / "docs" / "private" / "PLANNER_PROMPT.md"
        ).read_text(encoding="utf-8")
        lower = shared.lower()
        self.assertIn("authorized github connector/api", lower)
        self.assertIn("shell git", lower)
        self.assertIn("connector_checkpoint.py", shared)
        self.assertIn("CHECKPOINT_STAGING_BLOCKED", shared)
        self.assertIn("review-decisions/<request_id>.json", shared)
        for name in ("ADHOC_PLANNER_PROMPT.md", "DAILY_PLANNER_PROMPT.md"):
            prompt = (BOT_ROOT / "planning" / name).read_text(encoding="utf-8")
            combined = shared + "\n" + prompt
            self.assertIn("--rules-source-sha", combined)
            self.assertIn("authorized GitHub connector/API", combined)
            self.assertIn("connector_checkpoint.py", combined)
            for forbidden in (
                "git fetch origin main",
                "git clone",
                "git ls-remote",
                "git rev-parse origin/main",
                "git worktree",
            ):
                self.assertNotIn(forbidden, prompt)
            self.assertNotIn("--verify-git-head", prompt)


if __name__ == "__main__":
    unittest.main()
