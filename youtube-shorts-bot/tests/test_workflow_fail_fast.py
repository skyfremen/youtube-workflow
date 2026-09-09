import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
sys.path.insert(0, str(BASE))


class WorkflowFailFastContracts(unittest.TestCase):
    def test_daily_batch_runs_one_shared_youtube_preflight_before_external_cache_and_generation(self):
        batch = (ROOT / ".github/workflows/daily-growth-batch.yml").read_text(encoding="utf-8")
        preflight = "python youtube-shorts-bot/auth_check.py"
        self.assertEqual(batch.count(preflight), 1)
        self.assertLess(batch.index("validate_content.py"), batch.index(preflight))
        self.assertLess(batch.index("build_upload_body(data, require_future=False)"), batch.index(preflight))
        self.assertLess(batch.index(preflight), batch.index("ingest-manifest"))
        self.assertLess(batch.index(preflight), batch.index("media_resolver.py"))
        self.assertLess(batch.index(preflight), batch.index("render_aligned.py"))

    def test_pexels_secret_presence_fails_before_youtube_network_when_sourcing_is_required(self):
        batch = (ROOT / ".github/workflows/daily-growth-batch.yml").read_text(encoding="utf-8")
        missing_pexels = 'if [ -s /tmp/background-sourcing-manifests.txt ] && [ -z "${PEXELS_API_KEY:-}" ]'
        self.assertIn(missing_pexels, batch)
        self.assertLess(batch.index(missing_pexels), batch.index("python youtube-shorts-bot/auth_check.py"))

    def test_schedule_skip_branch_precedes_every_expensive_per_story_command(self):
        batch = (ROOT / ".github/workflows/daily-growth-batch.yml").read_text(encoding="utf-8")
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
