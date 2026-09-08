import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from test_request_schema import valid_request
from upload import build_upload_body


class PrivateUploadTests(unittest.TestCase):
    def test_payload_is_private_and_unscheduled(self):
        body = build_upload_body(valid_request(), privacy="private")
        self.assertEqual(body["status"]["privacyStatus"], "private")
        self.assertFalse(body["status"]["selfDeclaredMadeForKids"])
        self.assertNotIn("publishAt", body["status"])
        self.assertNotIn("publishAt", str(body))
        self.assertIn("wd-id-wd-20260908T161000-boss-overtime-a7c42f", body["snippet"]["tags"])

    def test_non_private_policy_rejected(self):
        with self.assertRaises(ValueError):
            build_upload_body(valid_request(), privacy="public")


if __name__ == "__main__":
    unittest.main()
