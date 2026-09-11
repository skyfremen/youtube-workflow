import re
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
WORKFLOWS = ROOT / ".github/workflows"


class WorkflowBoundaryContracts(unittest.TestCase):
    def daily(self):
        return (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")

    def analytics(self):
        return (WORKFLOWS / "analytics-collection.yml").read_text(encoding="utf-8")

    def test_private_daily_workflow_is_dispatch_only(self):
        text = self.daily()
        for forbidden in (
            "container:", "youtube-shorts-runner", "media_resolver.py",
            "render_aligned.py", "verify_publication.py", "finalize_receipt.py",
            "upload-artifact", "YOUTUBE_CLIENT_ID", "PEXELS_API_KEY",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("actions/workflows/run.yml/dispatches", text)
        self.assertEqual(text.count("-X POST"), 1)

    def test_one_push_batch_produces_one_opaque_dispatch(self):
        text = self.daily()
        self.assertIn("contains(github.event.head_commit.message, '[daily production]')", text)
        self.assertIn("'inputs': {'batch_id':", text)
        self.assertIn("'source_sha':", text)
        self.assertNotIn("'content_ids': os.environ", text)
        self.assertIn("b_$(printf", text)

    def test_manual_recovery_is_private_manifest_state(self):
        text = self.daily()
        self.assertIn("content/recovery/batches/{batch_id}.json", text)
        self.assertIn("source_commit_sha", text)
        self.assertIn("Existing immutable recovery manifest differs", text)
        self.assertIn("1-24 unique content IDs", text)

    def test_dispatcher_preserves_original_triggers(self):
        text = self.daily()
        for path in (
            "content/requests/*.json", "content/planning/*.json",
            "content/background-sourcing/*.json",
        ):
            self.assertIn(path, text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("content_ids:", text)

    def test_analytics_runs_only_for_public_observation_snapshot(self):
        text = self.analytics()
        self.assertIn(".state/observations/latest.json", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("content/completions/*.json", text)
        self.assertNotIn("content/results/*.json", text)
        for secret in (
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET",
            "YOUTUBE_REFRESH_TOKEN",
        ):
            self.assertNotIn(secret, text)

    def test_all_actions_are_full_sha_pinned(self):
        for workflow in WORKFLOWS.glob("*.yml"):
            for line in workflow.read_text(encoding="utf-8").splitlines():
                if "uses:" in line:
                    ref = line.split("@", 1)[-1].split()[0]
                    self.assertRegex(ref, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
