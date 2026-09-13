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

    def backgrounds(self):
        return (WORKFLOWS / "background-management.yml").read_text(encoding="utf-8")

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

    def test_one_ranked_pool_produces_one_opaque_dispatch(self):
        text = self.daily()
        self.assertIn(
            "contains(github.event.head_commit.message, '[daily pool]')", text
        )
        self.assertIn("planning.pool_admission daily", text)
        self.assertIn("planning.ranked_promotion daily", text)
        self.assertIn("[daily production] ${plan_date}", text)
        self.assertIn("python -m common.runtime_contract", text)
        self.assertIn("'batch_id': os.environ['BATCH_ID']", text)
        self.assertIn("'source_sha': os.environ['SOURCE_SHA']", text)
        self.assertIn("'contract_hash': os.environ['CONTRACT_HASH']", text)
        self.assertNotIn("'content_ids': os.environ", text)
        self.assertIn("b_$(printf", text)
        self.assertEqual(text.count("actions/workflows/run.yml/dispatches"), 1)

    def test_promoted_state_is_validated_before_first_push(self):
        daily = self.daily()
        daily_admission = daily.index("planning.pool_admission daily")
        daily_promotion = daily.index("planning.ranked_promotion daily")
        daily_validate = daily.index("python -m validation.planning_audit")
        daily_publish = daily.index("Publish validated Daily production state")
        self.assertLess(daily_admission, daily_promotion)
        self.assertLess(daily_validate, daily_publish)
        self.assertLess(daily_publish, daily.index("Dispatch public execution"))

        adhoc = self.adhoc()
        adhoc_admission = adhoc.index("planning.pool_admission adhoc")
        adhoc_promotion = adhoc.index("planning.ranked_promotion adhoc")
        adhoc_validate = adhoc.index("python -m validation.validate_content --request")
        adhoc_unique = adhoc.index("planning.ranked_promotion verify-adhoc")
        adhoc_publish = adhoc.index("Publish validated Ad-hoc production state")
        self.assertLess(adhoc_admission, adhoc_promotion)
        self.assertLess(adhoc_validate, adhoc_publish)
        self.assertLess(adhoc_unique, adhoc_publish)
        self.assertLess(adhoc_publish, adhoc.index("Create opaque execution"))

    def test_adhoc_promotions_are_serialized_for_repository_idempotency(self):
        text = self.adhoc()
        self.assertIn("group: private-adhoc-production-${{ github.ref }}", text)
        self.assertNotIn("inputs.content_id || github.sha", text)

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

    def test_dispatcher_triggers_only_on_daily_pool_or_manual_recovery(self):
        text = self.daily()
        trigger = text.split("concurrency:", 1)[0]
        self.assertIn("branches: [main]", trigger)
        self.assertIn("youtube-shorts-bot/content/planning-pools/daily/**/*.json", trigger)
        self.assertNotIn("content/planning/*.json", trigger)
        self.assertNotIn("content/requests/*.json", trigger)
        self.assertNotIn("content/background-sourcing/*.json", trigger)
        self.assertIn("workflow_dispatch:", trigger)
        self.assertIn("content_ids:", trigger)

    def test_shared_media_maintenance_is_merge_safe_and_planning_only(self):
        text = self.backgrounds()
        trigger = text.split("concurrency:", 1)[0]
        self.assertIn("branches: [main]", trigger)
        self.assertIn("content/background-sourcing/readiness/*.json", trigger)
        self.assertNotIn("media-library/reset-selection-", trigger)
        self.assertIn("BEFORE_SHA: ${{ github.event.before }}", text)
        self.assertIn('git diff --name-status "${BEFORE_SHA}" "${GITHUB_SHA}"', text)
        self.assertNotIn("media.media_readiness retire-current", text)
        self.assertIn("media.media_readiness audit", text)
        self.assertIn("media.pexels_resilient_ingest", text)
        self.assertIn("PEXELS_API_KEY", text)
        self.assertIn("contents: write", text)
        for forbidden in (
            "render_aligned.py",
            "videos().insert",
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET",
            "YOUTUBE_REFRESH_TOKEN",
        ):
            self.assertNotIn(forbidden, text)

    def test_automatic_recovery_stays_in_private_control_plane(self):
        text = self.recovery()
        active_lines = {
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertIn("recovery/controller.py", text)
        self.assertIn("content/diagnostics/**/*.json", text)
        self.assertIn("workflow_run:", text)
        self.assertIn("workflows: ['Daily Production', 'Ad-hoc Production']", text)
        self.assertIn("schedule:", text)
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
