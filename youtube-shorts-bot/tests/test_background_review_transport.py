import unittest
from pathlib import Path

from media.preview_review_materializer import _https_url, _representative_timestamps


class BackgroundReviewTransportContractTests(unittest.TestCase):
    def test_background_management_publishes_transport_only_review_artifact(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        self.assertIn('media.preview_review_materializer', workflow)
        self.assertIn('background-review-evidence-', workflow)
        self.assertIn(
            'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',
            workflow,
        )
        self.assertIn('discovery_result:', workflow)
        self.assertIn('--include-motion-evidence', workflow)
        self.assertIn('--representative-frames 5', workflow)
        self.assertIn('--motion-sample-seconds 6', workflow)
        self.assertNotIn('verified_preview=true', workflow)

    def test_review_transport_installs_ffmpeg_before_motion_materialization(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        install_index = workflow.index('- name: Install ffmpeg for exact-source motion evidence')
        materialize_index = workflow.index(
            '- name: Materialize exact preview evidence for ChatGPT review'
        )
        self.assertLess(install_index, materialize_index)
        self.assertIn('sudo apt-get install -y --no-install-recommends ffmpeg', workflow)

    def test_discovery_is_persisted_before_review_transport(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        commit_index = workflow.index('- name: Commit discovery result')
        materialize_index = workflow.index(
            '- name: Materialize exact preview evidence for ChatGPT review'
        )
        self.assertLess(commit_index, materialize_index)

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
