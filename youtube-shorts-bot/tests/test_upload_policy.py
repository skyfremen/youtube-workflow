import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from test_request_schema import valid_request
from upload import build_upload_body
from workflow_common import marker_tag


class AdhocUploadTests(unittest.TestCase):
    def test_payload_is_public_and_unscheduled(self):
        request = valid_request()
        body = build_upload_body(request)
        self.assertEqual(body["status"]["privacyStatus"], "public")
        self.assertFalse(body["status"]["selfDeclaredMadeForKids"])
        self.assertNotIn("publishAt", body["status"])
        self.assertNotIn("publishAt", str(body))
        self.assertIn(marker_tag(request["content_id"]), body["snippet"]["tags"])

    def test_explicit_private_policy_rejected_for_new_adhoc_upload(self):
        with self.assertRaises(ValueError):
            build_upload_body(valid_request(), privacy="private")

    def test_static_scheduled_validation_can_check_metadata_without_rejecting_elapsed_slot(self):
        now = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)
        request = valid_request()
        publish_at = (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        request["publication"] = {
            "mode": "scheduled", "timezone": "Asia/Singapore", "publish_at": publish_at
        }
        body = build_upload_body(request, require_future=False, now_utc=now)
        self.assertEqual(body["status"]["privacyStatus"], "private")
        self.assertEqual(body["status"]["publishAt"], publish_at)
        with self.assertRaisesRegex(ValueError, "future"):
            build_upload_body(request, now_utc=now)

    def test_description_limit_fails_before_upload(self):
        request = valid_request()
        request["youtube"]["description"] = "x" * 4995
        with self.assertRaisesRegex(ValueError, "5000-byte"):
            build_upload_body(request, require_future=False)

    def test_tag_limit_fails_before_upload(self):
        request = valid_request()
        request["youtube"]["hashtags"] = ["#" + (str(i) * 180) for i in range(3)]
        with self.assertRaisesRegex(ValueError, "500-character"):
            build_upload_body(request, require_future=False)


if __name__ == "__main__":
    unittest.main()
