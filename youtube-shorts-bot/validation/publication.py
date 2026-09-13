"""Pure publication/upload validation shared by planner and publisher."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from common.workflow_common import marker_tag, request_content_id


def expected_publication(request_data, *, require_future=True, now_utc=None):
    publication = request_data.get("publication")
    if not isinstance(publication, dict):
        raise ValueError("Publication contract is required")
    mode = publication.get("mode")
    if mode == "immediate":
        if publication.get("publish_at") is not None:
            raise ValueError("Immediate publication requires publish_at=null")
        return None
    if mode != "scheduled":
        raise ValueError("publication.mode must be scheduled or immediate")
    raw = str(publication.get("publish_at", ""))
    if not raw.endswith("Z"):
        raise ValueError("Scheduled publish_at must be UTC RFC3339 ending Z")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid scheduled publish_at") from None
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("Scheduled publish_at must be UTC")
    current = now_utc or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    current = current.astimezone(timezone.utc)
    if require_future and parsed <= current:
        raise ValueError("Scheduled publish_at must be in the future at upload time")
    return raw


def _append_unique_tag(tags, seen, value):
    clean = str(value or "").strip().lstrip("#")
    if clean and clean.lower() not in seen:
        tags.append(clean)
        seen.add(clean.lower())


def prepare_upload_metadata(request_data):
    """Return the exact description/tags the publisher will send, validating limits."""
    marker = marker_tag(request_content_id(request_data))
    youtube = request_data["youtube"]
    description = str(youtube["description"]).strip()
    existing = {
        value.lower()
        for value in re.findall(r"(?<!\w)#[A-Za-z0-9_]+", description)
    }
    extras = []
    for hashtag in youtube["hashtags"]:
        hashtag = str(hashtag).strip()
        if hashtag and hashtag.lower() not in existing:
            extras.append(hashtag)
            existing.add(hashtag.lower())
    if extras:
        description += "\n\n" + " ".join(extras)
    if len(description.encode("utf-8")) > 5000:
        raise ValueError("Description exceeds YouTube's 5000-byte limit")

    tags = [marker]
    seen = {marker.lower()}
    for tag in youtube["tags"]:
        _append_unique_tag(tags, seen, tag)
    for hashtag in youtube["hashtags"]:
        _append_unique_tag(tags, seen, hashtag)
    tag_cost = (
        sum(len(tag) + (2 if " " in tag else 0) for tag in tags)
        + max(0, len(tags) - 1)
    )
    if tag_cost > 500:
        raise ValueError("Tags exceed YouTube's combined 500-character limit")
    return description, tags


def validate_upload_contract(request_data, *, require_future=False, now_utc=None):
    """Validate the publication and YouTube payload constraints without side effects."""
    expected_publication(
        request_data,
        require_future=require_future,
        now_utc=now_utc,
    )
    prepare_upload_metadata(request_data)
    return True
