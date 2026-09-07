import json
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

frame_check = subprocess.run([
    'ffmpeg', '-v', 'error', '-ss', '6', '-i', str(VIDEO), '-frames:v', '1',
    '-vf', 'blackframe=amount=98:threshold=16', '-f', 'null', '-'
], capture_output=True, text=True)
if frame_check.returncode != 0:
    raise SystemExit('Render verification failed: ffmpeg could not decode a midpoint frame.')
if 'pblack:100' in (frame_check.stderr or ''):
    raise SystemExit('Render verification failed: midpoint frame appears fully black.')

print(f'Render verified: {duration:.2f}s, 1080x1920, video + audio, decodable midpoint frame.')
