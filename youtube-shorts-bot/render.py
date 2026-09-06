import json, subprocess
from pathlib import Path

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'
OUT = BASE / 'output'
ASSETS = BASE / 'assets'
OUT.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)

with CONTENT.open(encoding='utf-8') as f:
    data = json.load(f)

category = data.get('category', 'TECH').upper()
setup = data.get('setup') or data.get('hook') or data.get('script', '')
payoff = data.get('payoff') or data.get('script', '')
cta = data.get('cta', 'DOUBLE TAP TO AGREE').upper()
handle = data.get('handle', '@SKYFREMEN').upper()

# Short, punchy narration: setup then reveal.
spoken = f"{setup} {payoff}".strip()
voice_wav = OUT / 'voice.wav'
subprocess.run(['espeak-ng', '-s', '180', '-w', str(voice_wav), spoken], check=True)

probe = subprocess.check_output([
    'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
    '-of', 'default=nw=1:nk=1', str(voice_wav)
], text=True).strip()
duration = max(float(probe), 9.0)
reveal_at = max(duration * 0.48, 4.0)


def ass_escape(text):
    return str(text).replace('\\', r'\\').replace('{', r'\{').replace('}', r'\}')


def wrap(text, width):
    words = str(text).upper().split()
    lines, current = [], []
    for word in words:
        candidate = ' '.join(current + [word])
        if len(candidate) > width and current:
            lines.append(' '.join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(' '.join(current))
    return r'\N'.join(lines)


def ass_time(seconds):
    cs = int(round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f'{h}:{m:02}:{s:02}.{cs:02}'

ass = OUT / 'overlay.ass'
header = f'DID YOU KNOW?\\N{category} FACT'
setup_text = wrap(setup, 24)
payoff_text = wrap(payoff, 24)

ass.write_text(f'''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Header,DejaVu Sans,82,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,7,0,8,70,70,220,1
Style: Main,DejaVu Sans,72,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,2,0,1,5,2,5,80,80,0,1
Style: CTA,DejaVu Sans,42,&H0000D7FF,&H0000D7FF,&H00101010,&H00000000,-1,0,0,0,100,100,1,0,1,4,1,8,80,80,525,1
Style: Handle,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,3,5,0,2,110,110,300,1
Style: Subscribe,DejaVu Sans,42,&H0000D7FF,&H0000D7FF,&H00101010,&H00000000,-1,0,0,0,100,100,1,0,1,4,1,2,110,110,235,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,{ass_time(duration)},Header,,0,0,0,,{ass_escape(header)}
Dialogue: 0,0:00:00.50,{ass_time(reveal_at)},Main,,0,0,0,,{ass_escape(setup_text)}
Dialogue: 0,{ass_time(reveal_at)},{ass_time(duration)},Main,,0,0,0,,{ass_escape(payoff_text)}
Dialogue: 0,{ass_time(reveal_at)},{ass_time(duration)},CTA,,0,0,0,,{ass_escape(cta)}
Dialogue: 0,0:00:00.00,{ass_time(duration)},Handle,,0,0,0,,{ass_escape(handle)}
Dialogue: 0,{ass_time(reveal_at)},{ass_time(duration)},Subscribe,,0,0,0,,SUBSCRIBE
''', encoding='utf-8')

video = OUT / 'short.mp4'
background = ASSETS / 'background.mp4'

if background.exists():
    # Loop a user-provided royalty-free vertical/horizontal background clip.
    input_args = ['-stream_loop', '-1', '-i', str(background)]
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,eq=brightness=-0.14:saturation=0.8,"
        f"subtitles='{ass.as_posix()}'"
    )
else:
    # $0 fallback: moving abstract background generated entirely by FFmpeg.
    input_args = ['-f', 'lavfi', '-i', f"testsrc2=s=1080x1920:r=30:d={duration}"]
    vf = (
        "boxblur=18:8,eq=brightness=-0.30:saturation=0.55,"
        f"subtitles='{ass.as_posix()}'"
    )

subprocess.run([
    'ffmpeg', '-y', *input_args,
    '-i', str(voice_wav),
    '-vf', vf,
    '-t', str(duration),
    '-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k', '-shortest', str(video)
], check=True)

print(video)
