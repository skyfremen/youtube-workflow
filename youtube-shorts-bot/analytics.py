import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE = Path(__file__).parent
RESULTS = BASE / "content" / "results"
ANALYTICS = BASE / "analytics"
ANALYTICS.mkdir(exist_ok=True)
MILESTONES_PATH = ANALYTICS / "milestones.json"
MILESTONE_HOURS = {"24h": 24, "72h": 72, "7d": 168}


def load_receipts():
    records = {}
    if not RESULTS.exists():
        return records
    for path in sorted(RESULTS.glob("*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        vid = str(receipt.get("youtube_video_id", "")).strip()
        if vid:
            records[vid] = receipt
    return records


def _instant(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def public_age_hours(receipt, now_utc=None):
    now_utc = now_utc or datetime.now(timezone.utc)
    start = _instant(receipt.get("publish_at"))
    if start is None:
        return None
    return (now_utc - start).total_seconds() / 3600.0


def rate_per_1000(value, views):
    if value is None:
        return None
    return round((float(value or 0) / views * 1000) if views else 0, 3)


def enrich_row(row, receipt, now_utc=None):
    views = float(row.get("views") or 0)
    engaged = row.get("engagedViews")
    duration = float(receipt.get("video_seconds") or 0)
    avg_duration = row.get("averageViewDuration")
    row["qualified_shorts_views"] = None if engaged is None else int(engaged or 0)
    row["engaged_view_rate"] = None if engaged is None else round((float(engaged or 0) / views * 100) if views else 0, 3)
    row["average_percentage_viewed"] = row.get("averageViewPercentage")
    row["average_view_duration_relative"] = None if avg_duration is None or not duration else round(min(100.0, float(avg_duration) / duration * 100), 3)
    row["subscribers_per_1000_views"] = rate_per_1000(row.get("subscribersGained"), views)
    row["likes_per_1000_views"] = rate_per_1000(row.get("likes"), views)
    row["comments_per_1000_views"] = rate_per_1000(row.get("comments"), views)
    row["shares_per_1000_views"] = rate_per_1000(row.get("shares"), views)
    row["video_duration_seconds"] = receipt.get("video_seconds")
    row["publication_mode"] = receipt.get("publication_mode", "private")
    row["publish_at"] = receipt.get("publish_at")
    row["public_age_hours"] = public_age_hours(receipt, now_utc=now_utc)
    row["planning"] = receipt.get("planning")
    row["growth_eligible"] = bool(
        receipt.get("publication_mode") == "scheduled"
        and row["public_age_hours"] is not None
        and row["public_age_hours"] >= 0
        and receipt.get("planning")
    )
    return row


def load_milestones():
    try:
        payload = json.loads(MILESTONES_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"videos": {}}
    except (OSError, json.JSONDecodeError):
        return {"videos": {}}


def capture_milestones(rows, captured_at):
    payload = load_milestones()
    payload.setdefault("videos", {})
    for row in rows:
        if not row.get("growth_eligible"):
            continue
        vid = row["video"]
        snapshots = payload["videos"].setdefault(vid, {})
        age = row.get("public_age_hours")
        if age is None:
            continue
        for label, hours in MILESTONE_HOURS.items():
            if label not in snapshots and age >= hours:
                snapshots[label] = {
                    "captured_at": captured_at,
                    "age_hours": round(age, 2),
                    "metrics": {k: row.get(k) for k in (
                        "views", "qualified_shorts_views", "engaged_view_rate",
                        "averageViewDuration", "average_percentage_viewed",
                        "subscribers_per_1000_views", "shares_per_1000_views",
                        "likes_per_1000_views", "comments_per_1000_views",
                    )},
                }
    MILESTONES_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    receipts = load_receipts()
    video_ids = list(receipts)
    if not video_ids:
        print("No Wacky Dramas result receipts yet; analytics collection skipped.")
        return

    creds = Credentials(
        token=None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/yt-analytics.readonly", "https://www.googleapis.com/auth/youtube.readonly"],
    )
    start = (date.today() - timedelta(days=90)).isoformat()
    end = date.today().isoformat()
    metrics = "views,engagedViews,likes,comments,shares,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost"
    rows_by_video = {}
    try:
        service = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        for offset in range(0, len(video_ids), 200):
            batch = video_ids[offset:offset + 200]
            result = service.reports().query(
                ids="channel==MINE", startDate=start, endDate=end, metrics=metrics,
                dimensions="video", filters="video==" + ",".join(batch), sort="-views", maxResults=200,
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
                        "video": vid, "views": int(stats.get("viewCount", 0) or 0),
                        "engagedViews": None, "likes": int(stats.get("likeCount", 0) or 0),
                        "comments": int(stats.get("commentCount", 0) or 0), "shares": None,
                        "estimatedMinutesWatched": None, "averageViewDuration": None,
                        "averageViewPercentage": None, "subscribersGained": None,
                        "subscribersLost": None, "data_source": "youtube_data_api_fallback",
                    }
    except RefreshError:
        print("ANALYTICS_AUTHORIZATION_REQUIRED")
        return
    except HttpError as exc:
        if getattr(exc.resp, "status", None) in (400, 401, 403):
            # A newly requested metric may not be authorized/available on every
            # channel yet. Fail safely: keep the last known snapshot rather than
            # inventing values or breaking production planning.
            print(f"ANALYTICS_UNAVAILABLE_HTTP_{getattr(exc.resp, 'status', 'unknown')}")
            return
        raise

    now_utc = datetime.now(timezone.utc)
    rows = []
    for vid in video_ids:
        row = rows_by_video.get(vid)
        if not row:
            continue
        rows.append(enrich_row(row, receipts[vid], now_utc=now_utc))
    captured_at = now_utc.isoformat().replace("+00:00", "Z")
    capture_milestones(rows, captured_at)
    growth_rows = [x for x in rows if x.get("growth_eligible")]
    payload = {
        "captured_at": captured_at,
        "window": {"start_date": start, "end_date": end},
        "result_receipt_video_count": len(video_ids),
        "video_count": len(rows),
        "growth_video_count": len(growth_rows),
        "metrics_note": {
            "qualified_shorts_views": "engagedViews when available from YouTube Analytics",
            "viewed_vs_swiped_away": "not exposed by this targeted API path; never fabricated",
            "engaged_view_rate": "engagedViews/views continuation proxy; not labeled as viewed-vs-swiped",
        },
        "videos": rows,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (ANALYTICS / "latest.json").write_text(text, encoding="utf-8")
    (ANALYTICS / f"{end}.json").write_text(text, encoding="utf-8")
    print(f"Collected Wacky Dramas analytics for {len(rows)}/{len(video_ids)} videos; growth_eligible={len(growth_rows)}.")


if __name__ == "__main__":
    main()
