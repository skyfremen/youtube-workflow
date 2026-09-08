import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from workflow_common import CONTENT_ID_RE, YOUTUBE_TAG_MAX_CHARS, marker_tag, request_path_for_id


class RequestResolverTests(unittest.TestCase):
    def test_content_id_format(self):
        cid = "wd-20260908T161000-boss-overtime-a7c42f"
        self.assertRegex(cid, CONTENT_ID_RE)
        self.assertEqual(request_path_for_id(cid).name, cid + ".json")

    def test_marker_is_exact_deterministic_identity(self):
        cid = "wd-20260908T161000-boss-overtime-a7c42f"
        marker = marker_tag(cid)
        self.assertEqual(marker, marker_tag(cid))
        self.assertTrue(marker.startswith("wd-id-"))
        self.assertLessEqual(len(marker), YOUTUBE_TAG_MAX_CHARS)


if __name__ == "__main__":
    unittest.main()
