import json
import os
from datetime import date, timedelta
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from workflow_common import archive_records

BASE = Path(__file__).parent
ARCHIVE = BASE / 'content' / 'archive'
ANALYTICS = BASE / 'analytics'
ANALYTICS.mkdir(exist_ok=True)

video_ids = []
for _, record in archive_records(ARCHIVE):
    vid = str(record.get('youtube_video_id', '')).strip()
    if vid and vid not in video_ids:
        video_ids.append(vid)

if not video_ids:
    print('No archived YouTube videos yet; analytics collection skipped.')
    raise SystemExit(0)

creds = Credentials(
    token=None,
    refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
    token_uri='https://oauth2.googleapis.com/token',
    client_id=os.environ['YOUTUBE_CLIENT_ID'],
    client_secret=os.environ['YOUTUBE_CLIENT_SECRET'],
    scopes=['https://www.googleapis.com/auth/yt-analytics.readonly'],
)

start = (date.today() - timedelta(days=90)).isoformat()
end = date.today().isoformat()
metrics = 'views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost'
rows = []

try:
    service = build('youtubeAnalytics', 'v2', credentials=creds, cache_discovery=False)
    for offset in range(0, len(video_ids), 200):
        batch = video_ids[offset:offset + 200]
        result = service.reports().query(
            ids='channel==MINE',
            startDate=start,
            endDate=end,
            metrics=metrics,
            dimensions='video',
            filters='video==' + ','.join(batch),
            sort='-views',
            maxResults=200,
        ).execute()
        headers = [h['name'] for h in result.get('columnHeaders', [])]
        for row in result.get('rows', []) or []:
            rows.append(dict(zip(headers, row)))
except HttpError as exc:
    status = getattr(exc.resp, 'status', None)
    if status in (401, 403):
        print('ANALYTICS_AUTHORIZATION_REQUIRED: refresh token needs yt-analytics.readonly scope.')
        raise SystemExit(0)
    raise

for row in rows:
    views = float(row.get('views') or 0)
    gained = float(row.get('subscribersGained') or 0)
    row['subscribers_per_1000_views'] = round((gained / views * 1000) if views else 0, 3)

payload = {
    'window': {'start_date': start, 'end_date': end},
    'video_count': len(rows),
    'videos': rows,
}
latest = ANALYTICS / 'latest.json'
snapshot = ANALYTICS / f'{end}.json'
text = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
latest.write_text(text, encoding='utf-8')
snapshot.write_text(text, encoding='utf-8')
print(f'Collected analytics for {len(rows)} videos.')
