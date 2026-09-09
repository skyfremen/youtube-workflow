import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
