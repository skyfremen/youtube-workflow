import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from workflow_common import content_id

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'
UPLOAD_RESULT = BASE / 'output' / 'upload_result.json'
ARCHIVE_DIR = BASE / 'content' / 'archive'
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

with CONTENT.open(encoding='utf-8') as f:
    data = json.load(f)
with UPLOAD_RESULT.open(encoding='utf-8') as f:
    upload = json.load(f)

video_id = str(upload.get('youtube_video_id', '')).strip()
if not video_id:
    raise SystemExit('Finalize failed: upload_result.json has no YouTube video ID.')

sg_date = datetime.now(ZoneInfo('Asia/Singapore')).date().isoformat()
archive_path = ARCHIVE_DIR / f'{sg_date}.json'

if archive_path.exists():
    existing = json.loads(archive_path.read_text(encoding='utf-8'))
else:
    existing = {'date': sg_date, 'count': 0, 'shorts': []}

if isinstance(existing, dict) and isinstance(existing.get('shorts'), list):
    shorts = existing['shorts']
elif isinstance(existing, dict):
    legacy = dict(existing)
    legacy.pop('date', None)
    legacy.pop('count', None)
    shorts = [legacy] if legacy else []
else:
    raise SystemExit(f'Finalize failed: unsupported archive format in {archive_path.name}.')

cid = str(upload.get('content_id', '')).strip() or content_id(data)
commit_sha = str(upload.get('commit_sha', '')).strip()

for item in shorts:
    if not isinstance(item, dict):
        continue
    if str(item.get('youtube_video_id', '')).strip() == video_id:
        print(f'Archive already contains YouTube video {video_id}; no duplicate append needed.')
        break
    if (
        str(item.get('content_id', '')).strip() == cid
        and str(item.get('commit_sha', '')).strip() == commit_sha
        and commit_sha
    ):
        print(f'Archive already contains content_id={cid} for commit {commit_sha}; no duplicate append needed.')
        break
else:
    record = dict(data)
    record.pop('force_reupload', None)
    record.update({
        'content_id': cid,
        'youtube_video_id': video_id,
        'youtube_url': upload.get('youtube_url', f'https://www.youtube.com/watch?v={video_id}'),
        'commit_sha': commit_sha,
        'workflow_run_id': str(upload.get('workflow_run_id', '')).strip(),
        'uploaded_at': upload.get('uploaded_at', ''),
    })
    shorts.append(record)
    print(f'Archived YouTube video {video_id} with content_id={cid}.')

payload = {
    'date': sg_date,
    'count': len(shorts),
    'shorts': shorts,
}
archive_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if payload['count'] != len(payload['shorts']):
    raise SystemExit('Finalize failed: archive count does not match shorts length.')

print(f'Archive verified: {archive_path.name}, count={payload["count"]}.')
