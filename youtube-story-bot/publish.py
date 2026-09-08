import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from schedule_utils import scheduled_publish_at_from_selection
from workflow_common import content_id

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'
OUT = BASE / 'output'
QUEUE_SELECTION = OUT / 'queue_selection.json'
OUT.mkdir(exist_ok=True)

with CONTENT.open(encoding='utf-8') as f:
    data = json.load(f)

result = subprocess.run(
    ['python', str(BASE / 'upload.py')],
    capture_output=True,
    text=True,
    env=os.environ.copy(),
)

if result.stdout:
    print(result.stdout, end='')
if result.stderr:
    print(result.stderr, end='')
if result.returncode != 0:
    raise SystemExit(result.returncode)

match = re.search(r'Uploaded video ID:\s*([A-Za-z0-9_-]+)', result.stdout or '')
if not match:
    raise SystemExit('Upload completed without a parseable YouTube video ID; refusing to archive.')

video_id = match.group(1)
record = {
    'youtube_video_id': video_id,
    'youtube_url': f'https://www.youtube.com/watch?v={video_id}',
    'content_id': content_id(data),
    'commit_sha': os.getenv('SOURCE_COMMIT_SHA', '').strip() or os.getenv('GITHUB_SHA', ''),
    'workflow_run_id': os.getenv('GITHUB_RUN_ID', ''),
    'uploaded_at': datetime.now(timezone.utc).isoformat(),
}

schedule_mode = os.getenv('YOUTUBE_SCHEDULED_UPLOAD', '').strip().lower() in {'1', 'true', 'yes'}
if schedule_mode:
    record['scheduled_publish_at'] = scheduled_publish_at_from_selection(QUEUE_SELECTION)
    record['youtube_privacy_at_upload'] = 'private'

(OUT / 'upload_result.json').write_text(
    json.dumps(record, ensure_ascii=False, indent=2) + '\n',
    encoding='utf-8',
)
print('Upload metadata saved:', json.dumps(record, ensure_ascii=False))
