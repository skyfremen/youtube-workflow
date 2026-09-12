import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from analytics.analytics_learning import build_model
from planning.planning_config import (
    ANALYTICS_MATURITY_HOURS,
    ANALYTICS_MIN_MATURE_VIDEOS,
    ANALYTICS_VIEWS_PER_EVIDENCE_UNIT,
    MILESTONE_CAPTURE_TOLERANCE_HOURS,
    MILESTONE_HOURS,
)

BASE = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE.parent
RESULTS = BASE / "content" / "results"
ANALYTICS = BASE / "analytics"
ANALYTICS.mkdir(exist_ok=True)
RAW_PATH = REPO_ROOT / ".state" / "observations" / "latest.json"
MILESTONES_PATH = ANALYTICS / "milestones.json"
MODEL_PATH = ANALYTICS / "model.json"
LATEST_PATH = ANALYTICS / "latest.json"
SINGAPORE_TZ = ZoneInfo("Asia/Singapore")
SUPPORTED_RECEIPT_SCHEMA_VERSIONS = {3, 4, 5}


def singapore_date(now_utc=None):
    current = now_utc or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    return current.astimezone(SINGAPORE_TZ).date()


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
        receipt.get("schema_version") in SUPPORTED_RECEIPT_SCHEMA_VERSIONS
        and receipt.get("publication_mode") in {"scheduled", "immediate"}
        and isinstance(receipt.get("planning"), dict)
        and _instant(receipt.get("publish_at")) is not None
    )


def load_receipts():
    """Load canonical published success receipts for supported request schemas."""
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
    schema_version = receipt.get("schema_version")
    if schema_version not in SUPPORTED_RECEIPT_SCHEMA_VERSIONS:
        return {}
    path = REPO_ROOT / raw
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return request if request.get("schema_version") == schema_version else {}


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
    row = dict(row)
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
                        "data_source",
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


def write_snapshot(payload, dated=False, now_utc=None):
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    LATEST_PATH.write_text(text, encoding="utf-8")
    MODEL_PATH.write_text(
        json.dumps(payload["analytics_model"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if dated:
        (ANALYTICS / f"{singapore_date(now_utc).isoformat()}.json").write_text(
            text, encoding="utf-8"
        )


def load_raw_snapshot():
    try:
        payload = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported raw analytics schema")
    captured_at = _instant(payload.get("captured_at"))
    if captured_at is None:
        raise ValueError("invalid raw analytics captured_at")
    if not isinstance(payload.get("aggregate"), list) or not isinstance(
        payload.get("recent"), list
    ):
        raise ValueError("invalid raw analytics rows")
    return payload, captured_at


def raw_rows_by_video(raw):
    aggregate = {}
    for row in raw.get("aggregate", []):
        video_id = str(row.get("video", "")).strip()
        if video_id:
            aggregate[video_id] = dict(row)
    recent = {}
    for row in raw.get("recent", []):
        video_id = str(row.get("video", "")).strip()
        if video_id:
            recent[video_id] = dict(row)
    merged = dict(recent)
    merged.update(aggregate)
    return merged


def main():
    loaded = load_raw_snapshot()
    if loaded is None:
        print("No raw observation snapshot yet; analytics unchanged.")
        return
    raw, now_utc = loaded
    captured_at = now_utc.isoformat().replace("+00:00", "Z")
    receipts = load_receipts()
    video_ids = list(receipts)
    if not video_ids:
        payload = {
            "captured_at": captured_at,
            "window": raw.get("window", {}),
            "result_receipt_video_count": 0,
            "video_count": 0,
            "published_video_count": 0,
            "mature_video_count": 0,
            "analytics_evidence_count": 0,
            "analytics_evidence_views": 0,
            "videos": [],
        }
        payload["analytics_model"] = build_model(payload, {"videos": {}})
        write_snapshot(payload, now_utc=now_utc)
        print("No production receipts yet; analytics remains at 0%.")
        return

    observations = raw_rows_by_video(raw)
    rows = [
        enrich_row(observations[video_id], receipts[video_id], now_utc=now_utc)
        for video_id in video_ids
        if video_id in observations
    ]
    milestones = capture_milestones(rows, captured_at)
    evidence, mature_count, evidence_views = evidence_count(rows, milestones)
    eligible_rows = [row for row in rows if row.get("cohort_eligible")]

    payload = {
        "captured_at": captured_at,
        "window": raw.get("window", {}),
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
            "qualified_shorts_views": (
                "engagedViews when available from the aggregate analytics source"
            ),
            "viewed_vs_swiped_away": (
                "not exposed by this targeted API path; never fabricated"
            ),
            "engaged_view_rate": (
                "engagedViews/views continuation proxy; not labeled as viewed-vs-swiped"
            ),
            "net_subscribers_per_1000_views": (
                "(subscribersGained-subscribersLost)/views*1000"
            ),
            "source_precedence": (
                "aggregate analytics rows take precedence; recent statistics are "
                "used only when aggregate analytics has no row for a video"
            ),
        },
        "videos": rows,
    }
    model = build_model(payload, milestones)
    payload["analytics_model"] = model
    write_snapshot(payload, dated=True, now_utc=now_utc)
    print(
        f"Processed analytics for {len(rows)}/{len(video_ids)} videos; "
        f"published={len(eligible_rows)}; mature24h={mature_count}; "
        f"evidence_count={evidence}; analytics_enabled={model['analytics_enabled']}."
    )


if __name__ == "__main__":
    main()
