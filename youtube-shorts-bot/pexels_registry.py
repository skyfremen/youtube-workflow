"""Planning/library-maintenance tooling for Pexels-backed logical backgrounds.

PEXELS_API_KEY is intentionally used only here. The production resolver reads
checked-in rendition URLs and never calls the Pexels API or grows the registry.
"""

import argparse
import fcntl
import json
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from workflow_common import atomic_write_json

BASE = Path(__file__).parent
REGISTRY_PATH = BASE / "media-library" / "backgrounds.json"
API_ROOT = "https://api.pexels.com/v1/videos"
PEXELS_LICENSE = "Pexels License"


def now():
    return datetime.now(timezone.utc).isoformat()


def api_key():
    value = os.getenv("PEXELS_API_KEY", "").strip()
    if not value:
        raise RuntimeError("PEXELS_API_KEY is required for planning/library maintenance")
    return value


def api_get(path, key=None):
    request = Request(f"{API_ROOT}/{path.lstrip('/')}", headers={"Authorization": key or api_key()})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def rendition_from_api(item):
    width, height = item.get("width"), item.get("height")
    direct_url = item.get("link")
    if not isinstance(width, int) or not isinstance(height, int) or not direct_url:
        return None
    result = {
        "id": str(item.get("id")),
        "width": width,
        "height": height,
        "fps": float(item["fps"]) if item.get("fps") is not None else None,
        "file_type": str(item.get("file_type") or ""),
        "quality": str(item.get("quality") or ""),
        "direct_url": str(direct_url),
    }
    size = item.get("file_size") or item.get("size")
    if isinstance(size, int) and size > 0:
        result["file_size_bytes"] = size
    return result


def renditions_from_video(video):
    seen, renditions = set(), []
    for item in video.get("video_files", []):
        rendition = rendition_from_api(item)
        if not rendition:
            continue
        key = (rendition["id"], rendition["direct_url"])
        if key in seen:
            continue
        seen.add(key)
        renditions.append(rendition)
    return sorted(renditions, key=lambda item: (
        item["width"] * item["height"],
        float(item.get("fps") or 999),
        item["id"],
    ))


def pexels_video_id(asset):
    if asset.get("provider_asset_id"):
        return str(asset["provider_asset_id"])
    for field in ("source_page", "direct_url"):
        matches = re.findall(r"(?<!\d)(\d{5,})(?!\d)", str(asset.get(field, "")))
        if matches:
            return matches[-1]
    raise ValueError(f"Cannot derive Pexels video ID for {asset.get('id')}")


def orientation(width, height):
    if width > height:
        return "horizontal"
    if height > width:
        return "vertical"
    if width == height and width:
        return "square"
    return "unknown"


def enrich_asset(asset, video, retrieved_at=None):
    if str(video.get("id")) != pexels_video_id(asset):
        raise ValueError(f"Pexels response does not match {asset['id']}")
    renditions = renditions_from_video(video)
    if not renditions:
        raise ValueError(f"Pexels returned no usable physical renditions for {asset['id']}")
    if not any(
        rendition["file_type"] == "video/mp4"
        and rendition["width"] >= 720
        and rendition["height"] >= 1280
        for rendition in renditions
    ):
        raise ValueError(f"Pexels returned no rendition that can fill 720x1280 without upscaling for {asset['id']}")
    asset["provider_asset_id"] = str(video["id"])
    asset["source_page"] = str(video.get("url") or asset["source_page"])
    asset["creator"] = str(video.get("user", {}).get("name") or asset.get("creator") or "Unknown")
    asset["orientation"] = orientation(int(video.get("width") or 0), int(video.get("height") or 0))
    asset["width"] = int(video.get("width") or max(r["width"] for r in renditions))
    asset["height"] = int(video.get("height") or max(r["height"] for r in renditions))
    if video.get("duration"):
        asset["duration_seconds"] = float(video["duration"])
    asset["renditions"] = renditions
    asset["renditions_retrieved_at"] = retrieved_at or now()
    asset["renditions_source"] = "Pexels API v1 video_files"
    return asset


@contextmanager
def registry_lock(path):
    lock_path = Path(path).with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def load_registry_raw(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def enrich_existing(path=REGISTRY_PATH, key=None):
    failures, changed = [], 0
    with registry_lock(path):
        registry = load_registry_raw(path)
        registry["schema_version"] = 3
        registry.setdefault("rendition_policy", {
            "target_width": 720, "target_height": 1280, "target_fps": 30,
            "selection": "smallest_sufficient_crop_fill_without_upscaling",
        })
        for asset in registry.get("assets", []):
            asset.setdefault("renditions", [])
            if asset.get("source") != "Pexels":
                continue
            try:
                video = api_get(f"videos/{pexels_video_id(asset)}", key=key)
                enrich_asset(asset, video)
                changed += 1
            except Exception as exc:
                failures.append(f"{asset.get('id')}: {exc}")
        atomic_write_json(path, registry)
    return changed, failures


def next_logical_id(assets):
    numbers = [int(match.group(1)) for asset in assets
               if (match := re.fullmatch(r"satisfying-(\d{3,})", str(asset.get("id", ""))))]
    return f"satisfying-{max(numbers, default=0) + 1:03d}"


def register_video(video_id, metadata, path=REGISTRY_PATH, key=None):
    if metadata.get("verified_preview") is not True:
        raise ValueError("New backgrounds require explicit verified_preview=true")
    video = api_get(f"videos/{video_id}", key=key)
    retrieved_at = now()
    with registry_lock(path):
        registry = load_registry_raw(path)
        assets = registry.setdefault("assets", [])
        for existing in assets:
            try:
                same_provider_id = pexels_video_id(existing) == str(video_id)
            except ValueError:
                same_provider_id = False
            if same_provider_id:
                raise ValueError(f"Pexels video {video_id} is already registered as {existing['id']}")
        logical_id = next_logical_id(assets)
        width, height = int(video.get("width") or 0), int(video.get("height") or 0)
        asset = {
            "id": logical_id,
            "type": "video",
            "title": metadata["title"],
            "source": "Pexels",
            "source_page": str(video.get("url") or ""),
            "direct_url": f"https://www.pexels.com/download/video/{video_id}/",
            "provider_asset_id": str(video_id),
            "creator": str(video.get("user", {}).get("name") or "Unknown"),
            "license": PEXELS_LICENSE,
            "commercial_use": True,
            "attribution_required": False,
            "verified": True,
            "last_verified_at": retrieved_at,
            "status": "active",
            "orientation": orientation(width, height),
            "visual_tags": metadata["visual_tags"],
            "motion_type": metadata["motion_type"],
            "motion_intensity": metadata["motion_intensity"],
            "loopability_score": metadata["loopability_score"],
            "visual_satisfaction_score": metadata["visual_satisfaction_score"],
            "caption_readability_score": metadata["caption_readability_score"],
            "has_embedded_text": False,
            "has_watermark": False,
            "content_verified_by": "request_creator_visual_review",
            "renditions": [],
        }
        enrich_asset(asset, video, retrieved_at=retrieved_at)
        assets.append(asset)
        registry["schema_version"] = 3
        registry.setdefault("rendition_policy", {
            "target_width": 720, "target_height": 1280, "target_fps": 30,
            "selection": "smallest_sufficient_crop_fill_without_upscaling",
        })
        atomic_write_json(path, registry)
    return asset


def search(query, orientation_value=None, per_page=15, key=None):
    params = f"search?query={quote_plus(query)}&per_page={int(per_page)}"
    if orientation_value:
        params += f"&orientation={quote_plus(orientation_value)}"
    return api_get(params, key=key)


def main():
    parser = argparse.ArgumentParser(description="Planning-only Pexels registry maintenance")
    parser.add_argument("--registry", default=str(REGISTRY_PATH))
    sub = parser.add_subparsers(dest="command", required=True)
    enrich = sub.add_parser("enrich-existing")
    enrich.add_argument("--strict", action="store_true")
    find = sub.add_parser("search")
    find.add_argument("--query", required=True)
    find.add_argument("--orientation", choices=("portrait", "landscape", "square"))
    find.add_argument("--per-page", type=int, default=15)
    add = sub.add_parser("register")
    add.add_argument("--video-id", required=True)
    add.add_argument("--title", required=True)
    add.add_argument("--tags", required=True)
    add.add_argument("--motion-type", required=True)
    add.add_argument("--motion-intensity", choices=("low", "medium", "high"), required=True)
    add.add_argument("--loopability-score", type=int, required=True)
    add.add_argument("--visual-satisfaction-score", type=int, required=True)
    add.add_argument("--caption-readability-score", type=int, required=True)
    add.add_argument("--verified-preview", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "enrich-existing":
            changed, failures = enrich_existing(args.registry)
            print(json.dumps({"enriched": changed, "failures": failures}, indent=2))
            if failures and args.strict:
                raise SystemExit(3)
        elif args.command == "search":
            print(json.dumps(search(args.query, args.orientation, args.per_page), indent=2))
        else:
            scores = (args.loopability_score, args.visual_satisfaction_score, args.caption_readability_score)
            if any(not 0 <= value <= 100 for value in scores):
                raise ValueError("quality scores must be between 0 and 100")
            metadata = {
                "title": args.title,
                "visual_tags": [tag.strip() for tag in args.tags.split(",") if tag.strip()],
                "motion_type": args.motion_type,
                "motion_intensity": args.motion_intensity,
                "loopability_score": args.loopability_score,
                "visual_satisfaction_score": args.visual_satisfaction_score,
                "caption_readability_score": args.caption_readability_score,
                "verified_preview": args.verified_preview,
            }
            print(json.dumps(register_video(args.video_id, metadata, args.registry), indent=2))
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
