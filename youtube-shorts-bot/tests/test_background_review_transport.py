import unittest
from pathlib import Path

from media.preview_review_materializer import _https_url, _representative_timestamps


class BackgroundReviewTransportContractTests(unittest.TestCase):
    def test_background_management_does_not_require_public_review_evidence(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        self.assertNotIn('review-evidence.yml/dispatches', workflow)
        self.assertNotIn('PUBLIC_PRODUCTION_TOKEN', workflow)
        self.assertNotIn('Dispatch stateless exact-source review evidence', workflow)
        self.assertNotIn('verified_preview=true', workflow)
        self.assertNotIn('ffmpeg', workflow.lower())
        self.assertIn('Commit discovery result', workflow)
        self.assertIn('Ingest reviewed readiness manifest', workflow)

    def test_discovery_is_persisted_for_chatgpt_local_review(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        self.assertIn(
            'ChatGPT/Work consumes the exact\n      # preview URLs from this result and performs visual review locally',
            workflow,
        )
        self.assertNotIn('action=review', workflow)

    def test_materializer_builds_evenly_distributed_review_points(self):
        self.assertEqual(
            _representative_timestamps(60.0, 5),
            [10.0, 20.0, 30.0, 40.0, 50.0],
        )

    def test_materializer_rejects_non_pexels_visual_transport(self):
        with self.assertRaises(ValueError):
            _https_url('https://example.com/video.mp4', 'preview_video_url')

    def test_shared_background_policy_keeps_editorial_ownership_in_chatgpt(self):
        policy = Path('youtube-shorts-bot/docs/background-media-strategy.md').read_text(
            encoding='utf-8'
        )
        self.assertIn('canonical planner-time path is local to ChatGPT/Work', policy)
        self.assertIn('preview_review_materializer', policy)
        self.assertIn('optional transport fallback', policy)
        self.assertIn('GitHub Actions must never set `verified_preview`', policy)
        self.assertIn('Local Python outbound HTTPS is **not** a correctness dependency', policy)


if __name__ == '__main__':
    unittest.main()
