import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import runtime_contract
from common import workflow_common
from media import background_policy


class RuntimeContractTests(unittest.TestCase):
    def test_fingerprint_is_stable_sha256(self):
        first = runtime_contract.contract_hash()
        second = runtime_contract.contract_hash()
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_private_output_defaults_match_media_contract(self):
        payload = runtime_contract.contract_payload()
        output = payload["base"]["output"]
        self.assertEqual(output["width"], background_policy.TARGET_WIDTH)
        self.assertEqual(output["height"], background_policy.TARGET_HEIGHT)
        self.assertEqual(output["fps"], background_policy.TARGET_FPS)
        self.assertEqual(workflow_common.DEFAULT_VIDEO_WIDTH, 1080)
        self.assertEqual(workflow_common.DEFAULT_VIDEO_HEIGHT, 1920)
        self.assertEqual(workflow_common.DEFAULT_VIDEO_FPS, 30)

    def test_behavioral_vectors_are_frozen_into_contract(self):
        payload = runtime_contract.contract_payload()
        self.assertTrue(payload["behavior"]["marker"].startswith("wd-id-"))
        self.assertEqual(payload["behavior"]["voices"]["female:natural"], "af_heart")
        self.assertEqual(payload["behavior"]["voices"]["female:dramatic"], "af_bella")
        self.assertEqual(payload["behavior"]["voices"]["male:natural"], "am_echo")
        self.assertEqual(payload["behavior"]["voices"]["male:dramatic"], "am_fenrir")
        self.assertFalse(payload["behavior"]["renditions"]["hd_landscape"]["suitable"])
        self.assertTrue(payload["behavior"]["renditions"]["uhd_landscape"]["suitable"])


if __name__ == "__main__":
    unittest.main()
