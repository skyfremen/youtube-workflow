import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import render
from tts_backend import OnnxKokoroSynthesizer, sentence_chunks, validate_audio
from verify_render import parse_black_durations, resolve_blackdetect


class FakeOnnxEngine:
    def __init__(self):
        self.calls = []

    def create(self, text, voice, speed, lang):
        self.calls.append((text, voice, speed, lang))
        return np.full(2400, 0.05, dtype=np.float32), 24000


class OnnxNarrationTests(unittest.TestCase):
    def test_sentence_chunks_preserve_order_and_sentence_boundaries(self):
        text = "First sentence stays whole. Second sentence also stays whole! Third one finishes here?"
        chunks = sentence_chunks(text, max_words=7)
        self.assertEqual(" ".join(chunks), text)
        self.assertGreaterEqual(len(chunks), 2)

    def test_onnx_synthesis_preserves_voice_speed_language_and_order(self):
        synth = object.__new__(OnnxKokoroSynthesizer)
        synth.engine = FakeOnnxEngine()
        text = "One short sentence. Another short sentence. Final sentence."
        audio, segments, metrics = synth.synthesize(text, "af_heart", 1.75)
        self.assertGreater(audio.size, 0)
        self.assertEqual([text for text, _samples in segments], [call[0] for call in synth.engine.calls])
        self.assertTrue(all(call[1:] == ("af_heart", 1.75, "en-us") for call in synth.engine.calls))
        self.assertEqual(metrics["clipped_fraction"], 0.0)

    def test_audio_validation_rejects_wrong_sample_rate(self):
        with self.assertRaises(RuntimeError):
            validate_audio(np.ones(100, dtype=np.float32), 22050)

    def test_audio_validation_rejects_empty_nonfinite_and_pathological_clipping(self):
        with self.assertRaises(RuntimeError):
            validate_audio(np.array([], dtype=np.float32), 24000)
        with self.assertRaises(RuntimeError):
            validate_audio(np.array([0.0, np.nan], dtype=np.float32), 24000)
        with self.assertRaises(RuntimeError):
            validate_audio(np.ones(1000, dtype=np.float32), 24000)

    def test_renderer_keeps_primary_and_fallback_contract(self):
        source = (ROOT / "render.py").read_text(encoding="utf-8")
        self.assertIn("OnnxKokoroSynthesizer", source)
        self.assertIn("PytorchKokoroSynthesizer", source)
        self.assertIn("narration_backend_requested", source)
        self.assertIn("narration_backend_used", source)
        self.assertIn("narration_fallback_used", source)
        self.assertIn("narration_fallback_reason", source)
        self.assertIn('X264_PRESET = "superfast"', source)
        self.assertIn("X264_CRF = 19", source)


class BlackdetectTests(unittest.TestCase):
    def test_black_duration_parser(self):
        stderr = "black_start:1 black_end:1.4 black_duration:0.4\nblack_duration:0.72"
        self.assertEqual(parse_black_durations(stderr), [0.4, 0.72])

    def test_inline_evidence_skips_legacy_full_decode(self):
        def must_not_run(_video):
            raise AssertionError("legacy full-video blackdetect must not run")

        mode, maximum = resolve_blackdetect(
            {
                "inline_blackdetect_passed": True,
                "inline_blackdetect_max_duration_seconds": 0.0,
            },
            Path("unused.mp4"),
            legacy_runner=must_not_run,
        )
        self.assertEqual(mode, "inline_during_render")
        self.assertEqual(maximum, 0.0)

    def test_inline_evidence_at_threshold_fails_closed(self):
        with self.assertRaises(SystemExit):
            resolve_blackdetect(
                {
                    "inline_blackdetect_passed": True,
                    "inline_blackdetect_max_duration_seconds": 0.75,
                },
                Path("unused.mp4"),
            )

    def test_legacy_metadata_uses_compatibility_full_decode(self):
        seen = []

        def legacy(video):
            seen.append(video)
            return 0.10

        video = Path("legacy.mp4")
        mode, maximum = resolve_blackdetect({}, video, legacy_runner=legacy)
        self.assertEqual(mode, "legacy_second_pass")
        self.assertEqual(maximum, 0.10)
        self.assertEqual(seen, [video])

    def test_renderer_blackdetect_threshold_is_unchanged(self):
        self.assertEqual(render.BLACKDETECT_MAX_ALLOWED_SECONDS, 0.75)
        self.assertEqual(render.BLACKDETECT_FILTER, "blackdetect=d=0.50:pic_th=0.98:pix_th=0.10")


if __name__ == "__main__":
    unittest.main()
