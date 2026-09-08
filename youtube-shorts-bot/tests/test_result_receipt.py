import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from finalize import build_receipt
from test_request_schema import valid_request


class ResultReceiptTests(unittest.TestCase):
    def test_receipt_records_provenance_and_private_state(self):
        req = valid_request()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / (req["content_id"] + ".json")
            import json
            path.write_text(json.dumps(req), encoding="utf-8")
            upload = {
                "youtube_video_id": "abc123",
                "youtube_url": "https://www.youtube.com/watch?v=abc123",
                "uploaded_at": "2026-09-08T16:00:00+00:00",
                "privacy_status": "private",
                "publish_at": None,
                "youtube_verified_at": "2026-09-08T16:00:05+00:00",
                "content_id_tag_verified": True,
            }
            selection = {
                "background_asset_id": "satisfying-002",
                "background_selection": "backup",
            }
            render = {
                "narration_seconds": 4.5, "video_seconds": 4.85,
                "resolution": "720x1280", "fps": 30, "test_mode": True,
            }
            with patch.dict(os.environ, {"SOURCE_COMMIT_SHA": "deadbeef", "GITHUB_RUN_ID": "123"}):
                receipt = build_receipt(path, req, upload, selection, render)
            self.assertEqual(receipt["privacy_status"], "private")
            self.assertIsNone(receipt["publish_at"])
            self.assertEqual(receipt["background_selection"], "backup")
            self.assertEqual(receipt["source_commit_sha"], "deadbeef")
            self.assertTrue(receipt["request_blob_sha"])


if __name__ == "__main__":
    unittest.main()
