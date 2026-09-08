import argparse
import os
from pathlib import Path

from workflow_common import (
    OUTPUT_DIR, atomic_write_json, ensure_request_path_matches, git_blob_sha,
    load_json, result_path_for_id,
)


def build_receipt(request_path, request, upload, selection, render_meta):
    content_id = ensure_request_path_matches(request_path, request)
    if upload.get("privacy_status") != "private":
        raise ValueError("Cannot finalize: YouTube private verification has not passed")
    if upload.get("publish_at") not in (None, ""):
        raise ValueError("Cannot finalize: publish_at must be null")
    requested = request["visual"]
    return {
        "schema_version": 1,
        "content_id": content_id,
        "request_path": Path(request_path).as_posix(),
        "request_blob_sha": git_blob_sha(request_path),
        "source_commit_sha": os.getenv("SOURCE_COMMIT_SHA", "").strip() or os.getenv("GITHUB_SHA", ""),
        "renderer_source_commit": os.getenv("SOURCE_COMMIT_SHA", "").strip() or os.getenv("GITHUB_SHA", ""),
        "youtube_video_id": upload["youtube_video_id"],
        "youtube_url": upload.get("youtube_url") or f"https://www.youtube.com/watch?v={upload['youtube_video_id']}",
        "privacy_status": "private",
        "publish_at": None,
        "background_requested_primary_id": requested["background_primary_id"],
        "background_requested_backup_id": requested["background_backup_id"],
        "background_asset_id": selection["background_asset_id"],
        "background_selection": selection["background_selection"],
        "narration_voice": request["narration"]["voice"],
        "narration_speed": float(request["narration"]["speed"]),
        "narration_seconds": float(render_meta["narration_seconds"]),
        "video_seconds": float(render_meta["video_seconds"]),
        "resolution": render_meta["resolution"],
        "fps": int(render_meta["fps"]),
        "workflow_run_id": os.getenv("GITHUB_RUN_ID", ""),
        "uploaded_at": upload["uploaded_at"],
        "youtube_verified_at": upload.get("youtube_verified_at"),
        "content_id_tag_verified": bool(upload.get("content_id_tag_verified")),
        "test_mode": bool(render_meta.get("test_mode")),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    request_path = Path(args.request)
    request = load_json(request_path)
    upload = load_json(OUTPUT_DIR / "upload_result.json")
    selection = load_json(OUTPUT_DIR / "background_selection.json")
    render_meta = load_json(OUTPUT_DIR / "render-metadata.json")
    try:
        receipt = build_receipt(request_path, request, upload, selection, render_meta)
    except ValueError as exc:
        raise SystemExit(str(exc))
    result_path = result_path_for_id(request["content_id"])
    if result_path.exists():
        existing = load_json(result_path)
        if existing.get("youtube_video_id") == receipt.get("youtube_video_id") and existing.get("request_blob_sha") == receipt.get("request_blob_sha"):
            print(f"Immutable result receipt already exists and matches: {result_path.name}")
            return
        raise SystemExit(f"Result {request['content_id']} already exists and is immutable.")
    atomic_write_json(result_path, receipt)
    print(f"Created immutable result receipt: {result_path}")


if __name__ == "__main__":
    main()
