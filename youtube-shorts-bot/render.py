import json, subprocess, urllib.parse
from pathlib import Path

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)

with CONTENT.open(encoding='utf-8') as f:
    data = json.load(f)

required = [
    'category', 'setup', 'payoff', 'title',
    'background_url', 'music_url'
]
missing = [k for k in required if not data.get(k)]
if missing:
    raise SystemExit(f"No active Short content. Missing: {', '.join(missing)}")

category = data['category'].upper()
setup = data['setup']
payoff = data['payoff']
cta = data.get('cta', 'DOUBLE TAP TO AGREE').upper()
handle = '@WACKYINSIGHTS'
background_url = data['background_url']
music_url = data['music_url']

# Fixed meme-short pacing: no TTS, music only.
duration = 12.0
reveal_at = 6.0


def ass_escape_text(text):
    """Escape user text only. Do not escape ASS control sequences such as \\N."""
    return (
        str(text)
        .replace('\\', r'\\')
        .replace('{', r'\{')
        .replace('}', r'\}')
    )


def wrap(text, width=18):
    """Wrap text before inserting ASS newline codes so \\N remains functional."""
    words = ass_escape_text(str(text).upper()).split()
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


def download(url, target, source_url=None):
    """Download media with browser-like headers, redirects, and retries.

    Some royalty-free media hosts reject minimal urllib requests from CI runners.
    curl is used here because it handles redirects/retries reliably and lets us
    send the same basic headers a normal browser download would include.
    """
    if not str(url).startswith(('https://', 'http://')):
        raise SystemExit(f'Invalid media URL: {url}')

    cmd = [
        'curl', '-L', '--fail-with-body', '--silent', '--show-error',
        '--retry', '3', '--retry-delay', '2', '--retry-all-errors',
        '--connect-timeout', '20', '--max-time', '120',
        '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        '-H', 'Accept: */*',
        '-H', 'Accept-Language: en-US,en;q=0.9',
        '-o', str(target),
    ]

    if source_url and str(source_url).startswith(('https://', 'http://')):
        cmd += ['-e', str(source_url)]
    else:
        parsed = urllib.parse.urlsplit(str(url))
        if parsed.scheme and parsed.netloc:
            cmd += ['-H', f'Origin: {parsed.scheme}://{parsed.netloc}']

    cmd.append(str(url))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or 'unknown download error').strip()
        raise SystemExit(
            f'Failed to download media after retries: {url}\n'
            f'curl exit code {result.returncode}: {detail}\n'
            'Use a direct downloadable media URL that permits automated access from CI.'
        )

    if not target.exists() or target.stat().st_size < 10_000:
        size = target.stat().st_size if target.exists() else 0
        raise SystemExit(
            f'Downloaded media is suspiciously small ({size} bytes): {url}. '
            'The URL may have returned an HTML/error page instead of media.'
        )


def assert_stream(path, stream_type):
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-select_streams', f'{stream_type}:0',
        '-show_entries', 'stream=codec_type', '-of', 'default=nw=1:nk=1', str(path)
    ], capture_output=True, text=True)
    expected = 'video' if stream_type == 'v' else 'audio'
    if result.returncode != 0 or expected not in result.stdout:
        probe_error = (result.stderr or '').strip()
        raise SystemExit(
            f'{path.name} is not a valid direct {expected} media file. '
            'The selector must provide a direct downloadable asset URL, not a web page.'
            + (f' ffprobe: {probe_error}' if probe_error else '')
        )

ass = OUT / 'overlay.ass'
header = f'DID YOU KNOW?\\N{ass_escape_text(category)} FACT'
setup_text = wrap(setup, 18)
payoff_text = wrap(payoff, 18)
cta_text = ass_escape_text(cta)
handle_text = ass_escape_text(handle)

ass.write_text(f'''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Header,DejaVu Sans,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,7,0,8,100,100,220,1
Style: Main,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,1,0,1,5,2,5,145,145,0,1
Style: CTA,DejaVu Sans,40,&H0000D7FF,&H0000D7FF,&H00101010,&H00000000,-1,0,0,0,100,100,1,0,1,4,1,8,130,130,525,1
Style: Handle,DejaVu Sans,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,3,5,0,2,130,130,520,1
Style: Subscribe,DejaVu Sans,40,&H0000D7FF,&H0000D7FF,&H00101010,&H00000000,-1,0,0,0,100,100,1,0,1,4,1,2,130,130,450,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,{ass_time(duration)},Header,,0,0,0,,{header}
Dialogue: 0,0:00:00.50,{ass_time(reveal_at)},Main,,0,0,0,,{setup_text}
Dialogue: 0,{ass_time(reveal_at)},{ass_time(duration)},Main,,0,0,0,,{payoff_text}
Dialogue: 0,{ass_time(reveal_at)},{ass_time(duration)},CTA,,0,0,0,,{cta_text}
Dialogue: 0,0:00:00.00,{ass_time(duration)},Handle,,0,0,0,,{handle_text}
Dialogue: 0,{ass_time(reveal_at)},{ass_time(duration)},Subscribe,,0,0,0,,SUBSCRIBE
''', encoding='utf-8')

background = OUT / 'background.asset'
music = OUT / 'music.asset'
video = OUT / 'short.mp4'

download(background_url, background, data.get('background_source_url'))
download(music_url, music, data.get('music_source_url'))
assert_stream(background, 'v')
assert_stream(music, 'a')

vf = (
    'scale=1080:1920:force_original_aspect_ratio=increase,'
    'crop=1080:1920,eq=brightness=-0.14:saturation=0.85,'
    f"subtitles='{ass.as_posix()}'"
)

subprocess.run([
    'ffmpeg', '-y', '-stream_loop', '-1', '-i', str(background),
    '-stream_loop', '-1', '-i', str(music),
    '-vf', vf,
    '-t', str(duration),
    '-map', '0:v:0', '-map', '1:a:0',
    '-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k',
    '-af', 'volume=0.28,afade=t=in:st=0:d=0.4,afade=t=out:st=11.4:d=0.6',
    '-shortest', str(video)
], check=True)

print('Background source:', data.get('background_source_url', 'not provided'))
print('Music:', data.get('music_title', 'selected track'), '-', data.get('music_artist', 'unknown artist'))
print('Music source:', data.get('music_source_url', 'not provided'))
print(video)
