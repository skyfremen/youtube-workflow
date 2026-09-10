import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from analytics_learning import build_model
from planning_config import (
    ANALYTICS_MATURITY_HOURS,
    ANALYTICS_MIN_MATURE_VIDEOS,
    ANALYTICS_VIEWS_PER_EVIDENCE_UNIT,
    MILESTONE_CAPTURE_TOLERANCE_HOURS,
    MILESTONE_HOURS,
)

BASE = Path(__file__).parent
REPO_ROOT = BASE.parent
RESULTS = BASE / "content" / "results"
ANALYTICS = BASE / "analytics"
ANALYTICS.mkdir(exist_ok=True)
MILESTONES_PATH = ANALYTICS / "milestones.json"
MODEL_PATH = ANALYTICS / "model.json"
LATEST_PATH = ANALYTICS / "latest.json"


def _instant(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError:
        return None


def receipt_eligible(receipt):
    return bool(
        receipt.get("schema_version") == 3
        and receipt.get("publication_mode") == "scheduled"
        and isinstance(receipt.get("planning"), dict)
        and _instant(receipt.get("publish_at")) is not None
    )


def load_receipts():
    """Load canonical scheduled schema-v3 success receipts."""
    records = {}
    if not RESULTS.exists():
        return records
    for path in sorted(RESULTS.glob("*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not receipt_eligible(receipt):
            continue
        video_id = str(receipt.get("youtube_video_id", "")).strip()
        if video_id:
            records[video_id] = receipt
    return records


def load_request(receipt):
    raw = str(receipt.get("request_path") or "").strip()
    if not raw:
        return {}
    path = REPO_ROOT / raw
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return request if request.get("schema_version") == 3 else {}


def content_dimensions(receipt):
    request = load_request(receipt)
    planning = receipt.get("planning") if isinstance(receipt.get("planning"), dict) else {}
    attributes = planning.get("attributes") if isinstance(planning.get("attributes"), dict) else {}
    story = request.get("story") if isinstance(request.get("story"), dict) else {}
    duration = receipt.get("video_seconds") or planning.get("target_duration_seconds")
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        duration = None
    if duration is None:
        bucket = None
    elif duration < 120:
        bucket = "<120"
    elif duration < 135:
        bucket = "120-134"
    elif duration < 150:
        bucket = "135-149"
    elif duration < 165:
        bucket = "150-164"
    else:
        bucket = "165-178"
    return {
        "category": story.get("category"),
        "conflict": attributes.get("conflict"),
        "primary_emotion": attributes.get("primary_emotion"),
        "protagonist_role": attributes.get("protagonist_role"),
        "antagonist_role": attributes.get("antagonist_role"),
        "opening_style": attributes.get("opening_style"),
        "title_style": attributes.get("title_style"),
        "ending_style": attributes.get("ending_style"),
        "duration_bucket": bucket,
    }


def public_age_hours(receipt, now_utc=None):
    current = now_utc or datetime.now(timezone.utc)
    start = _instant(receipt.get("publish_at"))
    if start is None:
        return None
    return (current - start).total_seconds() / 3600.0


def rate_per_1000(value, views):
    if value is None:
        return None
    return round((float(value or 0) / views * 1000) if views else 0, 3)


def enrich_row(row, receipt, now_utc=None):
    views = float(row.get("views") or 0)
    engaged = row.get("engagedViews")
    duration = float(receipt.get("video_seconds") or 0)
    average_duration = row.get("averageViewDuration")
    gained = row.get("subscribersGained")
    lost = row.get("subscribersLost")
    net_subscribers = (
        None
        if gained is None and lost is None
        else float(gained or 0) - float(lost or 0)
    )

    row["qualified_shorts_views"] = None if engaged is None else int(engaged or 0)
    row["engaged_view_rate"] = (
        None
        if engaged is None
        else round((float(engaged or 0) / views * 100) if views else 0, 3)
    )
    row["average_percentage_viewed"] = row.get("averageViewPercentage")
    row["average_view_duration_relative"] = (
        None
        if average_duration is None or not duration
        else round(float(average_duration) / duration * 100, 3)
    )
    row["subscribers_per_1000_views"] = rate_per_1000(gained, views)
    row["net_subscribers_per_1000_views"] = rate_per_1000(net_subscribers, views)
    row["likes_per_1000_views"] = rate_per_1000(row.get("likes"), views)
    row["comments_per_1000_views"] = rate_per_1000(row.get("comments"), views)
    row["shares_per_1000_views"] = rate_per_1000(row.get("shares"), views)
    row["video_duration_seconds"] = receipt.get("video_seconds")
    row["publish_at"] = receipt.get("publish_at")
    row["public_age_hours"] = public_age_hours(receipt, now_utc=now_utc)
    row["planning"] = receipt["planning"]
    row["content_dimensions"] = content_dimensions(receipt)
    row["cohort_eligible"] = bool(
        row["public_age_hours"] is not None and row["public_age_hours"] >= 0
    )
    row["learning_eligible"] = bool(
        row["cohort_eligible"]
        and row["public_age_hours"] >= ANALYTICS_MATURITY_HOURS
    )
    return row


def load_milestones():
    try:
        payload = json.loads(MILESTONES_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"videos": {}}
    except (OSError, json.JSONDecodeError):
        return {"videos": {}}


def capture_milestones(rows, captured_at):
    """Capture only near target ages so 24h/72h/7d remain comparable."""
    payload = load_milestones()
    payload.setdefault("videos", {})
    for row in rows:
        if not row.get("cohort_eligible"):
            continue
        video_id = row["video"]
        snapshots = payload["videos"].setdefault(video_id, {})
        age = row.get("public_age_hours")
        if age is None:
            continue
        for label, hours in MILESTONE_HOURS.items():
            if label in snapshots:
                continue
            if not (hours <= age <= hours + MILESTONE_CAPTURE_TOLERANCE_HOURS):
                continue
            snapshots[label] = {
                "captured_at": captured_at,
                "target_age_hours": hours,
                "age_hours": round(age, 2),
                "metrics": {
                    key: row.get(key)
                    for key in (
                        "views",
                        "qualified_shorts_views",
                        "engaged_view_rate",
                        "averageViewDuration",
                        "average_percentage_viewed",
                        "net_subscribers_per_1000_views",
                        "subscribers_per_1000_views",
                        "shares_per_1000_views",
                        "likes_per_1000_views",
                        "comments_per_1000_views",
                    )
                },
            }
    MILESTONES_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def evidence_count(rows, milestones):
    """Return the evidence-equivalent count used by planning analytics weight."""
    rows_by_video = {
        str(row.get("video")): row for row in rows if row.get("cohort_eligible")
    }
    points = []
    total_evidence_views = 0.0
    for video_id, snapshots in milestones.get("videos", {}).items():
        point = snapshots.get("24h")
        if not point or video_id not in rows_by_video:
            continue
        points.append(point)
        metrics = point.get("metrics", {})
        comparable = metrics.get("qualified_shorts_views")
        if comparable is None:
            comparable = metrics.get("views")
        try:
            total_evidence_views += max(0.0, float(comparable or 0))
        except (TypeError, ValueError):
            pass
    mature_count = len(points)
    if mature_count < ANALYTICS_MIN_MATURE_VIDEOS:
        return 0, mature_count, int(total_evidence_views)
    view_units = int(total_evidence_views // ANALYTICS_VIEWS_PER_EVIDENCE_UNIT)
    return min(mature_count, view_units), mature_count, int(total_evidence_views)


def write_snapshot(payload, dated=False):
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    LATEST_PATH.write_text(text, encoding="utf-8")
    MODEL_PATH.write_text(
        json.dumps(payload["analytics_model"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if dated:
        (ANALYTICS / f"{date.today().isoformat()}.json").write_text(text, encoding="utf-8")


def main():
    receipts = load_receipts()
    video_ids = list(receipts)
    captured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if not video_ids:
        payload = {
            "captured_at": captured_at,
            "result_receipt_video_count": 0,
            "video_count": 0,
            "published_video_count": 0,
            "mature_video_count": 0,
            "analytics_evidence_count": 0,
            "analytics_evidence_views": 0,
            "videos": [],
        }
        payload["analytics_model"] = build_model(payload, {"videos": {}})
        write_snapshot(payload)
        print("No Wacky Dramas production receipts yet; analytics remains at 0%.")
        return

    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    credentials = Credentials(
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
    oldest_publish_date = min(_instant(receipt["publish_at"]).date() for receipt in receipts.values())
    start_date = max(date.today() - timedelta(days=90), oldest_publish_date).isoformat()
    end_date = date.today().isoformat()
    metrics = (
        "views,engagedViews,likes,comments,shares,estimatedMinutesWatched,"
        "averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost"
    )
    rows_by_video = {}
    try:
        service = build(
            "youtubeAnalytics", "v2", credentials=credentials, cache_discovery=False
        )
        for offset in range(0, len(video_ids), 200):
            batch = video_ids[offset : offset + 200]
            result = service.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics=metrics,
                dimensions="video",
                filters="video==" + ",".join(batch),
                sort="-views",
                maxResults=200,
            ).execute()
            headers = [column["name"] for column in result.get("columnHeaders", [])]
            for values in result.get("rows", []) or []:
                row = dict(zip(headers, values))
                video_id = str(row.get("video", "")).strip()
                if video_id:
                    row["data_source"] = "youtube_analytics"
                    rows_by_video[video_id] = row

        missing = [video_id for video_id in video_ids if video_id not in rows_by_video]
        if missing:
            youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
            for offset in range(0, len(missing), 50):
                batch = missing[offset : offset + 50]
                result = youtube.videos().list(
                    part="statistics", id=",".join(batch), maxResults=50
                ).execute()
                for item in result.get("items", []) or []:
                    video_id = item["id"]
                    stats = item.get("statistics", {})
                    rows_by_video[video_id] = {
                        "video": video_id,
                        "views": int(stats.get("viewCount", 0) or 0),
                        "engagedViews": None,
                        "likes": int(stats.get("likeCount", 0) or 0),
                        "comments": int(stats.get("commentCount", 0) or 0),
                        "shares": None,
                        "estimatedMinutesWatched": None,
                        "averageViewDuration": None,
                        "averageViewPercentage": None,
                        "subscribersGained": None,
                        "subscribersLost": None,
                        "data_source": "youtube_data_api_fallback",
                    }
    except RefreshError:
        print("ANALYTICS_AUTHORIZATION_REQUIRED")
        return
    except HttpError as exc:
        status = getattr(exc.resp, "status", None)
        if status in (400, 401, 403):
            print(f"ANALYTICS_UNAVAILABLE_HTTP_{status or 'unknown'}")
            return
        raise

    now_utc = datetime.now(timezone.utc)
    rows = [
        enrich_row(rows_by_video[video_id], receipts[video_id], now_utc=now_utc)
        for video_id in video_ids
        if video_id in rows_by_video
    ]
    captured_at = now_utc.isoformat().replace("+00:00", "Z")
    milestones = capture_milestones(rows, captured_at)
    evidence, mature_count, evidence_views = evidence_count(rows, milestones)
    eligible_rows = [row for row in rows if row.get("cohort_eligible")]

    payload = {
        "captured_at": captured_at,
        "window": {"start_date": start_date, "end_date": end_date},
        "result_receipt_video_count": len(video_ids),
        "video_count": len(rows),
        "published_video_count": len(eligible_rows),
        "mature_video_count": mature_count,
        "analytics_evidence_count": evidence,
        "analytics_evidence_views": evidence_views,
        "metrics_note": {
            "analytics_evidence_count": (
                "planner evidence-equivalent count: zero until >=10 24h snapshots, "
                "then min(mature videos, comparable views/500)"
            ),
            "qualified_shorts_views": "engagedViews when available from YouTube Analytics",
            "viewed_vs_swiped_away": (
                "not exposed by this targeted API path; never fabricated"
            ),
            "engaged_view_rate": (
                "engagedViews/views continuation proxy; not labeled as viewed-vs-swiped"
            ),
            "net_subscribers_per_1000_views": (
                "(subscribersGained-subscribersLost)/views*1000"
            ),
        },
        "videos": rows,
    }
    model = build_model(payload, milestones)
    payload["analytics_model"] = model
    write_snapshot(payload, dated=True)
    print(
        f"Collected analytics for {len(rows)}/{len(video_ids)} videos; "
        f"published={len(eligible_rows)}; mature24h={mature_count}; "
        f"evidence_count={evidence}; analytics_enabled={model['analytics_enabled']}."
    )


if __name__ == "__main__":
    main()
