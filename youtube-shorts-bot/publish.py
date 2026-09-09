import argparse
import hashlib
import os
from datetime import datetime, timedelta, timezone

from recovery_state import GitHubState, RecoveryBlocked, check_identity, identity_for, receipt_path, record_path
from upload import make_client, authenticated_channel, recover_record, authorize_fresh_upload, execute_upload
from workflow_common import OUTPUT_DIR, atomic_write_json, load_json

SCHEDULE_FRESHNESS_BUFFER_MINUTES = 10


def restore_upload(stored, identity, recovered=True):
    record = stored.data
    check_identity(record, identity)
    atomic_write_json(OUTPUT_DIR / "background_selection.json", record["background"])
    atomic_write_json(OUTPUT_DIR / "render-metadata.json", record["render"])
    payload = {**identity, "youtube_video_id": record["youtube_video_id"],
               "youtube_url": f"https://www.youtube.com/watch?v={record['youtube_video_id']}",
               "uploaded_at": record["uploaded_at"], "recovered": recovered,
               "recovery_source": "immutable_github_upload_record",
               "recovery_record_path": record_path(identity["content_id"], "upload"),
               "recovery_record_blob_sha": stored.sha, "upload_evidence": record}
    atomic_write_json(OUTPUT_DIR / "upload_result.json", payload)
    print(f"YouTube video resolved: {record['youtube_video_id']}; recovered={recovered}; upload_record={stored.sha}")


def scheduled_slot_guard(request, *, now_utc=None, buffer_minutes=SCHEDULE_FRESHNESS_BUFFER_MINUTES):
    """Return whether fresh generation should be skipped for an imminent/past scheduled slot.

    Recovery is deliberately handled before this guard. The guard protects only
    fresh background/TTS/render work when the immutable publish_at is no longer
    more than `buffer_minutes` into the future.
    """
    publication = request.get("publication")
    if not publication:
        return {"skip": False, "reason": None, "remaining_seconds": None}
    if publication.get("mode") != "scheduled":
        raise RecoveryBlocked("Unknown publication mode while checking scheduled slot guard")
    raw = str(publication.get("publish_at", ""))
    if not raw.endswith("Z"):
        raise RecoveryBlocked("Scheduled publish_at must be UTC RFC3339 ending Z")
    try:
        publish_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise RecoveryBlocked("Invalid scheduled publish_at while checking generation guard") from None
    if publish_at.utcoffset() is None or publish_at.utcoffset().total_seconds() != 0:
        raise RecoveryBlocked("Scheduled publish_at must be UTC")
    current = now_utc or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    current = current.astimezone(timezone.utc)
    cutoff = current + timedelta(minutes=buffer_minutes)
    remaining = (publish_at - current).total_seconds()
    skip = publish_at <= cutoff
    reason = None
    if skip:
        reason = (
            f"scheduled slot {raw} is past or within the {buffer_minutes}-minute fresh-generation buffer "
            f"(remaining_seconds={round(remaining, 3)})"
        )
    return {"skip": skip, "reason": reason, "remaining_seconds": remaining}


def prepare(request, identity, state, youtube, channel, recovery_only):
    receipt = state.load(receipt_path(identity["content_id"]))
    if receipt:
        check_identity(receipt.data, identity)
    stored = recover_record(youtube, state, identity, channel)
    if stored:
        if receipt and receipt.data.get("youtube_video_id") != stored.data["youtube_video_id"]:
            raise RecoveryBlocked("Receipt and durable upload evidence disagree")
        restore_upload(stored, identity)
        return False
    if receipt:
        raise RecoveryBlocked("Receipt is missing its durable upload evidence")
    if recovery_only:
        raise RecoveryBlocked("Recovery-only execution has no durable upload record; upload forbidden")
    authorize_fresh_upload(youtube, state, identity, channel)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--stage", choices=("prepare", "upload"), default="upload")
    parser.add_argument("--recovery-only", action="store_true")
    args = parser.parse_args()
    data = load_json(args.request)
    identity = identity_for(args.request, data)
    state, youtube = GitHubState(), make_client()
    channel = authenticated_channel(youtube)
    required = prepare(data, identity, state, youtube, channel, args.recovery_only)
    if args.stage == "prepare":
        guard = scheduled_slot_guard(data) if required else {"skip": False, "reason": None, "remaining_seconds": None}
        upload_required = bool(required and not guard["skip"])
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as output:
                output.write(f"upload_required={'true' if upload_required else 'false'}\n")
                output.write(f"schedule_skipped={'true' if guard['skip'] else 'false'}\n")
                output.write(f"schedule_skip_reason={guard['reason'] or ''}\n")
                if guard["remaining_seconds"] is not None:
                    output.write(f"schedule_remaining_seconds={round(guard['remaining_seconds'], 3)}\n")
        if guard["skip"]:
            print(f"Fresh generation skipped: {guard['reason']}")
        else:
            print(f"Recovery preflight: upload_required={upload_required}")
        return
    if not required:
        return
    video = OUTPUT_DIR / "short.mp4"
    render = load_json(OUTPUT_DIR / "render-metadata.json")
    if render.get("render_verified") is not True or render.get("content_id") != identity["content_id"]:
        raise RecoveryBlocked("Verified render for this content ID is required before upload")
    if hashlib.sha256(video.read_bytes()).hexdigest() != render.get("video_sha256"):
        raise RecoveryBlocked("Video bytes changed after render verification")
    stored, recovered = execute_upload(data, video, state=state, identity=identity, channel=channel,
        selection=load_json(OUTPUT_DIR / "background_selection.json"), render_meta=render, youtube=youtube)
    restore_upload(stored, identity, recovered)


if __name__ == "__main__":
    main()
