import json
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'

with CONTENT.open(encoding='utf-8') as f:
    data = json.load(f)

checks = [
    ('background_url', 'background_source_url', 'video'),
    ('music_url', 'music_source_url', 'audio'),
]

for url_key, source_key, kind in checks:
    url = str(data.get(url_key, '')).strip()
    if not url.startswith(('https://', 'http://')):
        raise SystemExit(f'Media preflight failed: invalid {url_key}: {url}')

    cmd = [
        'curl', '-L', '--fail-with-body', '--silent', '--show-error',
        '--connect-timeout', '15', '--max-time', '30', '--range', '0-65535',
        '-A', 'Mozilla/5.0', '-o', '/tmp/media-preflight.bin', '-w', '%{http_code} %{content_type}',
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f'Media preflight failed for {url_key}: {result.stderr.strip()}')
    output = (result.stdout or '').strip()
    parts = output.split(' ', 1)
    code = parts[0] if parts else ''
    ctype = parts[1].lower() if len(parts) > 1 else ''
    if not code.startswith('2'):
        raise SystemExit(f'Media preflight failed for {url_key}: HTTP {code}')
    if 'text/html' in ctype:
        raise SystemExit(f'Media preflight failed for {url_key}: returned HTML instead of {kind} media')
    print(f'{url_key} preflight OK: HTTP {code}, {ctype or "unknown content-type"}')
