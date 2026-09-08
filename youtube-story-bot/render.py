import json, math, subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFile
from kokoro import KPipeline

ImageFile.LOAD_TRUNCATED_IMAGES = True

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'
OUT = BASE / 'output'
ASSETS = BASE / 'assets'
OUT.mkdir(exist_ok=True)

data = json.loads(CONTENT.read_text(encoding='utf-8'))
duration = float(data.get('duration_seconds', 45.0))
channel_name = str(data.get('channel_name', 'Wacky Dramas'))
handle = str(data.get('handle', '@WACKYDRAMAS')).upper()
hook = str(data['hook'])
story = str(data['story'])
voice = str(data.get('tts_voice', 'af_heart'))
speed = float(data.get('tts_speed', 1.75))

W, H = 1080, 1920
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def run(cmd):
    subprocess.run(cmd, check=True)


def download(url, target, source_url=None):
    cmd = [
        'curl', '-L', '--fail', '--silent', '--show-error', '--retry', '3',
        '--connect-timeout', '20', '--max-time', '120', '-A', 'Mozilla/5.0',
        '-o', str(target)
    ]
    if source_url:
        cmd += ['-e', str(source_url)]
    cmd.append(str(url))
    run(cmd)


def ass_time(seconds):
    cs = int(round(max(0, seconds) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f'{h}:{m:02}:{s:02}.{cs:02}'


def escape_ass(text):
    return str(text).replace('\\', r'\\').replace('{', r'\{').replace('}', r'\}').replace('\n', r'\N')


def phrase_chunks(text, max_words=5):
    words = text.split()
    return [' '.join(words[i:i + max_words]) for i in range(0, len(words), max_words)]


def wrap_pixels(draw, text, font, max_width, max_lines=3):
    words = text.split()
    lines, current = [], ''
    for word in words:
        trial = f'{current} {word}'.strip()
        width = draw.textbbox((0, 0), trial, font=font)[2]
        if current and width > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines[:max_lines], len(lines) <= max_lines


def fit_hook(draw, text, max_width, max_height):
    for size in range(62, 43, -2):
        font = ImageFont.truetype(FONT_BOLD, size)
        lines, fits_lines = wrap_pixels(draw, text, font, max_width, max_lines=3)
        line_height = draw.textbbox((0, 0), 'Ag', font=font)[3] + 9
        if fits_lines and len(lines) * line_height <= max_height:
            return font, lines, line_height
    font = ImageFont.truetype(FONT_BOLD, 44)
    lines, _ = wrap_pixels(draw, text, font, max_width, max_lines=3)
    return font, lines, draw.textbbox((0, 0), 'Ag', font=font)[3] + 8


def centered_text(draw, box, text, font, fill):
    x1, y1, x2, y2 = box
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((x1 + (x2 - x1 - tw) / 2, y1 + (y2 - y1 - th) / 2 - 2), text, font=font, fill=fill)


# Kokoro TTS. Wacky Dramas standard speed is 1.75x.
pipeline = KPipeline(lang_code='a')
audio_parts = []
for _gs, _ps, audio in pipeline(story, voice=voice, speed=speed):
    audio_parts.append(np.asarray(audio, dtype=np.float32))
if not audio_parts:
    raise SystemExit('Kokoro produced no audio')
audio = np.concatenate(audio_parts)
target_samples = int(duration * 24000)
if len(audio) < target_samples:
    audio = np.pad(audio, (0, target_samples - len(audio)))
else:
    audio = audio[:target_samples]
narration = OUT / 'narration.wav'
sf.write(narration, audio, 24000)

# Separate transient card from persistent branding so the card can disappear
# after the hook while the handle + subscribe prompt remain visible.
card_overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
branding_overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
d_card = ImageDraw.Draw(card_overlay)
d_brand = ImageDraw.Draw(branding_overlay)

# Move the card higher so it occupies the top third rather than the middle.
card_box = (56, 290, 1024, 858)
for off, alpha in [(10, 55), (18, 25)]:
    d_card.rounded_rectangle(
        (card_box[0] + off, card_box[1] + off, card_box[2] + off, card_box[3] + off),
        radius=36, fill=(0, 0, 0, alpha)
    )
d_card.rounded_rectangle(card_box, radius=36, fill=(251, 251, 251, 252), outline=(28, 28, 28, 255), width=5)

# Display picture. Crop away transparent padding before fitting so the actual
# logo fills the avatar circle instead of appearing as a tiny sliver.
logo_path = ASSETS / 'channel-logo.png'
logo_loaded = False
if logo_path.exists():
    try:
        with Image.open(logo_path) as source_logo:
            source_logo.load()
            logo = source_logo.convert('RGBA').copy()
        bbox = logo.getbbox()
        if bbox:
            logo = logo.crop(bbox)
        avatar_size = 132
        fitted = ImageOps.contain(logo, (avatar_size, avatar_size), method=Image.Resampling.LANCZOS)
        avatar = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
        avatar.alpha_composite(fitted, ((avatar_size - fitted.width) // 2, (avatar_size - fitted.height) // 2))
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size - 1, avatar_size - 1), fill=255)
        clipped = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
        clipped.paste(avatar, (0, 0), mask)
        card_overlay.alpha_composite(clipped, (82, 345))
        logo_loaded = True
    except (OSError, ValueError) as exc:
        print(f'WARNING: channel logo could not be decoded; using WD fallback: {exc}')
if not logo_loaded:
    d_card.ellipse((82, 345, 214, 477), fill=(18, 18, 22, 255), outline=(230, 55, 45, 255), width=7)
    f_avatar = ImageFont.truetype(FONT_BOLD, 46)
    centered_text(d_card, (82, 345, 214, 477), 'WD', f_avatar, (255, 255, 255, 255))

# Channel name + verified tick.
name_x, name_y = 235, 340
f_name = ImageFont.truetype(FONT_BOLD, 40)
d_card.text((name_x, name_y), channel_name, font=f_name, fill=(18, 18, 18, 255))
name_bb = d_card.textbbox((name_x, name_y), channel_name, font=f_name)
vx, vy = name_bb[2] + 18, name_y + 8
d_card.ellipse((vx, vy, vx + 36, vy + 36), fill=(75, 128, 255, 255))
d_card.text((vx + 9, vy + 4), '✓', font=ImageFont.truetype(FONT_BOLD, 22), fill='white')

# Larger separated decorative icons that remain readable on a phone screen.
icon_y, icon_size, icon_gap = 408, 42, 18
icons = [
    ('✦', (185, 157, 255)), ('✿', (210, 210, 210)), ('◆', (250, 214, 88)),
    ('☕', (245, 235, 170)), ('♨', (245, 130, 95)), ('✺', (84, 216, 190)),
    ('◉', (110, 205, 255))
]
ix = name_x
icon_font = ImageFont.truetype(FONT_BOLD, 22)
for symbol, color in icons:
    d_card.ellipse((ix, icon_y, ix + icon_size, icon_y + icon_size), fill=color + (255,), outline=(255, 255, 255, 180), width=2)
    centered_text(d_card, (ix, icon_y, ix + icon_size, icon_y + icon_size), symbol, icon_font, (25, 25, 25, 255))
    ix += icon_size + icon_gap

# Hook is pixel wrapped and constrained to the card.
hook_x, hook_y = 86, 510
hook_width, hook_height = 900, 210
hook_font, hook_lines, line_height = fit_hook(d_card, hook, hook_width, hook_height)
for i, line in enumerate(hook_lines):
    d_card.text((hook_x, hook_y + i * line_height), line, font=hook_font, fill=(8, 8, 8, 255))

# Engagement row: separate like and comment counters with a real message bubble.
foot_y = 770
light = (110, 110, 110, 255)
f_meta = ImageFont.truetype(FONT_REG, 30)
f_sym = ImageFont.truetype(FONT_REG, 34)
d_card.text((82, foot_y - 6), '♡', font=f_sym, fill=light)
d_card.text((128, foot_y), '99+', font=f_meta, fill=light)

bubble_x, bubble_y = 218, foot_y + 3
d_card.rounded_rectangle((bubble_x, bubble_y, bubble_x + 40, bubble_y + 28), radius=9, outline=light, width=3)
d_card.polygon([
    (bubble_x + 11, bubble_y + 28),
    (bubble_x + 17, bubble_y + 38),
    (bubble_x + 22, bubble_y + 28)
], fill=light)
d_card.text((272, foot_y), '99+', font=f_meta, fill=light)

d_card.text((872, foot_y - 4), '↗', font=ImageFont.truetype(FONT_REG, 29), fill=light)
d_card.text((906, foot_y), 'Share', font=f_meta, fill=light)

# Persistent safe-zone branding with opaque rounded black backgrounds.
def pill(draw_obj, box, text, font, fill):
    draw_obj.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=(0, 0, 0, 225), outline=(255, 255, 255, 70), width=2)
    centered_text(draw_obj, box, text, font, fill)

pill(d_brand, (285, 1490, 795, 1564), handle, ImageFont.truetype(FONT_BOLD, 42), (255, 255, 255, 255))
pill(d_brand, (360, 1578, 720, 1648), 'SUBSCRIBE', ImageFont.truetype(FONT_BOLD, 38), (255, 214, 40, 255))

card_overlay_path = OUT / 'story-card.png'
branding_overlay_path = OUT / 'branding.png'
card_overlay.save(card_overlay_path)
branding_overlay.save(branding_overlay_path)

# Phrase-following subtitles: larger font, wider horizontal safety margins and
# centered vertically once the transient card has disappeared.
chunks = phrase_chunks(story, 5)
weights = [max(1, len(c.split())) for c in chunks]
total = sum(weights)
t = 0.10
events = []
for c, w in zip(chunks, weights):
    seg = max(0.30, (duration - 0.2) * w / total)
    end = min(duration - 0.03, t + seg)
    events.append(f'Dialogue: 0,{ass_time(t)},{ass_time(end)},Main,,0,0,0,,{escape_ass(c.upper())}')
    t = end

ass = OUT / 'captions.ass'
ass.write_text(f'''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Main,DejaVu Sans,72,&H00FFFFFF,&H00FFFFFF,&H00101010,&H35000000,-1,0,0,0,100,100,0,0,1,7,2,5,210,210,0,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n''' + '\n'.join(events) + '\n', encoding='utf-8')

# Visually satisfying background, independent from story semantics.
background = OUT / 'background.asset'
download(data['background_url'], background, data.get('background_source_url'))
video = OUT / 'short.mp4'
filter_complex = (
    "[0:v]fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
    "eq=brightness=-0.03:saturation=1.03[bg];"
    "[1:v]format=rgba,fade=t=out:st=1.70:d=0.30:alpha=1[card];"
    "[2:v]format=rgba[brand];"
    "[bg][card]overlay=x=0:y='-6*sin(PI*t/2)'[tmp1];"
    "[tmp1][brand]overlay=0:0[tmp2];"
    f"[tmp2]subtitles='{ass.as_posix()}'[v]"
)
run([
    'ffmpeg', '-y',
    '-stream_loop', '-1', '-i', str(background),
    '-loop', '1', '-i', str(card_overlay_path),
    '-loop', '1', '-i', str(branding_overlay_path),
    '-i', str(narration),
    '-filter_complex', filter_complex,
    '-map', '[v]', '-map', '3:a:0', '-t', str(duration),
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(video)
])
print(video)
