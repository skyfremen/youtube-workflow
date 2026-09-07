import json
import re
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
VIDEO = BASE / 'output' / 'short.mp4'

if not VIDEO.exists():
    raise SystemExit('Render verification failed: output/short.mp4 does not exist.')
if VIDEO.stat().st_size < 100_000:
    raise SystemExit(f'Render verification failed: short.mp4 is suspiciously small ({VIDEO.stat().st_size} bytes).')

probe = subprocess.run([
    'ffprobe', '-v', 'error', '-show_entries',
    'format=duration,size:stream=codec_type,codec_name,width,height', '-of', 'json', str(VIDEO)
], capture_output=True, text=True)

if probe.returncode != 0:
    raise SystemExit('Render verification failed: ffprobe could not read short.mp4.\n' + probe.stderr)

info = json.loads(probe.stdout or '{}')
streams = info.get('streams', [])
stream_types = {stream.get('codec_type') for stream in streams}

if 'video' not in stream_types:
    raise SystemExit('Render verification failed: no video stream found.')
if 'audio' not in stream_types:
    raise SystemExit(
        'Render verification failed: no audio stream found. Background music is mandatory; '
        'do not publish a silent Short. Replace the music asset and retry.'
    )

video_stream = next((s for s in streams if s.get('codec_type') == 'video'), {})
width = int(video_stream.get('width') or 0)
height = int(video_stream.get('height') or 0)
if (width, height) != (1080, 1920):
    raise SystemExit(f'Render verification failed: expected 1080x1920, got {width}x{height}.')

try:
    duration = float(info.get('format', {}).get('duration', 0))
except (TypeError, ValueError):
    duration = 0

if not 10 <= duration <= 15.5:
    raise SystemExit(f'Render verification failed: duration {duration:.2f}s is outside the 10–15s target.')

# Decode multiple points so a corrupt or empty middle section cannot slip through.
for fraction in (0.25, 0.50, 0.75):
    timestamp = max(0.1, duration * fraction)
    frame_check = subprocess.run([
        'ffmpeg', '-v', 'error', '-ss', f'{timestamp:.3f}', '-i', str(VIDEO),
        '-frames:v', '1', '-f', 'null', '-'
    ], capture_output=True, text=True)
    if frame_check.returncode != 0:
        raise SystemExit(
            f'Render verification failed: ffmpeg could not decode frame at {timestamp:.2f}s.\n'
            + (frame_check.stderr or '')
        )

# Scan the complete video for sustained near-black sections. blackdetect logs at info level,
# so using -v error here would silently disable the useful detection output.
black_scan = subprocess.run([
    'ffmpeg', '-hide_banner', '-v', 'info', '-i', str(VIDEO),
    '-vf', 'blackdetect=d=0.50:pic_th=0.98:pix_th=0.10',
    '-an', '-f', 'null', '-'
], capture_output=True, text=True)
if black_scan.returncode != 0:
    raise SystemExit('Render verification failed: ffmpeg black-frame scan failed.\n' + (black_scan.stderr or ''))

black_durations = [
    float(value)
    for value in re.findall(r'black_duration:([0-9]+(?:\.[0-9]+)?)', black_scan.stderr or '')
]
longest_black = max(black_durations, default=0.0)
if longest_black >= 0.75:
    raise SystemExit(
        f'Render verification failed: detected a sustained near-black section of {longest_black:.2f}s.'
    )

print(
    f'Render verified: {duration:.2f}s, 1080x1920, video + audio, '
    f'3 sampled frames decodable, longest near-black section {longest_black:.2f}s.'
)
