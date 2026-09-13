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
    def test_background_management_generates_private_review_artifact_without_approving(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        self.assertNotIn('PUBLIC_PRODUCTION_TOKEN', workflow)
        self.assertNotIn('verified_preview=true', workflow)
        self.assertIn('Materialize exact-source review contact sheets', workflow)
        self.assertIn('media.preview_review_materializer', workflow)
        self.assertIn('--contact-sheets-only', workflow)
        self.assertIn('actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02', workflow)
        self.assertIn('background-review-evidence-', workflow)
        self.assertIn('retention-days: 3', workflow)
        self.assertIn('Write immutable review evidence index', workflow)
        self.assertIn('content/background-sourcing/review-evidence/', workflow)
        self.assertIn('Ingest reviewed readiness manifest', workflow)

    def test_background_management_can_backfill_unindexed_discovery(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        self.assertIn('action=review', workflow)
        self.assertIn('newest discovery', workflow)
        self.assertIn('review_request_id', workflow)

    def test_materializer_builds_evenly_distributed_review_points(self):
        self.assertEqual(_representative_timestamps(60.0, 5), [10.0, 20.0, 30.0, 40.0, 50.0])

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
        self.assertEqual(result['image_failure_count'], 1)
        self.assertEqual(result['motion_evidence_count'], 1)

    def test_one_candidate_transport_failure_does_not_abort_remaining_candidates(self):
        discovery = {
            'request_id': 'dr-test',
            'candidates': [
                {'provider_asset_id': '123', 'source_page': 'https://www.pexels.com/video/example-123/', 'preview_image_url': 'https://images.pexels.com/photos/123/a.jpeg', 'preview_video_url': 'https://videos.pexels.com/video-files/123/a.mp4', 'duration_seconds': 60, 'preview_video_fps': 30},
                {'provider_asset_id': '456', 'source_page': 'https://www.pexels.com/video/example-456/', 'preview_image_url': 'https://images.pexels.com/photos/456/b.jpeg', 'preview_video_url': 'https://videos.pexels.com/video-files/456/b.mp4', 'duration_seconds': 60, 'preview_video_fps': 30},
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

    def test_staged_local_image_bypasses_blocked_python_network(self):
        discovery = {
            'request_id': 'dr-test',
            'candidates': [{
                'provider_asset_id': '123',
                'source_page': 'https://www.pexels.com/video/example-123/',
                'preview_image_url': 'https://images.pexels.com/photos/123/a.jpeg',
                'preview_video_url': 'https://videos.pexels.com/video-files/123/a.mp4',
                'duration_seconds': 60,
                'preview_video_fps': 30,
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'discovery.json'
            source.write_text(json.dumps(discovery), encoding='utf-8')
            staged = root / 'input' / '123' / 'preview.jpg'
            staged.parent.mkdir(parents=True)
            staged.write_bytes(b'exact-preview-pixels')
            with patch('media.preview_review_materializer._download', side_effect=RuntimeError('blocked')) as download:
                result = materialize(source, root / 'evidence', input_dir=root / 'input')
        download.assert_not_called()
        self.assertEqual(result['local_file_evidence_count'], 1)
        self.assertEqual(result['evidence'][0]['image']['transport'], 'local_file')

    def test_contact_sheets_only_skips_motion_sample(self):
        discovery = {
            'request_id': 'dr-test',
            'candidates': [{
                'provider_asset_id': '123',
                'source_page': 'https://www.pexels.com/video/example-123/',
                'preview_image_url': 'https://images.pexels.com/photos/123/a.jpeg',
                'preview_video_url': 'https://videos.pexels.com/video-files/123/a.mp4',
                'duration_seconds': 60,
                'preview_video_fps': 30,
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'discovery.json'
            source.write_text(json.dumps(discovery), encoding='utf-8')
            def fake_motion(candidate, destination, frame_count, sample_seconds, video_input=None, include_motion_sample=True):
                self.assertFalse(include_motion_sample)
                return {'source_url': candidate['preview_video_url'], 'transport': 'direct_url', 'contact_sheet': {'path': 'contact-sheet.jpg', 'bytes': 1, 'sha256': 'x'}}
            with patch('media.preview_review_materializer._download', side_effect=RuntimeError('image blocked')):
                with patch('media.preview_review_materializer._materialize_motion_evidence', side_effect=fake_motion):
                    result = materialize(source, Path(tmp) / 'evidence', include_motion_evidence=True, contact_sheets_only=True)
        self.assertTrue(result['contact_sheets_only'])
        self.assertFalse(result['motion_sample_requested'])
        self.assertEqual(result['motion_evidence_count'], 1)

    def test_shared_policy_keeps_editorial_ownership_in_chatgpt(self):
        policy = Path('youtube-shorts-bot/docs/background-media-strategy.md').read_text(encoding='utf-8')
        self.assertIn('private Background Management review-evidence artifact', policy)
        self.assertIn('review-evidence/<request_id>-run-<run_id>.json', policy)
        self.assertIn('contact-sheet.jpg', policy)
        self.assertIn('GitHub Actions must never set `verified_preview`', policy)
        self.assertIn('transport-only', policy)


if __name__ == '__main__':
    unittest.main()
