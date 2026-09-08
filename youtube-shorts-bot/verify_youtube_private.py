import argparse
import time
from datetime import datetime, timezone

from upload import make_client
from workflow_common import OUTPUT_DIR, atomic_write_json, load_json, marker_tag


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    request = load_json(args.request)
    content_id = request["content_id"]
    marker = marker_tag(content_id)
    upload_path = OUTPUT_DIR / "upload_result.json"
    if not upload_path.exists():
        raise SystemExit("Private verification failed: output/upload_result.json is missing")
    upload = load_json(upload_path)
    video_id = str(upload.get("youtube_video_id", "")).strip()
    if not video_id:
        raise SystemExit("Private verification failed: YouTube video ID is missing")

    youtube = make_client()
    last = None
    for attempt in range(1, 6):
        response = youtube.videos().list(part="snippet,status", id=video_id).execute()
        items = response.get("items", []) or []
        if not items:
            last = "video not visible through videos.list yet"
        else:
            item = items[0]
            status = item.get("status", {}) or {}
            snippet = item.get("snippet", {}) or {}
            privacy = str(status.get("privacyStatus", "")).strip().lower()
            publish_at = status.get("publishAt")
            tags = snippet.get("tags", []) or []
            upload_status = str(status.get("uploadStatus", "")).strip().lower()
            failure = status.get("failureReason") or status.get("rejectionReason")
            if upload_status in {"failed", "rejected", "deleted"} or failure:
                raise SystemExit(f"Private verification failed: uploadStatus={upload_status}, reason={failure}")
            if privacy != "private":
                raise SystemExit(f"Private verification failed: privacyStatus={privacy or 'missing'}, expected private")
            if publish_at not in (None, ""):
                raise SystemExit(f"Private verification failed: publishAt must be absent, got {publish_at!r}")
            if marker not in tags:
                raise SystemExit(f"Private verification failed: unique recovery tag {marker} is missing")
            upload.update({
                "privacy_status": "private",
                "publish_at": None,
                "youtube_verified_at": datetime.now(timezone.utc).isoformat(),
                "youtube_upload_status": upload_status or "unknown",
                "content_id_tag_verified": True,
            })
            atomic_write_json(upload_path, upload)
            print(f"YouTube PRIVATE verified: {video_id}; publishAt absent; marker present.")
            return
        if attempt < 5:
            time.sleep(attempt * 2)
    raise SystemExit(f"Private verification failed after 5 attempts: {last}")


if __name__ == "__main__":
    main()
