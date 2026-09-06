import json
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
VIDEO = BASE / 'output' / 'short.mp4'

if not VIDEO.exists():
    raise SystemExit('Render verification failed: output/short.mp4 does not exist.')

probe = subprocess.run([
    'ffprobe', '-v', 'error', '-show_entries',
    'format=duration:stream=codec_type', '-of', 'json', str(VIDEO)
], capture_output=True, text=True)

if probe.returncode != 0:
    raise SystemExit('Render verification failed: ffprobe could not read short.mp4.\n' + probe.stderr)

info = json.loads(probe.stdout or '{}')
stream_types = {stream.get('codec_type') for stream in info.get('streams', [])}

if 'video' not in stream_types:
    raise SystemExit('Render verification failed: no video stream found.')
if 'audio' not in stream_types:
    raise SystemExit(
        'Render verification failed: no audio stream found. Background music is mandatory; '
        'do not publish a silent Short. Replace the music asset and retry.'
    )

try:
    duration = float(info.get('format', {}).get('duration', 0))
except (TypeError, ValueError):
    duration = 0

if not 10 <= duration <= 15.5:
    raise SystemExit(f'Render verification failed: duration {duration:.2f}s is outside the 10–15s target.')

print(f'Render verified: {duration:.2f}s with video + audio streams.')
