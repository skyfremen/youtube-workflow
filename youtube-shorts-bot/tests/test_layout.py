import sys
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from render import fit_hook, wrap_caption, FONT_BOLD

class LayoutTests(unittest.TestCase):
    def test_acceptance_hook_is_complete_and_within_card(self):
        text='My boss made two hours of unpaid overtime mandatory every night, and one confirmation email ended the policy before lunch.'
        draw=ImageDraw.Draw(Image.new('RGB',(720,1280)))
        font,lines,height=fit_hook(draw,text,600,147,2/3)
        self.assertEqual(' '.join(lines),text)
        self.assertLessEqual(len(lines)*height,147)
        self.assertTrue(all(draw.textlength(line,font=font)<=600 for line in lines))

    def test_long_captions_are_explicitly_wrapped_inside_safe_width(self):
        font=ImageFont.truetype(FONT_BOLD,52)
        draw=ImageDraw.Draw(Image.new('L',(1,1)))
        for text in ('UNPAID OVERTIME MANDATORY','ONE CONFIRMATION EMAIL','EVERY NIGHT, AND'):
            wrapped=wrap_caption(text)
            self.assertEqual(' '.join(wrapped.split()),text)
            self.assertTrue(all(draw.textlength(line,font=font)<=500 for line in wrapped.splitlines()))
        self.assertIn('\n',wrap_caption('UNPAID OVERTIME MANDATORY'))

    def test_unrenderable_word_fails_instead_of_clipping(self):
        with self.assertRaises(ValueError):wrap_caption('X'*200)
