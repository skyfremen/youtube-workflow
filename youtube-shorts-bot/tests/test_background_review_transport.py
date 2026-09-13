import unittest
from pathlib import Path

from media.preview_review_materializer import _https_url, _representative_timestamps


class BackgroundReviewTransportContractTests(unittest.TestCase):
    def test_background_management_dispatches_public_review_evidence(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        self.assertIn('review-evidence.yml/dispatches', workflow)
        self.assertIn('PUBLIC_PRODUCTION_TOKEN', workflow)
        self.assertIn('discovery_result', workflow)
        self.assertIn('source_sha', workflow)
        self.assertNotIn('verified_preview=true', workflow)
        self.assertNotIn('ffmpeg', workflow.lower())

    def test_discovery_is_persisted_before_review_dispatch(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        commit_index = workflow.index('- name: Commit discovery result')
        dispatch_index = workflow.index(
            '- name: Dispatch stateless exact-source review evidence'
        )
        self.assertLess(commit_index, dispatch_index)

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
        self.assertIn('background-review-evidence-<request_id>', policy)
        self.assertIn('transport only', policy)
        self.assertIn('ChatGPT/Work must download the artifact', policy)
        self.assertIn('GitHub Actions must never set `verified_preview`', policy)


if __name__ == '__main__':
    unittest.main()
