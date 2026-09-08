import argparse
from datetime import datetime, timezone
from pathlib import Path

from upload import execute_upload
from workflow_common import OUTPUT_DIR, atomic_write_json, load_json, result_path_for_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    request_path = Path(args.request)
    data = load_json(request_path)
    content_id = data["content_id"]

    receipt = result_path_for_id(content_id)
    if receipt.exists():
        existing = load_json(receipt)
        print(f"Result receipt already exists; reusing video {existing['youtube_video_id']}.")
        atomic_write_json(OUTPUT_DIR / "upload_result.json", {
            "content_id": content_id,
            "youtube_video_id": existing["youtube_video_id"],
            "youtube_url": existing["youtube_url"],
            "uploaded_at": existing["uploaded_at"],
            "recovered": True,
            "recovery_source": "result_receipt",
        })
        return

    result = execute_upload(data, OUTPUT_DIR / "short.mp4")
    video_id = result["id"]
    payload = {
        "content_id": content_id,
        "youtube_video_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "recovered": bool(result.get("recovered")),
        "recovery_source": result.get("recovery_source"),
    }
    atomic_write_json(OUTPUT_DIR / "upload_result.json", payload)
    print(f"YouTube video resolved: {video_id}; recovered={payload['recovered']}")


if __name__ == "__main__":
    main()
