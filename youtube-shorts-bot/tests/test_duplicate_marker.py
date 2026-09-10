import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from common.workflow_common import YOUTUBE_TAG_MAX_CHARS, marker_tag


class DuplicateIdentityTests(unittest.TestCase):
    def test_marker_is_stable_and_platform_safe(self):
        cid = "wd-20260908T161000-boss-overtime-a7c42f"
        marker = marker_tag(cid)
        self.assertTrue(marker.startswith("wd-id-"))
        self.assertLessEqual(len(marker), YOUTUBE_TAG_MAX_CHARS)
        self.assertEqual(marker, marker_tag(cid))

    def test_different_content_ids_have_different_markers(self):
        a = "wd-20260908T161000-boss-overtime-a7c42f"
        b = "wd-20260908T161001-boss-overtime-b8d53a"
        self.assertNotEqual(marker_tag(a), marker_tag(b))


if __name__ == "__main__":
    unittest.main()
