import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from render import CARD_TRANSITION_SECONDS, caption_events, story_body_without_repeated_hook


class IntroSequenceTests(unittest.TestCase):
    def test_repeated_card_hook_is_not_repeated_in_story(self):
        hook = "My manager put the rule in writing."
        script = hook + "\n\nThen payroll saw the email and everything changed."
        self.assertEqual(
            story_body_without_repeated_hook(script, hook),
            "Then payroll saw the email and everything changed.",
        )

    def test_distinct_story_opening_is_preserved(self):
        hook = "The email changed everything."
        script = "We were three days from month-end when the meeting started."
        self.assertEqual(story_body_without_repeated_hook(script, hook), script)

    def test_subtitles_start_only_after_card_transition(self):
        story_start = 2.80 + CARD_TRANSITION_SECONDS
        events = caption_events(
            "Then payroll saw it",
            [("Then payroll saw it", 24000)],
            1.0,
            start_offset=story_start,
        )
        self.assertTrue(events)
        self.assertIn("0:00:03.10", events[0])
        self.assertNotIn("0:00:00.00", "\n".join(events))

    def test_renderer_fades_card_after_intro_and_offsets_captions(self):
        source = (ROOT / "render.py").read_text()
        self.assertIn("card_fade_start = intro_duration", source)
        self.assertIn("card_fade_dur = CARD_TRANSITION_SECONDS", source)
        self.assertIn("start_offset=story_start", source)
        self.assertIn("transition_audio = np.zeros", source)


if __name__ == "__main__":
    unittest.main()
