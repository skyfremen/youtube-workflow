import hashlib
import json
from pathlib import Path

FINGERPRINT_FIELDS = ('topic', 'category', 'setup', 'payoff')


def content_id(data):
    """Stable identity for the joke itself, independent of media or metadata."""
    payload = {key: str(data.get(key, '')).strip() for key in FINGERPRINT_FIELDS}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:20]


def archive_records(archive_dir):
    """Yield records from both legacy single-object and current daily archives."""
    archive_dir = Path(archive_dir)
    if not archive_dir.exists():
        return
    for path in sorted(archive_dir.glob('*.json')):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(payload, dict) and isinstance(payload.get('shorts'), list):
            for record in payload['shorts']:
                if isinstance(record, dict):
                    yield path, record
        elif isinstance(payload, dict):
            yield path, payload
