import json
from pathlib import Path

from workflow_common import archive_records, content_id

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'
ARCHIVE = BASE / 'content' / 'archive'
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)

with CONTENT.open(encoding='utf-8') as f:
    data = json.load(f)

required = (
    'topic', 'category', 'setup', 'payoff', 'title',
    'background_url', 'music_url', 'music_source_url',
    'music_title', 'music_artist', 'music_license'
)
missing = [key for key in required if not str(data.get(key, '')).strip()]
if missing:
    raise SystemExit(
        'Preflight failed. Missing required field(s): ' + ', '.join(missing) +
        '. Background music is mandatory and must never fall back to silence.'
    )

cid = content_id(data)
force_reupload = data.get('force_reupload') is True

matches = []
for path, record in archive_records(ARCHIVE):
    archived_cid = str(record.get('content_id', '')).strip() or content_id(record)
    if archived_cid == cid:
        matches.append((path.name, record.get('youtube_video_id', 'unknown')))

if matches and not force_reupload:
    details = ', '.join(f'{name} / video {video_id}' for name, video_id in matches)
    raise SystemExit(
        f'Duplicate content blocked. content_id={cid} already exists in archive: {details}. '
        'For an intentional remake/re-upload, set "force_reupload": true in latest.json for that one run.'
    )

if matches and force_reupload:
    print(f'Intentional re-upload allowed by force_reupload=true for content_id={cid}.')
else:
    print(f'Content is new. content_id={cid}.')

(OUT / 'content_id.txt').write_text(cid + '\n', encoding='utf-8')
