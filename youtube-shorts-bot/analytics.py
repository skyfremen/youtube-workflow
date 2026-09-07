import json
import os
from datetime import date, timedelta
from pathlib import Path

from google.auth.exceptions import RefreshError
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
    scopes=[
        'https://www.googleapis.com/auth/yt-analytics.readonly',
        'https://www.googleapis.com/auth/youtube.readonly',
    ],
)

start = (date.today() - timedelta(days=90)).isoformat()
end = date.today().isoformat()
metrics = 'views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost'
rows_by_video = {}

try:
    analytics_service = build('youtubeAnalytics', 'v2', credentials=creds, cache_discovery=False)
    for offset in range(0, len(video_ids), 200):
        batch = video_ids[offset:offset + 200]
        result = analytics_service.reports().query(
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
        for values in result.get('rows', []) or []:
            row = dict(zip(headers, values))
            vid = str(row.get('video', '')).strip()
            if vid:
                row['data_source'] = 'youtube_analytics'
                rows_by_video[vid] = row

    # YouTube Analytics can lag behind freshly published Shorts. Fill any missing
    # videos with current public statistics so the daily planner still has useful
    # performance signals instead of an empty analytics file.
    missing_ids = [vid for vid in video_ids if vid not in rows_by_video]
    if missing_ids:
        youtube_service = build('youtube', 'v3', credentials=creds, cache_discovery=False)
        for offset in range(0, len(missing_ids), 50):
            batch = missing_ids[offset:offset + 50]
            result = youtube_service.videos().list(
                part='statistics',
                id=','.join(batch),
                maxResults=50,
            ).execute()
            returned = set()
            for item in result.get('items', []) or []:
                vid = str(item.get('id', '')).strip()
                if not vid:
                    continue
                returned.add(vid)
                stats = item.get('statistics', {})
                rows_by_video[vid] = {
                    'video': vid,
                    'views': int(stats.get('viewCount', 0) or 0),
                    'likes': int(stats.get('likeCount', 0) or 0),
                    'comments': int(stats.get('commentCount', 0) or 0),
                    'shares': None,
                    'estimatedMinutesWatched': None,
                    'averageViewDuration': None,
                    'subscribersGained': None,
                    'subscribersLost': None,
                    'data_source': 'youtube_data_api_fallback',
                }
            for vid in batch:
                if vid not in returned and vid not in rows_by_video:
                    rows_by_video[vid] = {
                        'video': vid,
                        'views': 0,
                        'likes': 0,
                        'comments': 0,
                        'shares': None,
                        'estimatedMinutesWatched': None,
                        'averageViewDuration': None,
                        'subscribersGained': None,
                        'subscribersLost': None,
                        'data_source': 'unavailable',
                    }
except RefreshError:
    print('ANALYTICS_AUTHORIZATION_REQUIRED: refresh token needs yt-analytics.readonly and youtube.readonly scopes.')
    raise SystemExit(0)
except HttpError as exc:
    status = getattr(exc.resp, 'status', None)
    if status in (401, 403):
        print('ANALYTICS_AUTHORIZATION_REQUIRED: refresh token needs yt-analytics.readonly and youtube.readonly scopes.')
        raise SystemExit(0)
    raise

rows = []
for vid in video_ids:
    row = rows_by_video.get(vid)
    if not row:
        continue
    views = float(row.get('views') or 0)
    gained_raw = row.get('subscribersGained')
    if gained_raw is None:
        row['subscribers_per_1000_views'] = None
    else:
        gained = float(gained_raw or 0)
        row['subscribers_per_1000_views'] = round((gained / views * 1000) if views else 0, 3)
    rows.append(row)

payload = {
    'window': {'start_date': start, 'end_date': end},
    'archived_video_count': len(video_ids),
    'video_count': len(rows),
    'analytics_ready_count': sum(1 for row in rows if row.get('data_source') == 'youtube_analytics'),
    'fallback_count': sum(1 for row in rows if row.get('data_source') == 'youtube_data_api_fallback'),
    'videos': rows,
}
latest = ANALYTICS / 'latest.json'
snapshot = ANALYTICS / f'{end}.json'
text = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
latest.write_text(text, encoding='utf-8')
snapshot.write_text(text, encoding='utf-8')
print(
    f'Collected metrics for {len(rows)}/{len(video_ids)} archived videos '
    f'({payload["analytics_ready_count"]} Analytics, {payload["fallback_count"]} live-stat fallback).'
)
