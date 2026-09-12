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
    if not path.exists():
        return {}
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if request.get("schema_version") != schema_version:
        return {}
    return request


def load_raw_snapshot():
    if not RAW_PATH.exists():
        return None, None
    try:
        payload = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    captured = _instant(payload.get("captured_at"))
    if captured is None:
        return None, None
    return payload, captured


def raw_rows_by_video(payload):
    rows = {}
    for row in payload.get("recent", []):
        video = str(row.get("video", "")).strip()
        if video:
            rows[video] = row
    for row in payload.get("aggregate", []):
        video = str(row.get("video", "")).strip()
        if video:
            rows[video] = row
    return rows


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric_row(raw):
    views = _number(raw.get("views"))
    engaged = _number(raw.get("engagedViews"))
    subscribers_gained = _number(raw.get("subscribersGained"))
    subscribers_lost = _number(raw.get("subscribersLost"))
    return {
        "views": views,
        "engagedViews": engaged,
        "engaged_view_rate": (
            engaged / views if views and engaged is not None else None
        ),
        "averageViewDuration": _number(raw.get("averageViewDuration")),
        "averageViewPercentage": _number(raw.get("averageViewPercentage")),
        "estimatedMinutesWatched": _number(raw.get("estimatedMinutesWatched")),
        "subscribersGained": subscribers_gained,
        "subscribersLost": subscribers_lost,
        "net_subscribers": (
            subscribers_gained - subscribers_lost
            if subscribers_gained is not None and subscribers_lost is not None
            else None
        ),
        "shares": _number(raw.get("shares")),
        "likes": _number(raw.get("likes")),
        "comments": _number(raw.get("comments")),
        "data_source": raw.get("data_source"),
    }


def _milestone_label(age_hours):
    candidates = []
    for label, target_hours in MILESTONE_HOURS.items():
        distance = abs(age_hours - target_hours)
        if distance <= MILESTONE_CAPTURE_TOLERANCE_HOURS:
            candidates.append((distance, label))
    if not candidates:
        return None
    return min(candidates)[1]


def load_milestones():
    if not MILESTONES_PATH.exists():
        return {"schema_version": 1, "videos": {}}
    try:
        payload = json.loads(MILESTONES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "videos": {}}
    if payload.get("schema_version") != 1 or not isinstance(payload.get("videos"), dict):
        return {"schema_version": 1, "videos": {}}
    return payload


def atomic_write(path, payload):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def collect():
    receipts = load_receipts()
    raw, captured_at = load_raw_snapshot()
    milestones = load_milestones()
    if raw is None or captured_at is None:
        atomic_write(
            LATEST_PATH,
            {
                "schema_version": 1,
                "enabled": False,
                "reason": "no current raw analytics snapshot",
                "analytics_evidence_count": 0,
                "video_count": 0,
                "mature_video_count": 0,
                "published_video_count": len(receipts),
            },
        )
        return

    rows = raw_rows_by_video(raw)
    new_captures = 0
    for video_id, receipt in receipts.items():
        row = rows.get(video_id)
        if not row:
            continue
        published_at = _instant(receipt.get("publish_at"))
        if published_at is None:
            continue
        age_hours = (captured_at - published_at).total_seconds() / 3600.0
        label = _milestone_label(age_hours)
        if label is None:
            continue
        entry = milestones["videos"].setdefault(video_id, {})
        if label in entry:
            continue
        request = load_request(receipt)
        if not request:
            continue
        planning = request.get("planning") or receipt.get("planning") or {}
        story = request.get("story") or {}
        entry[label] = {
            "captured_at": raw["captured_at"],
            "published_at": receipt.get("publish_at"),
            "age_hours": round(age_hours, 3),
            "metrics": _metric_row(row),
            "planning": planning,
            "category": story.get("category"),
        }
        new_captures += 1

    atomic_write(MILESTONES_PATH, milestones)
    model, latest = build_model(milestones)
    latest["published_video_count"] = len(receipts)
    latest["new_milestone_captures"] = new_captures
    latest["raw_captured_at"] = raw.get("captured_at")
    atomic_write(MODEL_PATH, model)
    atomic_write(LATEST_PATH, latest)


if __name__ == "__main__":
    collect()
