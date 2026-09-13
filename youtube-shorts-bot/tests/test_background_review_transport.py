import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media.preview_review_materializer import (
    _https_url,
    _representative_timestamps,
    materialize,
)


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

    def test_image_failure_falls_through_to_exact_video_evidence(self):
        discovery = {
            'request_id': 'dr-test',
            'candidates': [{
                'provider_asset_id': '123',
                'source_page': 'https://www.pexels.com/video/example-123/',
                'preview_image_url': 'https://images.pexels.com/photos/123/pexels-photo-123.jpeg',
                'preview_video_url': 'https://videos.pexels.com/video-files/123/example.mp4',
                'duration_seconds': 60,
                'preview_video_fps': 30,
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'discovery.json'
            source.write_text(json.dumps(discovery), encoding='utf-8')
            motion = {
                'source_url': discovery['candidates'][0]['preview_video_url'],
                'contact_sheet': {'path': 'contact-sheet.jpg', 'bytes': 1, 'sha256': 'x'},
                'motion_sample': {'path': 'motion-sample.mp4', 'bytes': 1, 'sha256': 'y'},
            }
            with patch('media.preview_review_materializer._download', side_effect=RuntimeError('image blocked')):
                with patch('media.preview_review_materializer._materialize_motion_evidence', return_value=motion):
                    result = materialize(source, Path(tmp) / 'evidence', include_motion_evidence=True)

        self.assertEqual(result['evidence_count'], 1)
        self.assertEqual(result['failure_count'], 0)
        self.assertEqual(result['image_failure_count'], 1)
        self.assertEqual(result['motion_evidence_count'], 1)
        self.assertEqual(result['evidence'][0]['available_visual_transports'], ['motion'])

    def test_one_candidate_transport_failure_does_not_abort_remaining_candidates(self):
        discovery = {
            'request_id': 'dr-test',
            'candidates': [
                {
                    'provider_asset_id': '123',
                    'source_page': 'https://www.pexels.com/video/example-123/',
                    'preview_image_url': 'https://images.pexels.com/photos/123/a.jpeg',
                    'preview_video_url': 'https://videos.pexels.com/video-files/123/a.mp4',
                    'duration_seconds': 60,
                    'preview_video_fps': 30,
                },
                {
                    'provider_asset_id': '456',
                    'source_page': 'https://www.pexels.com/video/example-456/',
                    'preview_image_url': 'https://images.pexels.com/photos/456/b.jpeg',
                    'preview_video_url': 'https://videos.pexels.com/video-files/456/b.mp4',
                    'duration_seconds': 60,
                    'preview_video_fps': 30,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'discovery.json'
            source.write_text(json.dumps(discovery), encoding='utf-8')

            def fake_download(url, destination, max_bytes):
                if '/123/' in url:
                    raise RuntimeError('candidate 123 blocked')
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b'x')
                return {'path': str(destination), 'bytes': 1, 'sha256': 'x'}

            with patch('media.preview_review_materializer._download', side_effect=fake_download):
                result = materialize(source, Path(tmp) / 'evidence', include_motion_evidence=False)

        self.assertEqual(result['evidence_count'], 1)
        self.assertEqual(result['failure_count'], 1)
        self.assertEqual(result['evidence'][0]['provider_asset_id'], '456')

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
