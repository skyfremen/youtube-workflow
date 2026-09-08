import json
import os
import re

from workflow_common import OUTPUT_DIR, marker_tag, request_content_id

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def build_upload_body(request_data, privacy="private"):
    if privacy != "private":
        raise ValueError("Wacky Dramas ad-hoc workflow only supports private uploads")
    content_id = request_content_id(request_data)
    marker = marker_tag(content_id)
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
    tags = [marker]
    for hashtag in yt.get("hashtags", []):
        clean = str(hashtag).strip().lstrip("#")
        if clean and clean.lower() not in {x.lower() for x in tags}:
            tags.append(clean)
    return {
        "snippet": {
            "title": str(yt["title"])[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": str(yt["category_id"]),
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": bool(yt["made_for_kids"]),
        },
    }


def make_client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=YOUTUBE_SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def find_existing_by_marker(youtube, content_id, max_videos=200):
    marker = marker_tag(content_id)
    channels = youtube.channels().list(part="contentDetails", mine=True).execute()
    items = channels.get("items", []) or []
    if not items:
        return None
    playlist_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not playlist_id:
        return None
    ids = []
    token = None
    while len(ids) < max_videos:
        response = youtube.playlistItems().list(
            part="contentDetails", playlistId=playlist_id, maxResults=50, pageToken=token
        ).execute()
        ids.extend(
            x.get("contentDetails", {}).get("videoId")
            for x in response.get("items", []) or []
            if x.get("contentDetails", {}).get("videoId")
        )
        token = response.get("nextPageToken")
        if not token:
            break
    for start in range(0, min(len(ids), max_videos), 50):
        response = youtube.videos().list(
            part="snippet,status", id=",".join(ids[start:start + 50]), maxResults=50
        ).execute()
        for item in response.get("items", []) or []:
            tags = item.get("snippet", {}).get("tags", []) or []
            if marker in tags:
                return item
    return None


def upload_new(youtube, request_data, video_path):
    from googleapiclient.http import MediaFileUpload

    body = build_upload_body(request_data, privacy="private")
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response


def execute_upload(request_data, video_path):
    content_id = request_content_id(request_data)
    existing_checkpoint = OUTPUT_DIR / "upload_result.json"
    if existing_checkpoint.exists():
        try:
            checkpoint = json.loads(existing_checkpoint.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            checkpoint = {}
        if checkpoint.get("content_id") == content_id and str(checkpoint.get("youtube_video_id", "")).strip():
            return {
                "id": checkpoint["youtube_video_id"],
                "recovered": True,
                "recovery_source": "workflow_attempt_checkpoint",
            }

    youtube = make_client()
    existing = find_existing_by_marker(youtube, content_id)
    if existing:
        return {
            "id": existing["id"],
            "recovered": True,
            "recovery_source": "youtube_content_id_marker",
            "youtube_item": existing,
        }

    try:
        response = upload_new(youtube, request_data, video_path)
        return {"id": response["id"], "recovered": False, "recovery_source": None}
    except Exception:
        existing = find_existing_by_marker(youtube, content_id)
        if existing:
            return {
                "id": existing["id"],
                "recovered": True,
                "recovery_source": "youtube_marker_after_ambiguous_upload",
                "youtube_item": existing,
            }
        raise
