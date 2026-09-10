import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
sys.path.insert(0, str(BASE))


class WorkflowFailFastContracts(unittest.TestCase):
    def batch(self):
        return (ROOT / ".github/workflows/daily-production.yml").read_text(encoding="utf-8")

    def test_daily_batch_runs_one_shared_youtube_preflight_before_external_cache_and_generation(self):
        batch = self.batch()
        preflight = "python youtube-shorts-bot/publishing/auth_preflight.py"
        # One production preflight plus one conditional analytics fallback path.
        self.assertEqual(batch.count(preflight), 2)
        first_preflight = batch.index(preflight)
        self.assertLess(batch.index("python youtube-shorts-bot/media/validate_media_library.py"), first_preflight)
        self.assertLess(first_preflight, batch.index("ingest-manifest"))
        self.assertLess(first_preflight, batch.index("media/media_resolver.py"))
        self.assertLess(first_preflight, batch.index("rendering/render_aligned.py"))

    def test_global_duplicate_slot_contradiction_fails_before_shared_network_preflight(self):
        batch = self.batch()
        duplicate = "Duplicate publication slot in daily batch"
        self.assertIn(duplicate, batch)
        self.assertLess(batch.index(duplicate), batch.index("python youtube-shorts-bot/publishing/auth_preflight.py"))

    def test_pexels_secret_presence_is_global_and_fails_before_youtube_network(self):
        batch = self.batch()
        missing_pexels = 'if [ -s /tmp/background-sourcing-manifests.txt ] && [ -z "${PEXELS_API_KEY:-}" ]'
        self.assertIn(missing_pexels, batch)
        self.assertIn("Global failure", batch)
        self.assertLess(batch.index(missing_pexels), batch.index("python youtube-shorts-bot/publishing/auth_preflight.py"))

    def test_shared_youtube_preflight_exports_tri_state_for_independent_analytics(self):
        batch = self.batch()
        initial = 'echo "youtube_preflight_status=not_run" >> "$GITHUB_OUTPUT"'
        passed = 'echo "youtube_preflight_status=passed" >> "$GITHUB_OUTPUT"'
        failed = 'echo "youtube_preflight_status=failed" >> "$GITHUB_OUTPUT"'
        preflight = "python youtube-shorts-bot/publishing/auth_preflight.py"
        analytics = batch.index("- name: Collect analytics for next planning cycle")
        self.assertIn(initial, batch)
        self.assertIn(passed, batch)
        self.assertIn(failed, batch)
        self.assertLess(batch.index(initial), batch.index(preflight))
        self.assertLess(batch.index(preflight), batch.index(passed))
        self.assertLess(batch.index(passed), analytics)
        self.assertIn(
            "PRODUCTION_YOUTUBE_PREFLIGHT_STATUS: ${{ steps.batch.outputs.youtube_preflight_status }}",
            batch[analytics:],
        )

    def test_individual_schema_validation_is_inside_process_one_not_global_preflight(self):
        batch = self.batch()
        process_one = batch.index("process_one()")
        validate = batch.index("python youtube-shorts-bot/validation/validate_content.py --request \"$req\"")
        self.assertGreater(validate, process_one)
        self.assertEqual(batch.count("validation/validate_content.py"), 1)

    def test_individual_background_contract_is_per_video_before_expensive_media(self):
        batch = self.batch()
        process_one = batch.index("process_one()")
        prepare = batch.index("publishing/publish.py --stage prepare", process_one)
        background = batch.index("validate_request_backgrounds", process_one)
        resolver = batch.index("media/media_resolver.py", process_one)
        self.assertLess(prepare, background)
        self.assertLess(background, resolver)

    def test_upload_metadata_is_not_batch_fatal_anymore(self):
        batch = self.batch()
        global_step = batch[:batch.index("- name: Process videos with isolated per-video failures")]
        self.assertNotIn("build_upload_body", global_step)
        self.assertIn("publishing/publish.py --stage prepare", batch)

    def test_per_video_failure_continues_loop_then_fails_job_at_end(self):
        batch = self.batch()
        process = batch[batch.index("- name: Process videos with isolated per-video failures"):]
        loop = process.index("while IFS= read -r req")
        caught = process.index('if process_one "$req"; then', loop)
        continue_message = process.index("continuing remaining Shorts", caught)
        done = process.index("done < /tmp/batch-requests.txt", continue_message)
        final_exit = process.index("exit 1", done)
        self.assertLess(caught, continue_message)
        self.assertLess(continue_message, done)
        self.assertLess(done, final_exit)

    def test_youtube_verification_is_deferred_until_all_production_attempts_finish(self):
        batch = self.batch()
        process_one = batch.index("process_one()")
        upload = batch.index("publishing/publish.py --stage upload", process_one)
        deferred = batch.index("verification_deferred", upload)
        verify_definition = batch.index("verify_one()", deferred)
        verify = batch.index("publishing/verify_publication.py --request", verify_definition)
        finalize = batch.index("publishing/finalize_receipt.py --request", verify)
        production_done = batch.index("done < /tmp/batch-requests.txt", finalize)
        verify_call = batch.index('if verify_one "$req" "$deferred_at"; then', production_done)
        self.assertLess(upload, deferred)
        self.assertLess(deferred, production_done)
        self.assertLess(verify, finalize)
        self.assertLess(production_done, verify_call)

    def test_deferred_verification_preserves_failure_isolation_and_receipt_attempts(self):
        batch = self.batch()
        verification_loop = batch.index("# Phase 2:")
        caught = batch.index('if verify_one "$req" "$deferred_at"; then', verification_loop)
        continued = batch.index("continuing remaining receipts", caught)
        verification_done = batch.index("done < /tmp/batch-pending-verification.txt", continued)
        final_exit = batch.index("exit 1", verification_done)
        self.assertLess(caught, continued)
        self.assertLess(continued, verification_done)
        self.assertLess(verification_done, final_exit)

    def test_pipeline_metrics_are_lightweight_and_preserved(self):
        batch = self.batch()
        self.assertIn("/tmp/batch-pipeline-metrics.tsv", batch)
        self.assertIn("youtube_processing_overlap_seconds=", batch)
        artifact = batch[batch.index("- name: Preserve lightweight per-story evidence"):]
        self.assertIn("/tmp/batch-pipeline-metrics.tsv", artifact)
        for heavy in ("short.mp4", "narration.wav", "background.mp4"):
            self.assertNotIn(heavy, artifact)

    def test_schedule_skip_branch_precedes_every_expensive_per_story_command(self):
        batch = self.batch()
        skip = 'if [ "$schedule_skipped" = "true" ]'
        self.assertIn(skip, batch)
        skip_at = batch.index(skip)
        for command in ("media/media_resolver.py", "rendering/render_aligned.py", "rendering/verify_render.py", "publishing/publish.py --stage upload"):
            self.assertLess(skip_at, batch.index(command, skip_at))

    def test_analytics_is_non_blocking_and_fail_first_guards_precede_collection(self):
        batch = self.batch()
        start = batch.index("- name: Collect analytics for next planning cycle")
        analytics = batch[start:]
        self.assertIn("if: ${{ always() && github.event_name == 'push' }}", analytics)
        self.assertIn("continue-on-error: true", analytics)

        credentials = analytics.index("ANALYTICS FAIL-FIRST 1")
        duplicate = analytics.index("ANALYTICS FAIL-FIRST 2")
        auth = analytics.index("ANALYTICS FAIL-FIRST 3")
        eligible = analytics.index("ANALYTICS FAIL-FIRST 4")
        collect = analytics.index("python youtube-shorts-bot/analytics/analytics_collection.py")
        validate = analytics.index("ANALYTICS FAIL-CLOSED")
        commit = analytics.index('git commit -m "[skip upload] update YouTube analytics ${analytics_marker}"')

        self.assertLess(credentials, duplicate)
        self.assertLess(duplicate, auth)
        self.assertLess(auth, eligible)
        self.assertLess(eligible, collect)
        self.assertLess(collect, validate)
        self.assertLess(validate, commit)

    def test_analytics_reuses_known_good_auth_and_does_not_repeat_known_failure(self):
        batch = self.batch()
        analytics = batch[batch.index("- name: Collect analytics for next planning cycle"):]
        self.assertIn('case "${PRODUCTION_YOUTUBE_PREFLIGHT_STATUS:-not_run}" in', analytics)
        self.assertIn("passed)", analytics)
        self.assertIn("Reusing successful production YouTube preflight", analytics)
        self.assertIn("failed)", analytics)
        self.assertIn("Production already proved YouTube authentication/readiness failed", analytics)
        self.assertIn("Production did not reach YouTube preflight", analytics)
        self.assertEqual(analytics.count("python youtube-shorts-bot/publishing/auth_preflight.py"), 1)

    def test_analytics_rerun_guard_uses_stable_run_id(self):
        batch = self.batch()
        analytics = batch[batch.index("- name: Collect analytics for next planning cycle"):]
        self.assertIn('analytics_marker="[analytics run ${GITHUB_RUN_ID}]"', analytics)
        self.assertIn("git log -1 --fixed-strings --grep=\"$analytics_marker\"", analytics)
        self.assertIn("skipping duplicate collection", analytics)
        self.assertIn("${analytics_marker}", analytics)

    def test_invalid_analytics_output_is_restored_before_any_commit(self):
        batch = self.batch()
        analytics = batch[batch.index("- name: Collect analytics for next planning cycle"):]
        validation = analytics.index("Analytics output validation passed")
        restore = analytics.index("git restore --source=HEAD --staged --worktree -- youtube-shorts-bot/analytics/")
        commit = analytics.index('git commit -m "[skip upload] update YouTube analytics ${analytics_marker}"')
        self.assertLess(validation, restore)
        self.assertLess(restore, commit)
        self.assertIn("retaining previous committed model", analytics)
        self.assertIn("dated analytics snapshot differs from latest.json", analytics)
        self.assertIn("analytics/latest.json embedded model differs from model.json", analytics)


if __name__ == "__main__":
    unittest.main()
