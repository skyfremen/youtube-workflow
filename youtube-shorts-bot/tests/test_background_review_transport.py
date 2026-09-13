import unittest
from pathlib import Path


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
        self.assertNotIn('verified_preview=true', workflow)

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
