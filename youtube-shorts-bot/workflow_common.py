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


def recoverable_archive_match(archive_dir, selection_path, current_content):
    """Return an exact archived upload only for a still-pending selected queue item.

    This is intentionally narrow. It repairs the failure window where YouTube upload
    and archive persistence succeeded but the queue item remained pending. It must
    never turn a normal duplicate into a reusable upload.
    """
    selection_path = Path(selection_path)
    if not selection_path.exists():
        return None

    try:
        selection = json.loads(selection_path.read_text(encoding='utf-8'))
        raw_plan_path = str(selection.get('plan_path', '')).strip()
        item_index = int(selection.get('item_index'))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None

    if not raw_plan_path:
        return None
    plan_path = Path(raw_plan_path)
    if not plan_path.is_absolute():
        plan_path = Path.cwd() / plan_path

    try:
        plan = json.loads(plan_path.read_text(encoding='utf-8'))
        item = plan['items'][item_index]
    except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None

    if not isinstance(item, dict) or item.get('status', 'pending') != 'pending':
        return None
    selected_content = item.get('content')
    if not isinstance(selected_content, dict):
        return None

    current_cid = content_id(current_content)
    if content_id(selected_content) != current_cid:
        return None

    matches = []
    for path, record in archive_records(archive_dir):
        archived_cid = str(record.get('content_id', '')).strip() or content_id(record)
        video_id = str(record.get('youtube_video_id', '')).strip()
        if archived_cid == current_cid and video_id:
            matches.append((path, record))

    if len(matches) != 1:
        return None
    return matches[0]
