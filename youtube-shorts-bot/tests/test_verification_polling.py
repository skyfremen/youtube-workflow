import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from verify_youtube_private import RETRY_DELAYS


class VerificationPollingTests(unittest.TestCase):
    def test_polling_keeps_same_bound_without_long_blind_spot(self):
        self.assertEqual(RETRY_DELAYS[0], 0)
        self.assertEqual(sum(RETRY_DELAYS), 60)
        self.assertLessEqual(max(RETRY_DELAYS), 10)
        self.assertGreater(len(RETRY_DELAYS), 6)


if __name__ == '__main__':
    unittest.main()
