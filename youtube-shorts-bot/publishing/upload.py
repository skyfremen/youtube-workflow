"""Build canonical YouTube upload bodies from the shared publication contract."""
from validation.publication import (
    expected_publication as _expected_publication,
    prepare_upload_metadata,
)


def expected_publication(request_data, *, require_future=True, now_utc=None):
    """Backward-compatible publishing surface backed by shared validation."""
    return _expected_publication(
        request_data,
        require_future=require_future,
        now_utc=now_utc,
    )


def build_upload_body(request_data, *, require_future=True, now_utc=None):
    """Build the canonical scheduled or immediate-public YouTube request body."""
    publish_at = expected_publication(
        request_data, require_future=require_future, now_utc=now_utc
    )
    mode = request_data["publication"]["mode"]
    description, tags = prepare_upload_metadata(request_data)
    youtube = request_data["youtube"]

    status = {
        "privacyStatus": "public" if mode == "immediate" else "private",
        "selfDeclaredMadeForKids": bool(youtube["made_for_kids"]),
    }
    if mode == "scheduled":
        status["publishAt"] = publish_at

    return {
        "snippet": {
            "title": str(youtube["title"]),
            "description": description,
            "tags": tags,
            "categoryId": str(youtube["category_id"]),
        },
        "status": status,
    }
