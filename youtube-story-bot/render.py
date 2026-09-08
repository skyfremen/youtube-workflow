import json, math, re, subprocess, urllib.parse
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from kokoro import KPipeline

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)

data = json.loads(CONTENT.read_text(encoding='utf-8'))
duration = float(data.get('duration_seconds', 45.0))
channel_name = str(data.get('channel_name', 'Wacky Dramas'))
handle = str(data.get('handle', '@WACKYDRAMAS')).upper()
hook = str(data['hook'])
story = str(data['story'])
story_type = str(data.get('story_type', 'STORY')).upper()
voice = str(data.get('tts_voice', 'af_heart'))
speed = float(data.get('tts_speed', 1.1))


def run(cmd):
    subprocess.run(cmd, check=True)


def download(url, target, source_url=None):
    cmd = ['curl','-L','--fail','--silent','--show-error','--retry','3','--connect-timeout','20','--max-time','120','-A','Mozilla/5.0','-o',str(target)]
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
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(' '.join(words[i:i+max_words]))
    return chunks

# Kokoro TTS
pipeline = KPipeline(lang_code='a')
audio_parts = []
for _gs, _ps, audio in pipeline(story, voice=voice, speed=speed):
    audio_parts.append(np.asarray(audio, dtype=np.float32))
if not audio_parts:
    raise SystemExit('Kokoro produced no audio')
audio = np.concatenate(audio_parts)
# Hard-cap to requested Short duration; pad only if narration is shorter.
target_samples = int(duration * 24000)
if len(audio) < target_samples:
    audio = np.pad(audio, (0, target_samples - len(audio)))
else:
    audio = audio[:target_samples]
narration = OUT / 'narration.wav'
sf.write(narration, audio, 24000)

# Branded story card. Uses WD initials as a deterministic fallback avatar.
W, H = 1080, 1920
card = Image.new('RGBA', (W, H), (0,0,0,0))
d = ImageDraw.Draw(card)
font_bold = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
font_reg = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
d.rounded_rectangle((65,150,1015,620), radius=34, fill=(250,250,250,246), outline=(15,15,15,240), width=6)
d.ellipse((100,195,225,320), fill=(18,18,22,255), outline=(230,55,45,255), width=7)
f_avatar = ImageFont.truetype(font_bold, 46)
d.text((126,229), 'WD', font=f_avatar, fill=(255,255,255,255))
f_name = ImageFont.truetype(font_bold, 48)
f_type = ImageFont.truetype(font_reg, 28)
f_hook = ImageFont.truetype(font_bold, 58)
d.text((255,200), channel_name, font=f_name, fill=(15,15,15,255))
d.text((255,268), story_type, font=f_type, fill=(95,95,95,255))
# simple hook wrapping
words = hook.split(); lines=[]; cur=''
for word in words:
    trial = (cur + ' ' + word).strip()
    if len(trial) > 29 and cur:
        lines.append(cur); cur = word
    else: cur = trial
if cur: lines.append(cur)
d.multiline_text((105,365), '\n'.join(lines[:3]), font=f_hook, fill=(10,10,10,255), spacing=8)
card_path = OUT / 'story-card.png'
card.save(card_path)

# Phrase-following subtitles, proportionally timed to spoken word count.
chunks = phrase_chunks(story, 5)
weights = [max(1, len(c.split())) for c in chunks]
total = sum(weights)
t = 0.15
events=[]
for c,w in zip(chunks,weights):
    seg = max(0.35, (duration - 0.3) * w / total)
    end = min(duration - 0.05, t + seg)
    events.append(f'Dialogue: 0,{ass_time(t)},{ass_time(end)},Main,,0,0,0,,{escape_ass(c.upper())}')
    t = end

ass = OUT / 'captions.ass'
ass.write_text(f'''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Main,DejaVu Sans,68,&H00FFFFFF,&H00FFFFFF,&H00101010,&H40000000,-1,0,0,0,100,100,0,0,1,6,2,5,110,110,0,1\nStyle: Handle,DejaVu Sans,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,-1,0,0,0,100,100,1,0,3,4,0,2,100,100,115,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n''' + '\n'.join(events) + f'\nDialogue: 2,0:00:00.00,{ass_time(duration)},Handle,,0,0,0,,{escape_ass(handle)}\n', encoding='utf-8')

background = OUT / 'background.asset'
download(data['background_url'], background, data.get('background_source_url'))
video = OUT / 'short.mp4'
frames = max(1, math.ceil(duration * 30))
filter_complex = (
    f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
    f"eq=brightness=-0.08:saturation=0.9,zoompan=z='min(zoom+0.00025,1.06)':"
    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30[bg];"
    f"[bg][1:v]overlay=0:0[tmp];[tmp]subtitles='{ass.as_posix()}'[v]"
)
run(['ffmpeg','-y','-stream_loop','-1','-i',str(background),'-loop','1','-i',str(card_path),'-i',str(narration),
     '-filter_complex',filter_complex,'-map','[v]','-map','2:a:0','-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','21',
     '-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(video)])
print(video)
