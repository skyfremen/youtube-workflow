import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from publishing.upload import build_upload_body
from test_request_schema import valid_request
from common.workflow_common import marker_tag


class TagRecoveryContractTests(unittest.TestCase):
    def test_upload_body_keeps_recovery_out_of_description_and_in_tags(self):
        request = valid_request()
        body = build_upload_body(request, require_future=False)
        marker = marker_tag(request["content_id"])

        self.assertNotIn("content_id=", body["snippet"]["description"])
        self.assertNotIn("request_blob_sha=", body["snippet"]["description"])
        self.assertIn(marker, body["snippet"]["tags"])
        self.assertEqual(body["status"]["privacyStatus"], "private")
        self.assertEqual(
            body["status"]["publishAt"],
            request["publication"]["publish_at"],
        )


if __name__ == "__main__":
    unittest.main()
