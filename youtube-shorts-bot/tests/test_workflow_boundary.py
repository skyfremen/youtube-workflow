import re
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
WORKFLOWS = ROOT / ".github/workflows"


class WorkflowBoundaryContracts(unittest.TestCase):
    def daily(self):
        return (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")

    def recovery(self):
        return (WORKFLOWS / "automatic-recovery.yml").read_text(encoding="utf-8")

    def adhoc(self):
        return (WORKFLOWS / "adhoc-production.yml").read_text(encoding="utf-8")

    def analytics(self):
        return (WORKFLOWS / "analytics-collection.yml").read_text(encoding="utf-8")

    def test_private_daily_workflow_is_dispatch_only(self):
        text = self.daily()
        for forbidden in (
            "container:",
            "youtube-shorts-runner",
            "media_resolver.py",
            "render_aligned.py",
            "verify_publication.py",
            "finalize_receipt.py",
            "upload-artifact",
            "YOUTUBE_CLIENT_ID",
            "PEXELS_API_KEY",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("actions/workflows/run.yml/dispatches", text)
        self.assertEqual(text.count("-X POST"), 1)

    def test_one_push_batch_produces_one_opaque_dispatch(self):
        text = self.daily()
        self.assertIn(
            "contains(github.event.head_commit.message, '[daily production]')", text
        )
        self.assertIn("python -m common.runtime_contract", text)
        self.assertIn("'batch_id': os.environ['BATCH_ID']", text)
        self.assertIn("'source_sha': os.environ['SOURCE_SHA']", text)
        self.assertIn("'contract_hash': os.environ['CONTRACT_HASH']", text)
        self.assertNotIn("'content_ids': os.environ", text)
        self.assertIn("b_$(printf", text)

    def test_opaque_routing_targets_are_stable(self):
        daily = self.daily()
        adhoc = self.adhoc()
        recovery = self.recovery()
        self.assertIn("actions/workflows/run.yml/dispatches", daily)
        self.assertIn("actions/workflows/single.yml/dispatches", adhoc)
        self.assertIn("actions/workflows/run.yml/dispatches", recovery)
        for workflow in (daily, adhoc, recovery):
            for field in ("batch_id", "source_sha", "contract_hash"):
                self.assertIn(f"'{field}'", workflow)
            for forbidden in ("'story'", "'title'", "'voice'", "'background'"):
                self.assertNotIn(forbidden, workflow)

    def test_manual_recovery_is_private_manifest_state(self):
        text = self.daily()
        self.assertIn("content/recovery/batches/{batch_id}.json", text)
        self.assertIn("source_commit_sha", text)
        self.assertIn("Existing immutable recovery manifest differs", text)
        self.assertIn("1-24 unique content IDs", text)

    def test_dispatcher_triggers_only_on_daily_plan_or_manual_recovery(self):
        text = self.daily()
        trigger = text.split("concurrency:", 1)[0]
        self.assertIn("branches: [main]", trigger)
        self.assertIn("youtube-shorts-bot/content/planning/*.json", trigger)
        self.assertNotIn("content/requests/*.json", trigger)
        self.assertNotIn("content/background-sourcing/*.json", trigger)
        self.assertIn("workflow_dispatch:", trigger)
        self.assertIn("content_ids:", trigger)

    def test_automatic_recovery_stays_in_private_control_plane(self):
        text = self.recovery()
        self.assertIn("recovery/controller.py", text)
        self.assertIn("content/diagnostics/**/*.json", text)
        self.assertIn("workflow_run:", text)
        self.assertIn("workflows: ['Daily Production', 'Ad-hoc Production']", text)
        self.assertIn("schedule:", text)
        self.assertIn("cron: '17 */2 * * *'", text)
        self.assertIn("RECOVERY_MAX_AUTOMATIC_ATTEMPTS: '3'", text)
        self.assertIn("RECOVERY_ACTIVE_GRACE_MINUTES: '210'", text)
        self.assertIn("actions/workflows/run.yml/dispatches", text)
        self.assertIn("python -m common.runtime_contract", text)
        self.assertIn("PUBLIC_PRODUCTION_TOKEN", text)
        self.assertIn("cancel-in-progress: false", text)
        for forbidden in (
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET",
            "YOUTUBE_REFRESH_TOKEN",
            "PEXELS_API_KEY",
            "videos().insert",
            "render_aligned.py",
        ):
            self.assertNotIn(forbidden, text)

    def test_automatic_recovery_manual_default_is_plan_only(self):
        text = self.recovery()
        self.assertRegex(text, r"workflow_dispatch:[\s\S]*default: plan")
        self.assertIn('if [ "${mode}" = "execute" ]', text)
        self.assertIn("--write", text)

    def test_analytics_runs_only_for_public_observation_snapshot(self):
        workflow = self.analytics()
        processor = (BASE / "analytics" / "analytics_collection.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("analytics/analytics_collection.py", workflow)
        self.assertIn(
            'REPO_ROOT / ".state" / "observations" / "latest.json"',
            processor,
        )
        self.assertIn("load_raw_snapshot()", processor)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("content/completions/*.json", workflow)
        self.assertNotIn("content/results/*.json", workflow)
        for secret in (
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET",
            "YOUTUBE_REFRESH_TOKEN",
        ):
            self.assertNotIn(secret, workflow)

    def test_all_actions_are_full_sha_pinned(self):
        for workflow in WORKFLOWS.glob("*.yml"):
            for line in workflow.read_text(encoding="utf-8").splitlines():
                if "uses:" in line:
                    ref = line.split("@", 1)[-1].split()[0]
                    self.assertRegex(ref, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
