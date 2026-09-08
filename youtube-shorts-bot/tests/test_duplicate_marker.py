import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from workflow_common import marker_tag


class DuplicateIdentityTests(unittest.TestCase):
    def test_marker_contains_full_content_id(self):
        cid = "wd-20260908T161000-boss-overtime-a7c42f"
        self.assertEqual(marker_tag(cid), "wd-id-" + cid)


if __name__ == "__main__":
    unittest.main()
