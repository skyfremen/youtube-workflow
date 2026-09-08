import json
import os
from datetime import date, timedelta
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE = Path(__file__).parent
RESULTS = BASE / "content" / "results"
ANALYTICS = BASE / "analytics"
ANALYTICS.mkdir(exist_ok=True)


def result_video_ids():
    ids = []
    if not RESULTS.exists():
        return ids
    for path in sorted(RESULTS.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        vid = str(record.get("youtube_video_id", "")).strip()
        if vid and vid not in ids:
            ids.append(vid)
    return ids


video_ids = result_video_ids()
if not video_ids:
    print("No Wacky Dramas result receipts yet; analytics collection skipped.")
    raise SystemExit(0)

creds = Credentials(
    token=None,
    refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ["YOUTUBE_CLIENT_ID"],
    client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
    scopes=[
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "https://www.googleapis.com/auth/youtube.readonly",
    ],
)
start = (date.today() - timedelta(days=90)).isoformat()
end = date.today().isoformat()
metrics = "views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost"
rows_by_video = {}
try:
    service = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    for offset in range(0, len(video_ids), 200):
        batch = video_ids[offset:offset + 200]
        result = service.reports().query(
            ids="channel==MINE", startDate=start, endDate=end, metrics=metrics,
            dimensions="video", filters="video==" + ",".join(batch),
            sort="-views", maxResults=200,
        ).execute()
        headers = [x["name"] for x in result.get("columnHeaders", [])]
        for values in result.get("rows", []) or []:
            row = dict(zip(headers, values))
            vid = str(row.get("video", "")).strip()
            if vid:
                row["data_source"] = "youtube_analytics"
                rows_by_video[vid] = row
    missing = [x for x in video_ids if x not in rows_by_video]
    if missing:
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        for offset in range(0, len(missing), 50):
            batch = missing[offset:offset + 50]
            result = youtube.videos().list(part="statistics", id=",".join(batch), maxResults=50).execute()
            for item in result.get("items", []) or []:
                vid = item["id"]
                stats = item.get("statistics", {})
                rows_by_video[vid] = {
                    "video": vid,
                    "views": int(stats.get("viewCount", 0) or 0),
                    "likes": int(stats.get("likeCount", 0) or 0),
                    "comments": int(stats.get("commentCount", 0) or 0),
                    "shares": None, "estimatedMinutesWatched": None,
                    "averageViewDuration": None, "subscribersGained": None,
                    "subscribersLost": None, "data_source": "youtube_data_api_fallback",
                }
except RefreshError:
    print("ANALYTICS_AUTHORIZATION_REQUIRED")
    raise SystemExit(0)
except HttpError as exc:
    if getattr(exc.resp, "status", None) in (401, 403):
        print("ANALYTICS_AUTHORIZATION_REQUIRED")
        raise SystemExit(0)
    raise

rows = []
for vid in video_ids:
    row = rows_by_video.get(vid)
    if not row:
        continue
    views = float(row.get("views") or 0)
    gained = row.get("subscribersGained")
    row["subscribers_per_1000_views"] = None if gained is None else round((float(gained or 0) / views * 1000) if views else 0, 3)
    rows.append(row)
payload = {
    "window": {"start_date": start, "end_date": end},
    "result_receipt_video_count": len(video_ids),
    "video_count": len(rows),
    "videos": rows,
}
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
(ANALYTICS / "latest.json").write_text(text, encoding="utf-8")
(ANALYTICS / f"{end}.json").write_text(text, encoding="utf-8")
print(f"Collected Wacky Dramas analytics for {len(rows)}/{len(video_ids)} videos.")
