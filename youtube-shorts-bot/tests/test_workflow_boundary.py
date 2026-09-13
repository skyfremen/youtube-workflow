import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = REPO_ROOT / "youtube-shorts-bot"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


class WorkflowBoundaryContracts(unittest.TestCase):
    def daily(self):
        return (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")

    def adhoc(self):
        return (WORKFLOWS / "adhoc-production.yml").read_text(encoding="utf-8")

    def recovery(self):
        return (WORKFLOWS / "automatic-recovery.yml").read_text(encoding="utf-8")

    def analytics(self):
        return (WORKFLOWS / "analytics-collection.yml").read_text(encoding="utf-8")

    def background_management(self):
        return (WORKFLOWS / "background-management.yml").read_text(encoding="utf-8")

    def test_private_daily_workflow_is_dispatch_only(self):
        text = self.daily()
        self.assertIn("actions/workflows/run.yml/dispatches", text)
        self.assertIn("python -m common.runtime_contract", text)
        self.assertNotIn("ffmpeg", text)
        self.assertNotIn("kokoro", text.lower())
        self.assertNotIn("wav2vec", text.lower())
        self.assertNotIn("videos().insert", text)

    def test_one_ranked_pool_produces_one_opaque_dispatch(self):
        text = self.daily()
        self.assertIn("planning.pool_admission daily", text)
        self.assertIn("planning.ranked_promotion daily", text)
        self.assertIn("batch_id", text)
        self.assertIn("source_sha", text)
        self.assertNotIn("content_ids_json", text)

    def test_adhoc_promotions_are_serialized_for_repository_idempotency(self):
        text = self.adhoc()
        self.assertIn("concurrency:", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("planning.ranked_promotion verify-adhoc", text)

    def test_opaque_routing_targets_are_stable(self):
        for text in (self.daily(), self.adhoc(), self.recovery()):
            self.assertNotIn("production-runtime/.github/workflows", text)
            self.assertNotIn("youtube-shorts-runner", text)

    def test_promoted_state_is_validated_before_first_push(self):
        for text in (self.daily(), self.adhoc()):
            self.assertRegex(text, r"git commit[\s\S]*validate[\s\S]*git push")

    def test_dispatcher_triggers_only_on_daily_pool_or_manual_recovery(self):
        text = self.daily()
        self.assertIn("planning-pools/daily/**/*.json", text)
        self.assertNotIn("content/requests/*.json", text)

    def test_shared_media_maintenance_is_merge_safe_and_planning_only(self):
        text = self.background_management()
        self.assertIn("pexels_resilient_ingest", text)
        self.assertIn("git pull --rebase", text)
        self.assertIn("ffmpeg", text.lower())
        self.assertIn("preview_review_materializer", text)
        self.assertIn("--contact-sheets-only", text)
        self.assertIn("transport evidence only", text.lower())
        self.assertNotIn("kokoro", text.lower())
        self.assertNotIn("wav2vec", text.lower())
        self.assertNotIn("render_aligned.py", text)
        self.assertNotIn("videos().insert", text)
        for secret in (
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET",
            "YOUTUBE_REFRESH_TOKEN",
        ):
            self.assertNotIn(secret, text)

    def test_manual_recovery_is_private_manifest_state(self):
        text = self.recovery()
        self.assertIn("content/recovery", text)
        self.assertNotIn("planner-execution", text)

    def test_automatic_recovery_stays_in_private_control_plane(self):
        text = self.recovery()
        active_lines = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertIn("- cron: '17,47 * * * *'", active_lines)
        self.assertNotIn("- cron: '17 */2 * * *'", active_lines)
        self.assertIn("RECOVERY_MAX_AUTOMATIC_ATTEMPTS: '3'", text)
        self.assertIn("RECOVERY_ACTIVE_GRACE_MINUTES: '240'", text)
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
        facade = (BASE / "analytics" / "analytics_collection.py").read_text(
            encoding="utf-8"
        )
        implementation = (BASE / "analytics" / "analytics_collection_v6.py").read_text(
            encoding="utf-8"
        )
        processor = facade + "\n" + implementation
        self.assertIn("analytics/analytics_collection.py", workflow)
        self.assertIn(
            'REPO_ROOT / ".state" / "observations" / "latest.json"',
            processor,
        )
        self.assertIn("load_raw_snapshot()", processor)
        self.assertIn("SUPPORTED_RECEIPT_SCHEMA_VERSIONS = {3, 4, 5, 6, 7}", facade)
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
