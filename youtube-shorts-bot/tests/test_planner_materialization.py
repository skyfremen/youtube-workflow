import json
import shutil
import subprocess
import sys
import tempfile
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

    def test_connector_native_checkpoint_is_canonical(self):
        self.assertEqual(self.data["schema_version"], 8)
        self.assertEqual(self.data["contract"], "connector_native_planner_checkpoint")
        bootstrap = self.data["planner_bootstrap"]
        self.assertEqual(bootstrap["preferred"], "connector_native_checkpoint")
        self.assertEqual(bootstrap["fallback"], "none")
        self.assertEqual(
            bootstrap["chatgpt_work_source"], "authorized_github_connector_api"
        )
        self.assertFalse(bootstrap["github_actions_planning"])
        self.assertTrue(bootstrap["exact_sha_required"])
        self.assertFalse(bootstrap["shell_git_attempted_in_chatgpt_work"])

        requirements = self.data["chatgpt_work_requirements"]
        for key in (
            "git_required",
            "git_executable_required",
            "checkout_required",
            "git_metadata_required",
            "repository_archive_required",
            "repository_tree_materialization_required",
            "full_background_registry_local_copy_required",
            "connector_filesystem_mount_required",
            "materialization_verify_required",
        ):
            self.assertFalse(requirements[key], key)

    def test_standalone_checkpoint_path_exists_and_runs_without_repository(self):
        checkpoint = self.data["connector_native_checkpoint"]
        relative = checkpoint["path"]
        source = BOT_ROOT / relative.removeprefix("youtube-shorts-bot/")
        self.assertTrue(source.is_file(), relative)
        self.assertTrue(checkpoint["standard_library_only"])
        self.assertFalse(checkpoint["repository_imports"])

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "connector_checkpoint.py"
            shutil.copyfile(source, target)
            self.assertFalse((Path(temporary) / ".git").exists())
            completed = subprocess.run(
                [sys.executable, str(target), "contract"],
                cwd=temporary,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["repository"], "skyfremen/youtube-workflow")
        self.assertEqual(payload["checkpoint_schema_version"], 1)
        self.assertEqual(payload["request_schema_version"], 7)
        self.assertEqual(
            payload["execution_environment"]["canonical_mode"],
            "connector_native_checkpoint",
        )
        self.assertFalse(payload["execution_environment"]["shell_git_required"])
        self.assertFalse(payload["execution_environment"]["git_checkout_required"])
        self.assertEqual(payload["profiles"]["daily"]["pool_size"], 36)
        self.assertEqual(payload["profiles"]["adhoc"]["pool_size"], 5)

    def test_bounded_replenishment_contract_is_machine_readable(self):
        continuation = self.data["background_replenishment_continuation"]
        self.assertEqual(continuation["state"], "recoverable_intermediate")
        self.assertEqual(continuation["discovery_request_schema_version"], 2)
        self.assertEqual(continuation["review_decision_schema_version"], 1)
        self.assertEqual(
            continuation["session_identity_field"], "replenishment_session_id"
        )
        self.assertEqual(continuation["max_attempts"], 5)
        self.assertEqual(
            continuation["terminal_exhausted_code"],
            "E_MEDIA_REPLENISH_EXHAUSTED",
        )
        self.assertTrue(continuation["durable_review_exclusion"]["enabled"])

    def test_forbidden_bootstrap_keeps_shell_git_out_of_chatgpt(self):
        forbidden = self.data["forbidden_bootstrap_requirements"]
        for expected in (
            "ChatGPT/Work git fetch",
            "ChatGPT/Work git clone",
            "ChatGPT/Work git pull",
            "ChatGPT/Work git ls-remote",
            "ChatGPT/Work Git worktree creation",
            "ChatGPT/Work github.com DNS/proxy repair",
            "requiring .git metadata",
        ):
            self.assertIn(expected, forbidden)
        self.assertTrue(any("GitHub Actions" in value for value in forbidden))

    def test_prompts_bind_to_shared_connector_native_contract(self):
        shared = SHARED_PROMPT.read_text(encoding="utf-8")
        self.assertIn("authorized GitHub connector/API", shared)
        self.assertIn("connector_checkpoint.py", shared)
        self.assertIn("CHECKPOINT_STAGING_BLOCKED", shared)
        self.assertIn("review-decisions/<request_id>.json", shared)
        self.assertIn("E_MEDIA_REPLENISH_EXHAUSTED", shared)

        for name, profile in (
            ("ADHOC_PLANNER_PROMPT.md", "adhoc"),
            ("DAILY_PLANNER_PROMPT.md", "daily"),
        ):
            prompt = (PLANNING / name).read_text(encoding="utf-8")
            self.assertIn("docs/private/PLANNER_PROMPT.md", prompt)
            self.assertIn("connector_checkpoint.py", prompt)
            self.assertIn(f"--profile {profile}", prompt)
            self.assertNotIn("--verify-git-head", prompt)
            self.assertNotIn("git fetch origin main", prompt)


if __name__ == "__main__":
    unittest.main()
