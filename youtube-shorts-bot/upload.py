import os
import re

from recovery_state import RecoveryBlocked, check_identity, now, record_path, workflow_identity, source_supports_intent
from workflow_common import EXPECTED_YOUTUBE_CHANNEL_ID, OUTPUT_DIR, atomic_write_json, marker_tag, request_content_id

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]


def description_marker(identity):
    return f"[WackyDramas content_id={identity['content_id']} request_blob_sha={identity['request_blob_sha']}]"


def build_upload_body(request_data, privacy="private", identity=None):
    if privacy != "private":
        raise ValueError("Wacky Dramas ad-hoc workflow only supports private uploads")
    marker = marker_tag(request_content_id(request_data))
    yt = request_data["youtube"]
    description = str(yt["description"]).strip()
    existing = {x.lower() for x in re.findall(r"(?<!\w)#[A-Za-z0-9_]+", description)}
    extras = []
    for tag in yt.get("hashtags", []):
        tag = str(tag).strip()
        if tag and tag.lower() not in existing:
            extras.append(tag)
            existing.add(tag.lower())
    if extras:
        description += "\n\n" + " ".join(extras)
    if identity:
        description += "\n\n" + description_marker(identity)
    if len(description.encode("utf-8")) > 5000:
        raise ValueError("Description including recovery identity exceeds YouTube's 5000-byte limit")
    tags = [marker]
    for hashtag in yt.get("hashtags", []):
        clean = str(hashtag).strip().lstrip("#")
        if clean and clean.lower() not in {x.lower() for x in tags}:
            tags.append(clean)
    cost = sum(len(tag) + (2 if " " in tag else 0) for tag in tags) + max(0, len(tags) - 1)
    if cost > 500:
        raise ValueError("Tags exceed YouTube's combined 500-character limit")
    return {"snippet": {"title": str(yt["title"]), "description": description,
                        "tags": tags, "categoryId": str(yt["category_id"])},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": bool(yt["made_for_kids"])}}


def make_client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(token=None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"], scopes=YOUTUBE_SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def authenticated_channel(youtube):
    items = youtube.channels().list(part="id,snippet,contentDetails", mine=True).execute().get("items", [])
    if len(items) != 1:
        raise RecoveryBlocked("Exactly one authenticated YouTube channel is required")
    if items[0].get("id") != EXPECTED_YOUTUBE_CHANNEL_ID:
        raise RecoveryBlocked("Credentials resolve to a different channel than the pinned production channel")
    return items[0]


def find_existing_by_marker(youtube, content_id, max_videos=5000, identity=None, channel=None):
    channel = channel or authenticated_channel(youtube)
    playlist = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not playlist:
        raise RecoveryBlocked("Cannot enumerate authenticated channel uploads")
    ids, token = [], None
    while True:
        response = youtube.playlistItems().list(part="contentDetails", playlistId=playlist,
                                               maxResults=50, pageToken=token).execute()
        ids.extend(x["contentDetails"]["videoId"] for x in response.get("items", []))
        token = response.get("nextPageToken")
        if not token:
            break
        if len(ids) >= max_videos:
            raise RecoveryBlocked("Upload inventory limit reached; absence cannot authorize another upload")
    markers = {marker_tag(content_id), "wd-id-" + content_id}
    matches = {}
    for start in range(0, len(ids), 50):
        response = youtube.videos().list(part="snippet,status", id=",".join(ids[start:start + 50]), maxResults=50).execute()
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            tagged = bool(markers.intersection(snippet.get("tags", [])))
            described = identity and description_marker(identity) in snippet.get("description", "")
            if tagged or described:
                if snippet.get("channelId") != channel["id"]:
                    raise RecoveryBlocked("Recovery candidate channel mismatch")
                matches[item["id"]] = item
    if len(matches) > 1:
        raise RecoveryBlocked("Multiple videos match this immutable content ID; operator reconciliation required")
    return next(iter(matches.values()), None)


def upload_new(youtube, request_data, video_path, body):
    from googleapiclient.http import MediaFileUpload
    if body["status"].get("privacyStatus") != "private" or "publishAt" in body["status"]:
        raise RecoveryBlocked("Upload body violates PRIVATE-only policy")
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        # Only resume this one in-memory session. Never restart insert on an
        # exception or create another resumable session during recovery.
        _, response = request.next_chunk(num_retries=0)
    return response


def recover_record(youtube, state, identity, channel):
    path = record_path(identity["content_id"], "upload")
    stored = state.load(path)
    if stored:
        check_identity(stored.data, identity)
        return stored
    intent = state.load(record_path(identity["content_id"], "intent"))
    if not intent:
        return None
    check_identity(intent.data, identity)
    if intent.data["expected_channel_id"] != channel["id"]:
        raise RecoveryBlocked("Upload intent belongs to another authenticated channel")
    found = find_existing_by_marker(youtube, identity["content_id"], identity=identity, channel=channel)
    if not found:
        raise RecoveryBlocked("Upload intent exists but no video is observable yet; recovery only, never re-upload")
    payload = {**intent.data, "record_type": "upload", "youtube_video_id": found["id"],
               "uploaded_at": found["snippet"]["publishedAt"],
               "association": {"kind": "metadata_lookup_after_durable_intent", "intent_blob_sha": intent.sha,
                               "observed_at": now(), "video_item": found}}
    return state.create(path, payload)


def authorize_fresh_upload(youtube, state, identity, channel):
    if state.load(record_path(identity["content_id"], "intent")):
        raise RecoveryBlocked("Upload intent exists; recovery must resolve it before any insert")
    if not source_supports_intent(identity["source_commit_sha"]):
        raise RecoveryBlocked("Request predates durable upload intents; import original run evidence, never re-upload")
    if find_existing_by_marker(youtube, identity["content_id"], identity=identity, channel=channel):
        raise RecoveryBlocked("Existing untracked upload found; import its provenance instead of uploading")


def execute_upload(request_data, video_path, *, state, identity, channel, selection, render_meta, youtube):
    recovered = recover_record(youtube, state, identity, channel)
    if recovered:
        return recovered, True
    authorize_fresh_upload(youtube, state, identity, channel)
    body = build_upload_body(request_data, identity=identity)
    intent = {"schema_version": 1, "record_type": "intent", **identity,
              "expected_channel_id": channel["id"], "created_at": now(),
              "upload_workflow": workflow_identity(), "background": selection,
              "render": render_meta, "upload_body": body}
    claim = state.create(record_path(identity["content_id"], "intent"), intent)
    if not claim.created:
        raise RecoveryBlocked("This attempt did not exclusively create the upload intent; insert forbidden")
    try:
        response = upload_new(youtube, request_data, video_path, body)
    except Exception:
        recovered = recover_record(youtube, state, identity, channel)
        if recovered:
            return recovered, True
        raise
    # Write diagnostic evidence immediately, then acknowledge it durably BEFORE
    # verification or receipt creation. The intent survives either write failing.
    atomic_write_json(OUTPUT_DIR / "upload-response.json", response)
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(response.get("id", ""))):
        raise RecoveryBlocked("Upload response lacks a valid video ID; existing intent prevents re-upload")
    payload = {**intent, "record_type": "upload", "youtube_video_id": response["id"], "uploaded_at": now(),
               "association": {"kind": "youtube_insert_response", "intent_blob_sha": claim.sha,
                               "intent_commit_sha": claim.commit, "response": response}}
    atomic_write_json(OUTPUT_DIR / "upload-evidence.json", payload)
    return state.create(record_path(identity["content_id"], "upload"), payload), False
