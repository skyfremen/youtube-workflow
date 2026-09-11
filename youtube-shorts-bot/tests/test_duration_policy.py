import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from common.workflow_common import (
    END_TAIL_SECONDS,
    START_LEAD_SECONDS,
    PRODUCTION_ENCODE_SAFETY_SECONDS,
    PRODUCTION_MAX_SECONDS,
    PRODUCTION_TARGET_MAX_SECONDS,
    expected_video_config,
)


class DurationPolicyTests(unittest.TestCase):
    def test_production_ceiling_and_tail(self):
        self.assertEqual(PRODUCTION_MAX_SECONDS, 178.0)
        self.assertEqual(PRODUCTION_TARGET_MAX_SECONDS, 175.0)
        self.assertEqual(START_LEAD_SECONDS, 0.50)
        self.assertEqual(END_TAIL_SECONDS, 0.35)
        self.assertEqual(PRODUCTION_ENCODE_SAFETY_SECONDS, 0.10)
        self.assertLess(PRODUCTION_MAX_SECONDS - PRODUCTION_ENCODE_SAFETY_SECONDS, 178.0)

    def test_default_canvas(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(expected_video_config(), {"width": 1080, "height": 1920, "fps": 30})

    def test_five_second_test_config_can_be_set(self):
        with patch.dict(os.environ, {"STORY_TEST_MODE": "true", "STORY_RENDER_MAX_SECONDS": "5"}):
            self.assertEqual(float(os.environ["STORY_RENDER_MAX_SECONDS"]), 5.0)


if __name__ == "__main__":
    unittest.main()
