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

    def test_semantic_and_continuous_background_schema_are_fingerprinted(self):
        schema = runtime_contract.contract_payload()["schema"]
        self.assertEqual(schema["current_version"], 6)
        self.assertEqual(schema["supported_versions"], [4, 5, 6])
        self.assertEqual(schema["punchline_required_keys"], ["emphasis_text", "text"])
        self.assertEqual(schema["punchline_optional_keys"], ["type"])
        self.assertEqual(schema["punchline_max_emphasis_words"], 5)
        self.assertIn("REVERSAL", schema["punchline_types"])
        self.assertIn("punchline", schema["story_keys"])
        self.assertEqual(
            schema["treatment_keys"],
            ["mode", "segment_duration_seconds", "segment_start_seconds"],
        )
        self.assertEqual(schema["background_modes"], ["fit_to_short"])
        self.assertEqual(schema["fit_playback_rate_min"], 1.0)
        self.assertEqual(schema["fit_playback_rate_max"], 2.5)
        self.assertEqual(schema["min_continuous_source_seconds"], 180.0)
        self.assertEqual(schema["preferred_continuous_range_seconds"], 300.0)
        self.assertTrue(schema["runtime_derived_playback_rate"])
        self.assertEqual(schema["normal_loop_count"], 0)
        self.assertIn("background_primary_treatment", schema["visual_keys"])
        self.assertIn("background_backup_treatment", schema["visual_keys"])


if __name__ == "__main__":
    unittest.main()
