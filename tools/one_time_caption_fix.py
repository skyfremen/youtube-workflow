from pathlib import Path

render = Path('youtube-shorts-bot/render.py')
text = render.read_text(encoding='utf-8')
start = text.index('def wrap_caption(text):\n')
end = text.index('\ndef centered_text(', start)
replacement = '''def caption_layout(text):
    cfg = expected_video_config()
    scale = cfg["width"] / 1080.0
    max_width = cfg["width"] - 2 * scaled(156, scale) - 2 * scaled(9, scale)
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    for base_size in range(78, 57, -2):
        fnt = font(FONT_BOLD, base_size, scale)
        lines, current = [], ""
        oversized = False
        for word in str(text).split():
            if draw.textlength(word, font=fnt) > max_width:
                oversized = True
                break
            trial = (current + " " + word).strip()
            if current and draw.textlength(trial, font=fnt) > max_width:
                lines.append(current)
                current = word
            else:
                current = trial
        if oversized:
            continue
        if current:
            lines.append(current)
        if len(lines) <= 3:
            return "\\n".join(lines), max(12, scaled(base_size, scale))
    raise ValueError("Caption cannot fit safe central region without clipping")


def wrap_caption(text):
    return caption_layout(text)[0]


def caption_ass_text(text):
    wrapped, event_font_size = caption_layout(text)
    payload = escape_ass(wrapped)
    cfg = expected_video_config()
    default_size = max(12, scaled(78, cfg["width"] / 1080.0))
    if event_font_size != default_size:
        return f"{{\\fs{event_font_size}}}{payload}"
    return payload

'''
text = text[:start] + replacement + text[end + 1:]
old = 'escape_ass(wrap_caption(chunk.upper()))'
count = text.count(old)
assert count == 2, f'expected two caption event call sites, found {count}'
text = text.replace(old, 'caption_ass_text(chunk.upper())')
render.write_text(text, encoding='utf-8')

test = Path('youtube-shorts-bot/tests/test_layout.py')
t = test.read_text(encoding='utf-8')
old_import = 'from render import fit_hook, wrap_caption, FONT_BOLD\n'
assert old_import in t
t = t.replace(old_import, 'from render import caption_layout, fit_hook, wrap_caption, FONT_BOLD\n')
anchor = "    def test_unrenderable_word_fails_instead_of_clipping(self):\n"
assert anchor in t
method = '''    def test_long_single_word_scales_down_without_clipping(self):
        wrapped,size=caption_layout('ADMINISTRATION')
        self.assertEqual(wrapped,'ADMINISTRATION')
        self.assertLess(size,52)
        font=ImageFont.truetype(FONT_BOLD,size)
        draw=ImageDraw.Draw(Image.new('L',(1,1)))
        self.assertLessEqual(draw.textlength(wrapped,font=font),500)

'''
t = t.replace(anchor, method + anchor)
test.write_text(t, encoding='utf-8')
