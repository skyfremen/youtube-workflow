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

    def test_contract_declares_connector_materialization_canonical(self):
        execution = build_contract()["execution_environment"]
        self.assertEqual(execution["canonical_mode"], "connector_exact_sha_materialization")
        self.assertEqual(execution["preferred_bootstrap"], "connector_materialization")
        self.assertEqual(execution["fallback_bootstrap"], "none")
        self.assertEqual(
            execution["chatgpt_work_repository_source"],
            "authorized_github_connector_api",
        )
        self.assertFalse(execution["git_preferred"])
        self.assertFalse(execution["git_reuse_preferred"])
        self.assertFalse(execution["chatgpt_work_shell_git_allowed"])
        self.assertTrue(execution["developer_git_checkout_supported"])
        self.assertTrue(execution["exact_detached_snapshot_required_in_git_mode"])
        self.assertFalse(execution["authenticated_checkout_required"])
        self.assertFalse(execution["git_metadata_required"])
        self.assertFalse(execution["github_actions_planner_execution_required"])
        self.assertEqual(
            execution["repository_identity_source"],
            "connector_resolved_current_main_sha",
        )
        self.assertEqual(
            execution["materialization_mode"], "shared_plus_selected_profile"
        )
        self.assertEqual(execution["cache"]["primary_key"], "rules_source_sha")
        self.assertFalse(execution["cache"]["correctness_dependency"])
        self.assertNotIn(
            "--verify-git-head", execution["canonical_precommit_command"]
        )
        self.assertIn("--verify-git-head", execution["git_precommit_command"])
        self.assertIn("--connector-current-main-sha", execution["drift_command"])
        self.assertIn("planning.planner_drift", execution["developer_git_drift_command"])

    def test_canonical_prompts_never_require_shell_git_before_connector(self):
        shared = (
            REPO_ROOT / "docs" / "private" / "PLANNER_PROMPT.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Shell Git access to github.com is neither attempted nor required",
            shared,
        )
        self.assertIn("Never manufacture synthetic Git metadata", shared)
        self.assertIn("GitHub Actions planner execution remains prohibited", shared)
        for name in ("ADHOC_PLANNER_PROMPT.md", "DAILY_PLANNER_PROMPT.md"):
            prompt = (BOT_ROOT / "planning" / name).read_text(encoding="utf-8")
            combined = shared + "\n" + prompt
            self.assertIn("--rules-source-sha", combined)
            self.assertIn("authorized GitHub connector/API", combined)
            self.assertIn("planning.materialization_verify", combined)
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
