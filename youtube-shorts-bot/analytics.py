import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from analytics_learning import build_model
from growth_config import (
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
EPOCH_PATH = ANALYTICS / "epoch.json"
MODEL_PATH = ANALYTICS / "model.json"


def _instant(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def load_epoch():
    try:
        payload = json.loads(EPOCH_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Analytics epoch is missing or invalid: {exc}") from None
    start = _instant(payload.get("start_at"))
    if payload.get("schema_version") != 1 or start is None:
        raise SystemExit("Analytics epoch must be schema_version=1 with valid start_at")
    return payload, start


def receipt_in_epoch(receipt, epoch_start):
    publish_at = _instant(receipt.get("publish_at"))
    return bool(
        receipt.get("publication_mode") == "scheduled"
        and receipt.get("planning")
        and publish_at is not None
        and publish_at >= epoch_start
    )


def load_receipts(epoch_start):
    """Load only fresh-start scheduled growth receipts; old evidence remains untouched."""
    records = {}
    if not RESULTS.exists():
        return records
    for path in sorted(RESULTS.glob("*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not receipt_in_epoch(receipt, epoch_start):
            continue
        vid = str(receipt.get("youtube_video_id", "")).strip()
        if vid:
            records[vid] = receipt
    return records


def load_request(receipt):
    raw = str(receipt.get("request_path") or "").strip()
    if not raw:
        return {}
    path = REPO_ROOT / raw
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def growth_dimensions(receipt):
    request = load_request(receipt)
    planning = receipt.get("planning") if isinstance(receipt.get("planning"), dict) else {}
    attrs = planning.get("attributes") if isinstance(planning.get("attributes"), dict) else {}
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
        "conflict": attrs.get("conflict"),
        "primary_emotion": attrs.get("primary_emotion"),
        "protagonist_role": attrs.get("protagonist_role"),
        "antagonist_role": attrs.get("antagonist_role"),
        "opening_style": attrs.get("opening_style"),
        "title_style": attrs.get("title_style"),
        "ending_style": attrs.get("ending_style"),
        "duration_bucket": bucket,
    }


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


def enrich_row(row, receipt, epoch_start, now_utc=None):
    views = float(row.get("views") or 0)
    engaged = row.get("engagedViews")
    duration = float(receipt.get("video_seconds") or 0)
    avg_duration = row.get("averageViewDuration")
    gained = row.get("subscribersGained")
    lost = row.get("subscribersLost")
    net_subscribers = None if gained is None and lost is None else float(gained or 0) - float(lost or 0)
    row["qualified_shorts_views"] = None if engaged is None else int(engaged or 0)
    row["engaged_view_rate"] = None if engaged is None else round(
        (float(engaged or 0) / views * 100) if views else 0, 3
    )
    row["average_percentage_viewed"] = row.get("averageViewPercentage")
    row["average_view_duration_relative"] = (
        None if avg_duration is None or not duration
        else round(float(avg_duration) / duration * 100, 3)
    )
    row["subscribers_per_1000_views"] = rate_per_1000(gained, views)
    row["net_subscribers_per_1000_views"] = rate_per_1000(net_subscribers, views)
    row["likes_per_1000_views"] = rate_per_1000(row.get("likes"), views)
    row["comments_per_1000_views"] = rate_per_1000(row.get("comments"), views)
    row["shares_per_1000_views"] = rate_per_1000(row.get("shares"), views)
    row["video_duration_seconds"] = receipt.get("video_seconds")
    row["publication_mode"] = receipt.get("publication_mode", "private")
    row["publish_at"] = receipt.get("publish_at")
    row["public_age_hours"] = public_age_hours(receipt, now_utc=now_utc)
    row["planning"] = receipt.get("planning")
    row["growth_dimensions"] = growth_dimensions(receipt)
    publish_at = _instant(receipt.get("publish_at"))
    row["epoch_eligible"] = bool(publish_at and publish_at >= epoch_start)
    row["growth_eligible"] = bool(
        row["epoch_eligible"]
        and receipt.get("publication_mode") == "scheduled"
        and row["public_age_hours"] is not None
        and row["public_age_hours"] >= 0
        and receipt.get("planning")
    )
    row["learning_eligible"] = bool(
        row["growth_eligible"]
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
    """Capture only near the target age so 24h/72h/7d remain comparable."""
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
            if label in snapshots:
                continue
            if not (hours <= age <= hours + MILESTONE_CAPTURE_TOLERANCE_HOURS):
                continue
            snapshots[label] = {
                "captured_at": captured_at,
                "target_age_hours": hours,
                "age_hours": round(age, 2),
                "metrics": {k: row.get(k) for k in (
                    "views", "qualified_shorts_views", "engaged_view_rate",
                    "averageViewDuration", "average_percentage_viewed",
                    "net_subscribers_per_1000_views", "subscribers_per_1000_views",
                    "shares_per_1000_views", "likes_per_1000_views",
                    "comments_per_1000_views",
                )},
            }
    MILESTONES_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def evidence_count(rows, milestones):
    """Return conservative evidence-equivalent count for growth_planner.analytics_weight()."""
    rows_by_video = {str(row.get("video")): row for row in rows if row.get("growth_eligible")}
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


def main():
    epoch, epoch_start = load_epoch()
    receipts = load_receipts(epoch_start)
    video_ids = list(receipts)
    if not video_ids:
        payload = {
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "analytics_epoch": epoch,
            "result_receipt_video_count": 0,
            "video_count": 0,
            "published_growth_video_count": 0,
            "mature_growth_video_count": 0,
            "growth_video_count": 0,
            "analytics_model": {
                "schema_version": 2, "epoch": epoch, "active_cohort": None,
                "analytics_evidence_count": 0, "analytics_enabled": False,
                "cohorts": {},
            },
            "videos": [],
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        (ANALYTICS / "latest.json").write_text(text, encoding="utf-8")
        MODEL_PATH.write_text(
            json.dumps(payload["analytics_model"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("No post-epoch Wacky Dramas growth receipts yet; fresh-start analytics remains at 0%.")
        return

    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    creds = Credentials(
        token=None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/yt-analytics.readonly",
                "https://www.googleapis.com/auth/youtube.readonly"],
    )
    start = max(date.today() - timedelta(days=90), epoch_start.date()).isoformat()
    end = date.today().isoformat()
    metrics = (
        "views,engagedViews,likes,comments,shares,estimatedMinutesWatched,"
        "averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost"
    )
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
                result = youtube.videos().list(
                    part="statistics", id=",".join(batch), maxResults=50
                ).execute()
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
            print(f"ANALYTICS_UNAVAILABLE_HTTP_{getattr(exc.resp, 'status', 'unknown')}")
            return
        raise

    now_utc = datetime.now(timezone.utc)
    rows = []
    for vid in video_ids:
        row = rows_by_video.get(vid)
        if not row:
            continue
        rows.append(enrich_row(row, receipts[vid], epoch_start, now_utc=now_utc))

    captured_at = now_utc.isoformat().replace("+00:00", "Z")
    milestones = capture_milestones(rows, captured_at)
    evidence, mature_count, evidence_views = evidence_count(rows, milestones)
    growth_rows = [x for x in rows if x.get("growth_eligible")]

    payload = {
        "captured_at": captured_at,
        "analytics_epoch": epoch,
        "window": {"start_date": start, "end_date": end},
        "result_receipt_video_count": len(video_ids),
        "video_count": len(rows),
        "published_growth_video_count": len(growth_rows),
        "mature_growth_video_count": mature_count,
        "growth_video_count": evidence,
        "analytics_evidence_views": evidence_views,
        "metrics_note": {
            "growth_video_count": (
                "planner evidence-equivalent count: zero until >=10 24h snapshots, "
                "then min(mature videos, comparable views/500)"
            ),
            "qualified_shorts_views": "engagedViews when available from YouTube Analytics",
            "viewed_vs_swiped_away": "not exposed by this targeted API path; never fabricated",
            "engaged_view_rate": "engagedViews/views continuation proxy; not labeled as viewed-vs-swiped",
            "net_subscribers_per_1000_views": "(subscribersGained-subscribersLost)/views*1000",
        },
        "videos": rows,
    }
    model = build_model(payload, milestones)
    payload["analytics_model"] = model

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (ANALYTICS / "latest.json").write_text(text, encoding="utf-8")
    (ANALYTICS / f"{end}.json").write_text(text, encoding="utf-8")
    MODEL_PATH.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Collected fresh-start analytics for {len(rows)}/{len(video_ids)} videos; "
        f"published={len(growth_rows)}; mature24h={mature_count}; "
        f"evidence_count={evidence}; analytics_enabled={model['analytics_enabled']}."
    )


if __name__ == "__main__":
    main()
