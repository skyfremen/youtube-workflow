import json
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'
TMP = Path('/tmp/media-preflight.bin')


def preflight(url, kind):
    if not str(url).startswith(('https://', 'http://')):
        return False, f'invalid URL: {url}'
    cmd = [
        'curl', '-L', '--fail-with-body', '--silent', '--show-error',
        '--connect-timeout', '15', '--max-time', '30', '--range', '0-65535',
        '-A', 'Mozilla/5.0', '-o', str(TMP), '-w', '%{http_code} %{content_type}',
        str(url),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or 'curl failed').strip()
    output = (result.stdout or '').strip()
    parts = output.split(' ', 1)
    code = parts[0] if parts else ''
    ctype = parts[1].lower() if len(parts) > 1 else ''
    if not code.startswith('2'):
        return False, f'HTTP {code}'
    if 'text/html' in ctype:
        return False, f'returned HTML instead of {kind} media'
    return True, f'HTTP {code}, {ctype or "unknown content-type"}'


def activate_backup(data, prefix):
    mapping = {
        'background': ('url', 'source_url', 'creator', 'license', 'credit'),
        'music': ('url', 'source_url', 'title', 'artist', 'license', 'credit'),
    }
    for suffix in mapping[prefix]:
        backup_key = f'{prefix}_backup_{suffix}'
        primary_key = f'{prefix}_{suffix}'
        if backup_key in data:
            data[primary_key] = data[backup_key]
    data[f'{prefix}_used_backup'] = True


def check_component(data, prefix, kind):
    primary_url = str(data.get(f'{prefix}_url', '')).strip()
    ok, detail = preflight(primary_url, kind)
    if ok:
        print(f'{prefix} primary preflight OK: {detail}')
        return

    print(f'::warning::{prefix} primary media failed preflight: {detail}')
    backup_url = str(data.get(f'{prefix}_backup_url', '')).strip()
    if not backup_url:
        raise SystemExit(f'{prefix} primary failed and no backup URL is available.')

    ok, backup_detail = preflight(backup_url, kind)
    if not ok:
        raise SystemExit(
            f'{prefix} primary failed ({detail}) and backup failed ({backup_detail}).'
        )

    activate_backup(data, prefix)
    print(f'::warning::{prefix} switched to backup media: {backup_detail}')


with CONTENT.open(encoding='utf-8') as f:
    data = json.load(f)

check_component(data, 'background', 'video')
check_component(data, 'music', 'audio')
CONTENT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
