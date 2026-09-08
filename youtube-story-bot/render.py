import json, math, subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFile, ImageStat
from kokoro import KPipeline

ImageFile.LOAD_TRUNCATED_IMAGES = True

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'
OUT = BASE / 'output'
ASSETS = BASE / 'assets'
UI_ASSETS = ASSETS / 'ui'
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
EMOJI_FONT_CANDIDATES = [
    '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',
    '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf',
]


def pick_existing(paths):
    for p in paths:
        if Path(p).exists():
            return p
    return None


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


def phrase_chunks(text, max_words=3):
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
    for size in range(64, 43, -2):
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


def load_ui_icon(name, target_size):
    path = UI_ASSETS / name
    if not path.exists():
        raise SystemExit(f'Missing required UI asset: {path}')
    try:
        with Image.open(path) as source:
            source.load()
            icon = source.convert('RGBA').copy()
    except (OSError, ValueError) as exc:
        raise SystemExit(f'Invalid UI asset {path}: {exc}')
    bbox = icon.getchannel('A').getbbox()
    if not bbox:
        raise SystemExit(f'UI asset has no visible pixels: {path}')
    icon = icon.crop(bbox)
    return ImageOps.contain(icon, (target_size, target_size), method=Image.Resampling.LANCZOS)


def paste_icon_centered(canvas, icon, x, center_y):
    y = int(round(center_y - icon.height / 2))
    canvas.alpha_composite(icon, (int(x), y))
    return int(x + icon.width)


def draw_text_centered_y(draw, x, center_y, text, font, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    y = center_y - (bb[3] - bb[1]) / 2 - bb[1]
    draw.text((x, y), text, font=font, fill=fill)
    return bb[2] - bb[0]


def render_emoji(icon, target_size=54):
    emoji_font_path = pick_existing(EMOJI_FONT_CANDIDATES)
    if emoji_font_path:
        try:
            font = ImageFont.truetype(emoji_font_path, 109)
            tile = Image.new('RGBA', (150, 150), (0, 0, 0, 0))
            draw = ImageDraw.Draw(tile)
            bb = draw.textbbox((0, 0), icon, font=font, embedded_color=True)
            x = (150 - (bb[2] - bb[0])) / 2 - bb[0]
            y = (150 - (bb[3] - bb[1])) / 2 - bb[1]
            draw.text((x, y), icon, font=font, embedded_color=True)
            bbox = tile.getbbox()
            if bbox:
                tile = tile.crop(bbox)
            return ImageOps.contain(tile, (target_size, target_size), method=Image.Resampling.LANCZOS)
        except (OSError, ValueError):
            pass

    fallback_map = {'💼':'B','🏠':'H','💔':'♥','🔥':'F','☕':'C','😱':'!'}
    tile = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    font = ImageFont.truetype(FONT_BOLD, int(target_size * 0.72))
    centered_text(draw, (0, 0, target_size, target_size), fallback_map.get(icon, '•'), font, (28,28,28,255))
    return tile


pipeline = KPipeline(lang_code='a')
audio_parts = []
tts_segments = []
for gs, _ps, segment_audio in pipeline(story, voice=voice, speed=speed):
    part = np.asarray(segment_audio, dtype=np.float32)
    if part.size == 0:
        continue
    audio_parts.append(part)
    segment_text = str(gs).strip() if gs is not None else ''
    tts_segments.append((segment_text, len(part)))
if not audio_parts:
    raise SystemExit('Kokoro produced no audio')

speech_audio = np.concatenate(audio_parts)
speech_samples = len(speech_audio)
speech_duration = min(duration, speech_samples / 24000.0)
target_samples = int(duration * 24000)
if speech_samples < target_samples:
    audio = np.pad(speech_audio, (0, target_samples - speech_samples))
else:
    audio = speech_audio[:target_samples]
narration = OUT / 'narration.wav'
sf.write(narration, audio, 24000)

card_overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
branding_overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
d_card = ImageDraw.Draw(card_overlay)
d_brand = ImageDraw.Draw(branding_overlay)

card_box = (56, 235, 1024, 805)
for off, alpha in [(10,55),(18,25)]:
    d_card.rounded_rectangle((card_box[0]+off,card_box[1]+off,card_box[2]+off,card_box[3]+off), radius=36, fill=(0,0,0,alpha))
d_card.rounded_rectangle(card_box, radius=36, fill=(251,251,251,252), outline=(28,28,28,255), width=5)

logo_path = ASSETS / 'channel-avatar.png'
if not logo_path.exists():
    raise SystemExit('Missing required asset: youtube-story-bot/assets/channel-avatar.png')
try:
    with Image.open(logo_path) as source_logo:
        source_logo.load()
        logo = source_logo.convert('RGBA').copy()
    rgb = logo.convert('RGB')
    stat = ImageStat.Stat(rgb)
    mean_rgb = stat.mean
    extrema = rgb.getextrema()
    dynamic_range = sum(hi - lo for lo, hi in extrema)
    if max(mean_rgb) < 18 or dynamic_range < 90:
        raise ValueError(f'channel-avatar.png appears blank/corrupt: mean={mean_rgb}, extrema={extrema}')
    avatar_size = 132
    avatar_square = logo.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
    mask = Image.new('L', (avatar_size, avatar_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, avatar_size - 1, avatar_size - 1), fill=255)
    clipped = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
    clipped.paste(avatar_square, (0, 0), mask)
    card_overlay.alpha_composite(clipped, (82, 290))
except (OSError, ValueError) as exc:
    raise SystemExit(f'Invalid channel avatar: {exc}')

name_x,name_y=235,285
f_name=ImageFont.truetype(FONT_BOLD,40)
d_card.text((name_x,name_y),channel_name,font=f_name,fill=(18,18,18,255))
name_bb=d_card.textbbox((name_x,name_y),channel_name,font=f_name)
verified_icon = load_ui_icon('verified-blue.png', 38)
verified_x = int(name_bb[2] + 18)
verified_y = int(name_y + 4)
card_overlay.alpha_composite(verified_icon, (verified_x, verified_y))

emoji_icons=['💼','🏠','💔','🔥','☕','😱']
icon_y=350
ix=name_x
for icon in emoji_icons:
    emoji_img=render_emoji(icon,target_size=54)
    x=int(ix+(58-emoji_img.width)/2)
    y=int(icon_y+(58-emoji_img.height)/2)
    card_overlay.alpha_composite(emoji_img,(x,y))
    ix+=66

hook_x,hook_y=86,455
hook_width,hook_height=900,220
hook_font,hook_lines,line_height=fit_hook(d_card,hook,hook_width,hook_height)
for i,line in enumerate(hook_lines):
    d_card.text((hook_x,hook_y+i*line_height),line,font=hook_font,fill=(8,8,8,255))

foot_center_y = 742
light=(110,110,110,255)
f_meta=ImageFont.truetype(FONT_REG,30)
like_icon = load_ui_icon('like.png', 30)
comment_icon = load_ui_icon('comment.png', 31)
share_icon = load_ui_icon('share.png', 29)

like_end = paste_icon_centered(card_overlay, like_icon, 82, foot_center_y)
draw_text_centered_y(d_card, like_end + 10, foot_center_y, '99+', f_meta, light)

comment_end = paste_icon_centered(card_overlay, comment_icon, 214, foot_center_y)
draw_text_centered_y(d_card, comment_end + 10, foot_center_y, '99+', f_meta, light)

share_end = paste_icon_centered(card_overlay, share_icon, 868, foot_center_y)
draw_text_centered_y(d_card, share_end + 10, foot_center_y, 'Share', f_meta, light)


def pill(draw_obj,box,text,font,fill):
    draw_obj.rounded_rectangle(box,radius=(box[3]-box[1])//2,fill=(0,0,0,225),outline=(255,255,255,70),width=2)
    centered_text(draw_obj,box,text,font,fill)


pill(d_brand,(285,1260,795,1334),handle,ImageFont.truetype(FONT_BOLD,42),(255,255,255,255))
pill(d_brand,(360,1348,720,1418),'SUBSCRIBE',ImageFont.truetype(FONT_BOLD,38),(255,214,40,255))

card_overlay_path=OUT/'story-card.png'
branding_overlay_path=OUT/'branding.png'
card_overlay.save(card_overlay_path)
branding_overlay.save(branding_overlay_path)

events=[]
cursor = 0.0
usable_segments = [(text, samples) for text, samples in tts_segments if text and samples > 0]
segment_words = sum(len(text.split()) for text, _ in usable_segments)
story_words = len(story.split())
use_segment_text = bool(usable_segments) and segment_words >= max(1, int(story_words * 0.75))

if use_segment_text:
    for segment_text, samples in usable_segments:
        seg_start = cursor
        seg_duration = min(samples / 24000.0, max(0.0, speech_duration - seg_start))
        if seg_duration <= 0:
            break
        chunks = phrase_chunks(segment_text, 3)
        weights = [max(1, sum(len(w.strip('.,!?;:"()[]{}')) for w in c.split())) for c in chunks]
        total_weight = max(1, sum(weights))
        local = seg_start
        for i, (chunk, weight) in enumerate(zip(chunks, weights)):
            if i == len(chunks) - 1:
                end = min(speech_duration, seg_start + seg_duration)
            else:
                end = min(speech_duration, local + seg_duration * weight / total_weight)
            if end > local + 0.03:
                events.append(f'Dialogue: 0,{ass_time(local)},{ass_time(end)},Main,,0,0,0,,{escape_ass(chunk.upper())}')
            local = end
        cursor = min(speech_duration, seg_start + seg_duration)
else:
    chunks = phrase_chunks(story, 3)
    weights = [max(1, sum(len(w.strip('.,!?;:"()[]{}')) for w in c.split())) for c in chunks]
    total_weight = max(1, sum(weights))
    cursor = 0.0
    for i, (chunk, weight) in enumerate(zip(chunks, weights)):
        if i == len(chunks) - 1:
            end = speech_duration
        else:
            end = min(speech_duration, cursor + speech_duration * weight / total_weight)
        if end > cursor + 0.03:
            events.append(f'Dialogue: 0,{ass_time(cursor)},{ass_time(end)},Main,,0,0,0,,{escape_ass(chunk.upper())}')
        cursor = end

ass=OUT/'captions.ass'
ass_header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Main,DejaVu Sans,78,&H00FFFFFF,&H00FFFFFF,&H00101010,&H35000000,-1,0,0,0,100,100,0,0,1,7,2,5,260,260,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
ass.write_text(ass_header + '\n'.join(events) + '\n', encoding='utf-8')

background=OUT/'background.asset'
download(data['background_url'],background,data.get('background_source_url'))
video=OUT/'short.mp4'
filter_complex=("[0:v]fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=brightness=-0.03:saturation=1.03[bg];" "[1:v]format=rgba,fade=t=out:st=1.70:d=0.30:alpha=1[card];" "[2:v]format=rgba[brand];" "[bg][card]overlay=x=0:y='-6*sin(PI*t/2)'[tmp1];" "[tmp1][brand]overlay=0:0[tmp2];" f"[tmp2]subtitles='{ass.as_posix()}'[v]")
run(['ffmpeg','-y','-stream_loop','-1','-i',str(background),'-loop','1','-i',str(card_overlay_path),'-loop','1','-i',str(branding_overlay_path),'-i',str(narration),'-filter_complex',filter_complex,'-map','[v]','-map','3:a:0','-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(video)])
print(video)
