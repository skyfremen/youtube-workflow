from pathlib import Path

render_path = Path('youtube-shorts-bot/render.py')
text = render_path.read_text(encoding='utf-8')

old = 'CARD_TRANSITION_SECONDS = 0.30\n'
new = '''CARD_TRANSITION_SECONDS = 0.30

# Wacky Dramas production layout is permanently 720x1280. Keep all UI
# geometry in native output pixels so safe-space rules are explicit.
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280

CAPTION_MARGIN_X = 85
CAPTION_MAX_WIDTH = VIDEO_WIDTH - (2 * CAPTION_MARGIN_X)  # 550px
CAPTION_FONT_SIZE = 52
CAPTION_MIN_FONT_SIZE = 39
CAPTION_MAX_LINES = 3
CAPTION_OUTLINE = 5
CAPTION_SHADOW = 1

CARD_BOX = (37, 157, 683, 537)
CARD_RADIUS = 24
CARD_SHADOWS = ((7, 55), (12, 25))
CARD_BORDER_WIDTH = 3
AVATAR_SIZE = 88
AVATAR_POS = (55, 193)
CHANNEL_NAME_POS = (157, 190)
CHANNEL_NAME_FONT_SIZE = 27
VERIFIED_ICON_SIZE = 25
VERIFIED_ICON_GAP = 12
VERIFIED_ICON_Y_OFFSET = 3
EMOJI_ROW_Y = 233
EMOJI_STEP_X = 51
EMOJI_TARGET_SIZE = 44
EMOJI_CELL_SIZE = 39
HOOK_POS = (57, 303)
HOOK_MAX_WIDTH = 600
HOOK_MAX_HEIGHT = 147
HOOK_MAX_FONT_SIZE = 43
HOOK_MIN_FONT_SIZE = 27
HOOK_LINE_GAP = 6
FOOTER_Y = 495
FOOTER_FONT_SIZE = 20
LIKE_ICON_SIZE = 20
COMMENT_ICON_SIZE = 21
SHARE_ICON_SIZE = 19
LIKE_X = 55
COMMENT_X = 143
SHARE_X = 579
FOOTER_TEXT_GAP = 7
HANDLE_PILL = (190, 840, 530, 889)
SUBSCRIBE_PILL = (240, 899, 480, 945)
HANDLE_FONT_SIZE = 28
SUBSCRIBE_FONT_SIZE = 25
PILL_OUTLINE_WIDTH = 1
CARD_BOB_AMPLITUDE = 4
'''
assert text.count(old) == 1
text = text.replace(old, new)

start = text.index('def scaled(value, scale):\n')
end = text.index('\ndef wrap_pixels(', start)
text = text[:start] + '''def font_px(path, size):
    return ImageFont.truetype(path, max(12, int(size)))

''' + text[end + 1:]

start = text.index('def fit_hook(')
end = text.index('\ndef centered_text(', start)
replacement = '''def fit_hook(draw, text, max_width, max_height):
    for font_size in range(HOOK_MAX_FONT_SIZE, HOOK_MIN_FONT_SIZE - 1, -1):
        fnt = font_px(FONT_BOLD, font_size)
        lines, fits = wrap_pixels(draw, text, fnt, max_width, 6)
        bb = draw.textbbox((0, 0), "Ag", font=fnt)
        line_height = (bb[3] - bb[1]) + HOOK_LINE_GAP
        widths_fit = all(draw.textlength(line, font=fnt) <= max_width for line in lines)
        if fits and widths_fit and len(lines) * line_height <= max_height:
            return fnt, lines, line_height
    raise ValueError("Complete opening hook cannot fit card bounds; refusing to truncate text")


def caption_layout(text):
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    for font_size in range(CAPTION_FONT_SIZE, CAPTION_MIN_FONT_SIZE - 1, -1):
        fnt = font_px(FONT_BOLD, font_size)
        lines, current = [], ""
        oversized = False
        for word in str(text).split():
            if draw.textlength(word, font=fnt) > CAPTION_MAX_WIDTH:
                oversized = True
                break
            trial = (current + " " + word).strip()
            if current and draw.textlength(trial, font=fnt) > CAPTION_MAX_WIDTH:
                lines.append(current)
                current = word
            else:
                current = trial
        if oversized:
            continue
        if current:
            lines.append(current)
        if len(lines) <= CAPTION_MAX_LINES:
            return "\\n".join(lines), font_size
    raise ValueError("Caption cannot fit safe central region without clipping")


def wrap_caption(text):
    return caption_layout(text)[0]


def caption_ass_text(text):
    wrapped, event_font_size = caption_layout(text)
    payload = escape_ass(wrapped)
    if event_font_size != CAPTION_FONT_SIZE:
        return f"{{\\fs{event_font_size}}}{payload}"
    return payload


def build_ass_header():
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {VIDEO_WIDTH}
PlayResY: {VIDEO_HEIGHT}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Main,DejaVu Sans,{CAPTION_FONT_SIZE},&H00FFFFFF,&H00FFFFFF,&H00101010,&H35000000,-1,0,0,0,100,100,0,0,1,{CAPTION_OUTLINE},{CAPTION_SHADOW},5,{CAPTION_MARGIN_X},{CAPTION_MARGIN_X},0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

'''
text = text[:start] + replacement + text[end + 1:]

text = text.replace('def render_emoji(icon, target_size, scale):', 'def render_emoji(icon, target_size):')
text = text.replace('    # the configured canvas. Scaling the font size itself makes Pillow\n', '    # the fixed 720p canvas. Scaling the font size itself makes Pillow\n')

old = '''    cfg = expected_video_config()
    W, H, fps = cfg["width"], cfg["height"], cfg["fps"]
    if W <= 0 or H <= 0 or fps <= 0:
        raise SystemExit("VIDEO_WIDTH, VIDEO_HEIGHT and VIDEO_FPS must be positive")
    sx, sy = W / 1080.0, H / 1920.0
    scale = min(sx, sy)
'''
new = '''    cfg = expected_video_config()
    fps = cfg["fps"]
    if (cfg["width"], cfg["height"]) != (VIDEO_WIDTH, VIDEO_HEIGHT):
        raise SystemExit("Wacky Dramas renderer requires fixed 720x1280 production dimensions")
    if fps <= 0:
        raise SystemExit("VIDEO_FPS must be positive")
    W, H = VIDEO_WIDTH, VIDEO_HEIGHT
'''
assert text.count(old) == 1
text = text.replace(old, new)

start = text.index('    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))\n')
end = text.index('    card_path = OUTPUT_DIR / "story-card.png"\n', start)
ui = '''    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    brand = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc, db = ImageDraw.Draw(card), ImageDraw.Draw(brand)

    box = CARD_BOX
    for offset, alpha in CARD_SHADOWS:
        shadow = (box[0] + offset, box[1] + offset, box[2] + offset, box[3] + offset)
        dc.rounded_rectangle(shadow, radius=CARD_RADIUS, fill=(0, 0, 0, alpha))
    dc.rounded_rectangle(
        box,
        radius=CARD_RADIUS,
        fill=(251, 251, 251, 252),
        outline=(28, 28, 28, 255),
        width=CARD_BORDER_WIDTH,
    )

    logo_path = ASSETS / "channel-avatar.png"
    if not logo_path.exists():
        raise SystemExit(f"Missing required asset: {logo_path}")
    with Image.open(logo_path) as src:
        src.load()
        logo = src.convert("RGBA").copy()
    rgb = logo.convert("RGB")
    stat = ImageStat.Stat(rgb)
    extrema = rgb.getextrema()
    if max(stat.mean) < 18 or sum(hi - lo for lo, hi in extrema) < 90:
        raise SystemExit("channel-avatar.png appears blank or corrupt")
    avatar = logo.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
    mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, AVATAR_SIZE - 1, AVATAR_SIZE - 1), fill=255)
    clipped = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
    clipped.paste(avatar, (0, 0), mask)
    card.alpha_composite(clipped, AVATAR_POS)

    name_x, name_y = CHANNEL_NAME_POS
    name_font = font_px(FONT_BOLD, CHANNEL_NAME_FONT_SIZE)
    dc.text((name_x, name_y), channel_name, font=name_font, fill=(18, 18, 18, 255))
    name_bb = dc.textbbox((name_x, name_y), channel_name, font=name_font)
    verified = load_ui_icon("verified-blue.png", VERIFIED_ICON_SIZE)
    card.alpha_composite(
        verified,
        (int(name_bb[2] + VERIFIED_ICON_GAP), int(name_y + VERIFIED_ICON_Y_OFFSET)),
    )

    emojis = story.get("card_emojis", [])[:6]
    ix = name_x
    for emoji in emojis:
        img = render_emoji(str(emoji), EMOJI_TARGET_SIZE)
        x = int(ix + (EMOJI_CELL_SIZE - img.width) / 2)
        y = int(EMOJI_ROW_Y + (EMOJI_CELL_SIZE - img.height) / 2)
        card.alpha_composite(img, (x, y))
        ix += EMOJI_STEP_X

    hook_x, hook_y = HOOK_POS
    hook_font, hook_lines, line_height = fit_hook(
        dc, hook, HOOK_MAX_WIDTH, HOOK_MAX_HEIGHT
    )
    for i, line in enumerate(hook_lines):
        dc.text((hook_x, hook_y + i * line_height), line, font=hook_font, fill=(8, 8, 8, 255))

    light = (110, 110, 110, 255)
    meta_font = font_px(FONT_REG, FOOTER_FONT_SIZE)
    like = load_ui_icon("like.png", LIKE_ICON_SIZE)
    comment = load_ui_icon("comment.png", COMMENT_ICON_SIZE)
    share = load_ui_icon("share.png", SHARE_ICON_SIZE)
    end = paste_icon_centered(card, like, LIKE_X, FOOTER_Y)
    draw_text_centered_y(dc, end + FOOTER_TEXT_GAP, FOOTER_Y, "99+", meta_font, light)
    end = paste_icon_centered(card, comment, COMMENT_X, FOOTER_Y)
    draw_text_centered_y(dc, end + FOOTER_TEXT_GAP, FOOTER_Y, "99+", meta_font, light)
    end = paste_icon_centered(card, share, SHARE_X, FOOTER_Y)
    draw_text_centered_y(dc, end + FOOTER_TEXT_GAP, FOOTER_Y, "Share", meta_font, light)

    def pill(draw, box, text, fnt, fill):
        draw.rounded_rectangle(
            box,
            radius=(box[3] - box[1]) // 2,
            fill=(0, 0, 0, 225),
            outline=(255, 255, 255, 70),
            width=PILL_OUTLINE_WIDTH,
        )
        centered_text(draw, box, text, fnt, fill)

    pill(db, HANDLE_PILL, handle, font_px(FONT_BOLD, HANDLE_FONT_SIZE), (255, 255, 255, 255))
    pill(
        db,
        SUBSCRIBE_PILL,
        "SUBSCRIBE",
        font_px(FONT_BOLD, SUBSCRIBE_FONT_SIZE),
        (255, 214, 40, 255),
    )

'''
text = text[:start] + ui + text[end:]

start = text.index('    events = caption_events(')
end = text.index('    video = OUTPUT_DIR / "short.mp4"\n', start)
ass = '''    events = caption_events(narration_text, tts_segments, story_duration, start_offset=story_start)
    ass = OUTPUT_DIR / "captions.ass"
    ass.write_text(build_ass_header() + "\\n".join(events) + "\\n", encoding="utf-8")

'''
text = text[:start] + ass + text[end:]

old = '        f"[bg][card]overlay=x=0:y=\'-{scaled(6, sy)}*sin(PI*t/2)\'[tmp1];"\n'
new = '        f"[bg][card]overlay=x=0:y=\'-{CARD_BOB_AMPLITUDE}*sin(PI*t/2)\'[tmp1];"\n'
assert text.count(old) == 1
text = text.replace(old, new)

for forbidden in ('W / 1080.0', 'H / 1920.0', 'scaled(', 'sx', 'sy', 'scale = min('):
    assert forbidden not in text, forbidden

render_path.write_text(text, encoding='utf-8')

test_path = Path('youtube-shorts-bot/tests/test_layout.py')
test = '''import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from render import (
    CAPTION_FONT_SIZE,
    CAPTION_MARGIN_X,
    CAPTION_MAX_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
    FONT_BOLD,
    build_ass_header,
    caption_layout,
    fit_hook,
    wrap_caption,
)


class LayoutTests(unittest.TestCase):
    def test_acceptance_hook_is_complete_and_within_card(self):
        text = 'My boss made two hours of unpaid overtime mandatory every night, and one confirmation email ended the policy before lunch.'
        draw = ImageDraw.Draw(Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT)))
        font, lines, height = fit_hook(draw, text, 600, 147)
        self.assertEqual(' '.join(lines), text)
        self.assertLessEqual(len(lines) * height, 147)
        self.assertTrue(all(draw.textlength(line, font=font) <= 600 for line in lines))

    def test_caption_geometry_is_native_720p_and_centered(self):
        self.assertEqual((VIDEO_WIDTH, VIDEO_HEIGHT), (720, 1280))
        self.assertEqual(CAPTION_MARGIN_X, 85)
        self.assertEqual(CAPTION_MAX_WIDTH, 550)
        self.assertEqual(VIDEO_WIDTH - 2 * CAPTION_MARGIN_X, CAPTION_MAX_WIDTH)

        header = build_ass_header()
        self.assertIn('PlayResX: 720', header)
        self.assertIn('PlayResY: 1280', header)
        style = next(line for line in header.splitlines() if line.startswith('Style: Main,'))
        self.assertIn(',5,85,85,0,1', style)

    def test_long_captions_are_explicitly_wrapped_inside_safe_width(self):
        font = ImageFont.truetype(FONT_BOLD, CAPTION_FONT_SIZE)
        draw = ImageDraw.Draw(Image.new('L', (1, 1)))
        for text in ('UNPAID OVERTIME MANDATORY', 'ONE CONFIRMATION EMAIL', 'EVERY NIGHT, AND'):
            wrapped = wrap_caption(text)
            self.assertEqual(' '.join(wrapped.split()), text)
            self.assertTrue(
                all(draw.textlength(line, font=font) <= CAPTION_MAX_WIDTH for line in wrapped.splitlines())
            )
        self.assertIn('\\n', wrap_caption('UNPAID OVERTIME MANDATORY'))

    def test_long_single_word_scales_down_without_clipping(self):
        wrapped, size = caption_layout('MISCOMMUNICATION')
        self.assertEqual(wrapped, 'MISCOMMUNICATION')
        self.assertLess(size, CAPTION_FONT_SIZE)
        font = ImageFont.truetype(FONT_BOLD, size)
        draw = ImageDraw.Draw(Image.new('L', (1, 1)))
        self.assertLessEqual(draw.textlength(wrapped, font=font), CAPTION_MAX_WIDTH)

    def test_unrenderable_word_fails_instead_of_clipping(self):
        with self.assertRaises(ValueError):
            wrap_caption('X' * 200)
'''
test_path.write_text(test, encoding='utf-8')
