import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from schedule_utils import scheduled_publish_at_from_selection, parse_publish_at

BASE = Path(__file__).parent
OUT = BASE / 'output'
UPLOAD_RESULT = OUT / 'upload_result.json'
QUEUE_SELECTION = OUT / 'queue_selection.json'

if not UPLOAD_RESULT.exists():
    raise SystemExit('YouTube schedule verification failed: upload_result.json is missing.')
if not QUEUE_SELECTION.exists():
    raise SystemExit('YouTube schedule verification failed: queue_selection.json is missing.')

upload = json.loads(UPLOAD_RESULT.read_text(encoding='utf-8'))
video_id = str(upload.get('youtube_video_id', '')).strip()
if not video_id:
    raise SystemExit('YouTube schedule verification failed: no video ID in upload_result.json.')

expected_publish_at = scheduled_publish_at_from_selection(QUEUE_SELECTION)
expected_dt = parse_publish_at(expected_publish_at)

creds = Credentials(
    token=None,
    refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
    token_uri='https://oauth2.googleapis.com/token',
    client_id=os.environ['YOUTUBE_CLIENT_ID'],
    client_secret=os.environ['YOUTUBE_CLIENT_SECRET'],
    scopes=[
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.readonly',
    ],
)

youtube = build('youtube', 'v3', credentials=creds, cache_discovery=False)
last_error = None
for attempt in range(1, 6):
    response = youtube.videos().list(part='status', id=video_id).execute()
    items = response.get('items', []) or []
    if not items:
        last_error = f'video {video_id} not visible through videos.list yet'
    else:
        status = items[0].get('status', {}) or {}
        upload_status = str(status.get('uploadStatus', '')).strip().lower()
        privacy = str(status.get('privacyStatus', '')).strip().lower()
        actual_publish_at = str(status.get('publishAt', '')).strip()
        failure_reason = str(status.get('failureReason', '')).strip()
        rejection_reason = str(status.get('rejectionReason', '')).strip()

        if upload_status in {'failed', 'rejected', 'deleted'} or failure_reason or rejection_reason:
            raise SystemExit(
                'YouTube schedule verification failed: '
                f'uploadStatus={upload_status or "unknown"}, '
                f'failureReason={failure_reason or "none"}, '
                f'rejectionReason={rejection_reason or "none"}.'
            )

        if privacy != 'private':
            last_error = f'privacyStatus={privacy or "missing"}, expected private'
        elif not actual_publish_at:
            last_error = 'publishAt was not returned by YouTube'
        else:
            try:
                actual_dt = parse_publish_at(actual_publish_at)
            except ValueError:
                last_error = f'YouTube returned invalid publishAt={actual_publish_at!r}'
            else:
                delta = abs((actual_dt - expected_dt).total_seconds())
                if delta > 1:
                    last_error = (
                        f'publishAt mismatch: expected {expected_publish_at}, '
                        f'YouTube returned {actual_publish_at}'
                    )
                else:
                    upload['youtube_verified_at'] = datetime.now(timezone.utc).isoformat()
                    upload['youtube_upload_status'] = upload_status or 'unknown'
                    upload['youtube_privacy_at_upload'] = privacy
                    upload['scheduled_publish_at'] = expected_publish_at
                    UPLOAD_RESULT.write_text(
                        json.dumps(upload, ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8',
                    )
                    print(
                        'YouTube schedule verified:', video_id,
                        f'privacy={privacy}, uploadStatus={upload_status or "unknown"},',
                        f'publishAt={actual_publish_at}'
                    )
                    raise SystemExit(0)

    if attempt < 5:
        print(f'YouTube schedule verification attempt {attempt} incomplete: {last_error}; retrying...')
        time.sleep(attempt * 2)

raise SystemExit(f'YouTube schedule verification failed after 5 attempts: {last_error}')
