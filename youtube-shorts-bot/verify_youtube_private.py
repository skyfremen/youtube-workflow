import argparse
import time

from recovery_state import RecoveryBlocked, check_identity, identity_for, now
from upload import make_client, authenticated_channel, description_marker
from workflow_common import OUTPUT_DIR, atomic_write_json, load_json, marker_tag


RETRY_DELAYS = (0, 2, 4, 8, 16, 30)


def verify_video(youtube, request, identity, evidence, sleep=time.sleep):
    check_identity(evidence, identity)
    video_id = evidence.get("youtube_video_id")
    if not video_id or evidence.get("record_type") != "upload" or not evidence.get("association"):
        raise RecoveryBlocked("A durable upload record is required before verification")
    channel = authenticated_channel(youtube)
    if channel["id"] != evidence.get("expected_channel_id"):
        raise RecoveryBlocked("Authenticated channel differs from upload evidence")
    expected_snippet = evidence["upload_body"]["snippet"]
    last = "video not visible"
    observations = []
    for attempt, delay in enumerate(RETRY_DELAYS, 1):
        if delay:
            sleep(delay)
        response = youtube.videos().list(part="snippet,status,contentDetails", id=video_id).execute()
        items = response.get("items", [])
        if not items:
            last = "video not visible"
            observations.append({"attempt": attempt, "observed_at": now(), "state": last})
            continue
        if len(items) != 1 or items[0].get("id") != video_id:
            raise RecoveryBlocked("YouTube returned a different video ID")
        item = items[0]
        snippet, status = item.get("snippet", {}), item.get("status", {})
        if not snippet or not status:
            last = "snippet/status not propagated"
            continue
        if snippet.get("channelId") != channel["id"]:
            raise RecoveryBlocked("Video belongs to a different channel")
        if status.get("privacyStatus") != "private":
            raise RecoveryBlocked("Video is not exactly PRIVATE")
        if "publishAt" in status:
            raise RecoveryBlocked("publishAt must be absent, including empty/null values")
        if status.get("uploadStatus") in {"failed", "rejected", "deleted"} or status.get("failureReason") or status.get("rejectionReason"):
            raise RecoveryBlocked("YouTube rejected or failed the upload")
        # Do not silently accept another story or overwrite mismatched metadata.
        for field in ("title", "description", "categoryId"):
            if snippet.get(field) != expected_snippet.get(field):
                raise RecoveryBlocked(f"YouTube {field} differs from recorded upload metadata")
        if status.get("uploadStatus") != "processed":
            last = "YouTube processing not complete"
            observations.append({"attempt": attempt, "observed_at": now(), "state": last})
            continue
        tags = snippet.get("tags", [])
        known_tags = [marker_tag(identity["content_id"]), "wd-id-" + identity["content_id"]]
        seen_tags = [tag for tag in known_tags if tag in tags]
        # Tags are supplementary. The immutable GitHub blob binds request bytes,
        # original workflow and exact returned video ID even during tag lag.
        return {
            "passed": True, "state": "verified_private", "verified_at": now(),
            **identity, "youtube_video_id": video_id, "channel_id": channel["id"],
            "channel_title": channel.get("snippet", {}).get("title"),
            "channel_handle": channel.get("snippet", {}).get("customUrl"),
            "privacy_status": "private", "publish_at_absent": True,
            "upload_status": status["uploadStatus"], "association_method": "immutable_github_upload_record",
            "observed_marker_tags": seen_tags,
            "description_marker_observed": description_marker(identity) in snippet.get("description", ""),
            "attempts": attempt, "prior_observations": observations,
        }
    raise RecoveryBlocked(f"Private verification incomplete after {len(RETRY_DELAYS)} bounded attempts: {last}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    request = load_json(args.request)
    identity = identity_for(args.request, request)
    path = OUTPUT_DIR / "upload_result.json"
    upload = load_json(path)
    check_identity(upload, identity)
    verification = verify_video(make_client(), request, identity, upload["upload_evidence"])
    upload.update({"privacy_status": "private", "publish_at": None, "publish_at_absent": True,
                   "youtube_verified_at": verification["verified_at"], "verification": verification,
                   "content_id_tag_verified": bool(verification["observed_marker_tags"])})
    atomic_write_json(path, upload)
    atomic_write_json(OUTPUT_DIR / "youtube-verification.json", verification)
    print(f"YouTube PRIVATE verified: {upload['youtube_video_id']}; publishAt absent; immutable evidence verified; tags={verification['observed_marker_tags']}")


if __name__ == "__main__":
    main()
