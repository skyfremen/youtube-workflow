import argparse
import time
from datetime import datetime, timezone

from recovery_state import RecoveryBlocked, check_identity, identity_for, now
from upload import authenticated_channel, make_client
from workflow_common import OUTPUT_DIR, atomic_write_json, load_json, marker_tag

RETRY_DELAYS = (0, 2, 4, 8, 8, 4, 4, 10, 10, 10)


def _instant(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _same_instant(left, right):
    return _instant(left) is not None and _instant(left) == _instant(right)


def expected_publication_for_verification(request, evidence):
    publication = request.get("publication")
    if publication:
        raw = str(publication.get("publish_at", ""))
        if publication.get("mode") != "scheduled" or _instant(raw) is None:
            raise RecoveryBlocked("Invalid immutable publication contract")
        return {"mode": "scheduled", "publish_at": raw}

    # Schema-v2 did not encode publication in the request. New uploads are
    # immediate public, but historical private uploads must continue to recover
    # exactly as originally recorded in durable pre-insert evidence.
    status = evidence.get("upload_body", {}).get("status", {})
    privacy = status.get("privacyStatus")
    if "publishAt" in status:
        raise RecoveryBlocked("Unscheduled durable upload evidence unexpectedly contains publishAt")
    if privacy not in {"public", "private"}:
        raise RecoveryBlocked("Unscheduled durable upload evidence has unexpected privacy state")
    return {"mode": privacy, "publish_at": None}


def verify_video(youtube, request, identity, evidence, sleep=time.sleep):
    check_identity(evidence, identity)
    video_id = evidence.get("youtube_video_id")
    if not video_id or evidence.get("record_type") != "upload" or not evidence.get("association"):
        raise RecoveryBlocked("A durable upload record is required before verification")
    channel = authenticated_channel(youtube)
    if channel["id"] != evidence.get("expected_channel_id"):
        raise RecoveryBlocked("Authenticated channel differs from upload evidence")
    expected_snippet = evidence["upload_body"]["snippet"]
    publication = expected_publication_for_verification(request, evidence)
    expected_publish_at = publication.get("publish_at")
    if publication["mode"] == "scheduled":
        intent_publish_at = evidence.get("upload_body", {}).get("status", {}).get("publishAt")
        if not _same_instant(intent_publish_at, expected_publish_at):
            raise RecoveryBlocked("Durable upload intent does not contain the immutable scheduled publication time")

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
            observations.append({"attempt": attempt, "observed_at": now(), "state": last})
            continue
        if snippet.get("channelId") != channel["id"]:
            raise RecoveryBlocked("Video belongs to a different channel")
        if status.get("uploadStatus") in {"failed", "rejected", "deleted"} or status.get("failureReason") or status.get("rejectionReason"):
            raise RecoveryBlocked("YouTube rejected or failed the upload")
        for field in ("title", "description", "categoryId"):
            if snippet.get(field) != expected_snippet.get(field):
                raise RecoveryBlocked(f"YouTube {field} differs from recorded upload metadata")
        if status.get("uploadStatus") != "processed":
            last = "YouTube processing not complete"
            observations.append({"attempt": attempt, "observed_at": now(), "state": last})
            continue

        privacy = status.get("privacyStatus")
        publish_at = status.get("publishAt")
        verification_state = None
        publish_at_absent = "publishAt" not in status
        if publication["mode"] == "public":
            if privacy != "public":
                raise RecoveryBlocked("Ad-hoc video is not exactly PUBLIC")
            if not publish_at_absent:
                raise RecoveryBlocked("Immediate public video must not contain publishAt")
            verification_state = "verified_public"
        elif publication["mode"] == "private":
            if privacy != "private":
                raise RecoveryBlocked("Historical ad-hoc video is not exactly PRIVATE")
            if not publish_at_absent:
                raise RecoveryBlocked("Historical private video must not contain publishAt")
            verification_state = "verified_private"
        else:
            expected_dt = _instant(expected_publish_at)
            if privacy == "private":
                if not _same_instant(publish_at, expected_publish_at):
                    raise RecoveryBlocked("YouTube scheduled publication differs from immutable request")
                verification_state = "verified_scheduled"
                publish_at_absent = False
            elif privacy == "public":
                # Recovery may occur after the scheduled transition. The durable
                # pre-insert intent proves the requested publishAt; public state
                # is accepted only after that instant, never before it.
                current = datetime.now(timezone.utc)
                if expected_dt is None or current < expected_dt:
                    raise RecoveryBlocked("Scheduled video became public before its immutable publication time")
                if publish_at is not None and not _same_instant(publish_at, expected_publish_at):
                    raise RecoveryBlocked("Published video exposes a different publishAt than requested")
                published_at = _instant(snippet.get("publishedAt"))
                if published_at and published_at < expected_dt:
                    raise RecoveryBlocked("YouTube publishedAt predates the immutable scheduled time")
                verification_state = "verified_scheduled_published"
            else:
                raise RecoveryBlocked("Scheduled video has an unexpected privacy state")

        tags = snippet.get("tags", [])
        known_tags = [marker_tag(identity["content_id"]), "wd-id-" + identity["content_id"]]
        seen_tags = [tag for tag in known_tags if tag in tags]
        return {
            "passed": True, "state": verification_state, "verified_at": now(),
            **identity, "youtube_video_id": video_id, "channel_id": channel["id"],
            "channel_title": channel.get("snippet", {}).get("title"),
            "channel_handle": channel.get("snippet", {}).get("customUrl"),
            "privacy_status": privacy, "publish_at": expected_publish_at,
            "publish_at_absent": publish_at_absent,
            "upload_status": status["uploadStatus"], "association_method": "immutable_github_upload_record",
            "observed_marker_tags": seen_tags, "description_marker_observed": False,
            "attempts": attempt, "prior_observations": observations,
        }
    raise RecoveryBlocked(f"YouTube verification incomplete after {len(RETRY_DELAYS)} bounded attempts: {last}")


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
    upload.update({
        "privacy_status": verification["privacy_status"],
        "publish_at": verification["publish_at"],
        "publish_at_absent": verification["publish_at_absent"],
        "youtube_verified_at": verification["verified_at"], "verification": verification,
        "content_id_tag_verified": bool(verification["observed_marker_tags"]),
    })
    atomic_write_json(path, upload)
    atomic_write_json(OUTPUT_DIR / "youtube-verification.json", verification)
    print(
        f"YouTube verified: {upload['youtube_video_id']}; state={verification['state']}; "
        f"publishAt={verification['publish_at']}; tags={verification['observed_marker_tags']}"
    )


if __name__ == "__main__":
    main()
