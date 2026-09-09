import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
sys.path.insert(0, str(BASE))


class WorkflowFailFastContracts(unittest.TestCase):
    def batch(self):
        return (ROOT / ".github/workflows/daily-growth-batch.yml").read_text(encoding="utf-8")

    def test_daily_batch_runs_one_shared_youtube_preflight_before_external_cache_and_generation(self):
        batch = self.batch()
        preflight = "python youtube-shorts-bot/auth_check.py"
        self.assertEqual(batch.count(preflight), 1)
        self.assertLess(batch.index("python youtube-shorts-bot/validate_media_library.py"), batch.index(preflight))
        self.assertLess(batch.index(preflight), batch.index("ingest-manifest"))
        self.assertLess(batch.index(preflight), batch.index("media_resolver.py"))
        self.assertLess(batch.index(preflight), batch.index("render_aligned.py"))

    def test_global_duplicate_slot_contradiction_fails_before_shared_network_preflight(self):
        batch = self.batch()
        duplicate = "Duplicate publication slot in daily batch"
        self.assertIn(duplicate, batch)
        self.assertLess(batch.index(duplicate), batch.index("python youtube-shorts-bot/auth_check.py"))

    def test_pexels_secret_presence_is_global_and_fails_before_youtube_network(self):
        batch = self.batch()
        missing_pexels = 'if [ -s /tmp/background-sourcing-manifests.txt ] && [ -z "${PEXELS_API_KEY:-}" ]'
        self.assertIn(missing_pexels, batch)
        self.assertIn("Global failure", batch)
        self.assertLess(batch.index(missing_pexels), batch.index("python youtube-shorts-bot/auth_check.py"))

    def test_individual_schema_validation_is_inside_process_one_not_global_preflight(self):
        batch = self.batch()
        process_one = batch.index("process_one()")
        validate = batch.index("python youtube-shorts-bot/validate_content.py --request \"$req\"")
        self.assertGreater(validate, process_one)
        self.assertEqual(batch.count("validate_content.py"), 1)

    def test_individual_background_contract_is_per_video_before_expensive_media(self):
        batch = self.batch()
        process_one = batch.index("process_one()")
        prepare = batch.index("publish.py --stage prepare", process_one)
        background = batch.index("validate_request_backgrounds", process_one)
        resolver = batch.index("media_resolver.py", process_one)
        self.assertLess(prepare, background)
        self.assertLess(background, resolver)

    def test_upload_metadata_is_not_batch_fatal_anymore(self):
        batch = self.batch()
        global_step = batch[:batch.index("- name: Process videos with isolated per-video failures")]
        self.assertNotIn("build_upload_body", global_step)
        # publish.py prepare owns the recovery-first, schedule, and upload-body
        # validation path for each individual request.
        self.assertIn("publish.py --stage prepare", batch)

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

    def test_schedule_skip_branch_precedes_every_expensive_per_story_command(self):
        batch = self.batch()
        skip = 'if [ "$schedule_skipped" = "true" ]'
        self.assertIn(skip, batch)
        skip_at = batch.index(skip)
        for command in ("media_resolver.py", "render_aligned.py", "verify_render.py", "publish.py --stage upload"):
            self.assertLess(skip_at, batch.index(command, skip_at))

    def test_adhoc_does_not_add_redundant_second_auth_preflight(self):
        adhoc = (ROOT / ".github/workflows/adhoc-story-private.yml").read_text(encoding="utf-8")
        self.assertNotIn("auth_check.py", adhoc)
        self.assertLess(adhoc.index("publish.py --stage prepare"), adhoc.index("media_resolver.py"))


if __name__ == "__main__":
    unittest.main()
