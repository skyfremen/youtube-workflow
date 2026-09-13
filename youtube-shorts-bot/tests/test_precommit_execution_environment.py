import inspect
import unittest
from pathlib import Path

from planning import adhoc_precommit, daily_precommit
from planning.planner_contract import build_contract


BOT_ROOT = Path(__file__).resolve().parents[1]


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

    def test_contract_declares_explicit_sha_as_canonical_identity(self):
        execution = build_contract()["execution_environment"]
        self.assertEqual(execution["canonical_mode"], "explicit_rules_source_sha")
        self.assertFalse(execution["authenticated_checkout_required"])
        self.assertFalse(execution["git_metadata_required"])
        self.assertEqual(
            execution["repository_identity_source"], "explicit_rules_source_sha"
        )
        self.assertTrue(execution["legacy_snapshot_mode"]["deprecated"])
        self.assertFalse(execution["legacy_snapshot_mode"]["supported"])

    def test_canonical_prompts_do_not_require_git_head(self):
        for name in ("ADHOC_PLANNER_PROMPT.md", "DAILY_PLANNER_PROMPT.md"):
            prompt = (BOT_ROOT / "planning" / name).read_text(encoding="utf-8")
            self.assertIn("--rules-source-sha", prompt)
            self.assertIn("A Git checkout, Git executable, `.git` directory", prompt)
            self.assertIn("is **not** a planner prerequisite", prompt)
            self.assertIn("GitHub API/connector", prompt)
            self.assertIn("--verify-git-head", prompt)
            self.assertNotIn("$(git rev-parse HEAD)", prompt)
            self.assertNotIn("git clone", prompt.lower())


if __name__ == "__main__":
    unittest.main()
