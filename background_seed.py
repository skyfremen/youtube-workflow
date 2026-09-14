#!/usr/bin/env python3
"""Wacky Dramas background discovery, review, and promotion V1."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "data" / "backgrounds.json"
REVIEWS = ROOT / "content" / "background-reviews"
APPROVALS = ROOT / "content" / "background-approvals"

CATEGORIES = (
    "pov_movement",
    "city_motion",
    "nature_motion",
    "cleaning",
    "crafting",
    "food_process",
    "assembly_process",
    "satisfying_process",
)

SEARCH_QUERIES = {
    "pov_movement": (
        "pov walking",
        "pov driving",
        "walking street pov",
        "walking trail",
        "train window",
        "cycling pov",
        "driving road",
        "walking city",
        "hiking pov",
        "car window road",
        "moving walkway",
        "escalator pov",
    ),
    "city_motion": (
        "city traffic",
        "night drive",
        "urban street",
        "pedestrian street",
        "busy intersection",
        "city timelapse",
        "subway",
        "train station",
        "night traffic",
        "downtown street",
        "city lights",
        "urban traffic",
    ),
    "nature_motion": (
        "forest trail",
        "scenic road",
        "mountain road",
        "river",
        "ocean waves",
        "waterfall",
        "forest stream",
        "mountain landscape",
        "waves beach",
        "clouds mountains",
        "rain forest",
        "flowing water",
    ),
    "cleaning": (
        "car wash",
        "pressure washing",
        "car detailing",
        "window cleaning",
        "floor cleaning",
        "dish washing",
        "deep cleaning",
        "steam cleaning",
        "scrubbing",
        "vacuum cleaning",
        "cleaning glass",
        "washing floor",
    ),
    "crafting": (
        "pottery making",
        "woodworking",
        "handmade craft",
        "artisan process",
        "wood carving",
        "pottery wheel",
        "leather crafting",
        "painting craft",
        "sewing",
        "jewelry making",
        "ceramic making",
        "hand crafting",
    ),
    "food_process": (
        "food preparation",
        "chopping food",
        "cooking closeup",
        "baking",
        "coffee making",
        "tea making",
        "cake decorating",
        "dough kneading",
        "food slicing",
        "cooking pan",
        "pastry making",
        "chef preparing food",
    ),
    "assembly_process": (
        "factory assembly",
        "manufacturing",
        "machining",
        "packaging",
        "assembly line",
        "factory machine",
        "industrial production",
        "product assembly",
        "machine workshop",
        "manufacturing process",
        "packing machine",
        "automated factory",
    ),
    "satisfying_process": (
        "satisfying process",
        "sorting",
        "printing press",
        "repetitive machine",
        "cutting machine",
        "mixing process",
        "pouring liquid",
        "automatic machine",
        "precision cutting",
        "production line",
        "rolling machine",
        "smooth process",
    ),
}

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 30.0
MAX_UPSCALE = 1.05
MAX_SOURCE_PIXELS = 4096 * 2160
MIN_DURATION = 60.0
MAX_REVIEW_CANDIDATES = 100
PEXELS_SEARCH = "https://api.pexels.com/v1/videos/search"
REQUEST_ID_RE = re.compile(r"^bgreq-[A-Za-z0-9-]{8,96}$")
ASSET_ID_RE = re.compile(r"^px-[0-9]+$")
FINAL_ASSET_FIELDS = {"id", "category", "duration_seconds", "source_url", "download_url"}
ALLOWED_MEDIA_HOSTS = (
    "videos.pexels.com",
    "player.vimeo.com",
    "vod-progressive.akamaized.net",
)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


class SeedError(ValueError):
    pass


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _https_host(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(str(url))
    except ValueError:
        return ""
    return (parsed.hostname or "").lower() if parsed.scheme == "https" else ""


def valid_source_url(url: str) -> bool:
    host = _https_host(url)
    try:
        source_path = urllib.parse.urlparse(str(url)).path
    except ValueError:
        return False
    return (host == "www.pexels.com" or host == "pexels.com") and source_path.startswith("/video/")


def valid_media_url(url: str) -> bool:
    host = _https_host(url)
    return any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_MEDIA_HOSTS)


def validate_registry(data) -> dict:
    if not isinstance(data, dict) or set(data) != {"assets"} or not isinstance(data.get("assets"), list):
        raise SeedError("backgrounds.json must contain exactly root field assets[]")
    seen = set()
    for index, asset in enumerate(data["assets"]):
        where = f"assets[{index}]"
        if not isinstance(asset, dict) or set(asset) != FINAL_ASSET_FIELDS:
            raise SeedError(f"{where} must contain exactly {sorted(FINAL_ASSET_FIELDS)}")
        asset_id = asset.get("id")
        if not isinstance(asset_id, str) or not ASSET_ID_RE.fullmatch(asset_id):
            raise SeedError(f"{where}.id must match px-<digits>")
        if asset_id in seen:
            raise SeedError(f"duplicate background id: {asset_id}")
        seen.add(asset_id)
        if asset.get("category") not in CATEGORIES:
            raise SeedError(f"{where}.category is not allowed")
        duration = asset.get("duration_seconds")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(float(duration)) or float(duration) < MIN_DURATION:
            raise SeedError(f"{where}.duration_seconds must be numeric and >= {MIN_DURATION:g}")
        if not valid_source_url(asset.get("source_url")):
            raise SeedError(f"{where}.source_url must be an https Pexels page")
        if not valid_media_url(asset.get("download_url")):
            raise SeedError(f"{where}.download_url host is not allowed")
    return data


def load_registry(path: Path = REGISTRY) -> dict:
    return validate_registry(read_json(path))


def request_id_from_path(path: Path) -> str:
    request_id = Path(path).stem
    if not REQUEST_ID_RE.fullmatch(request_id):
        raise SeedError("request id must match bgreq-<8..96 letters/digits/hyphens>")
    return request_id


def validate_request(data) -> dict:
    if not isinstance(data, dict) or set(data) != {"target_per_category", "max_candidates"}:
        raise SeedError("background request must contain exactly target_per_category and max_candidates")
    target = data["target_per_category"]
    limit = data["max_candidates"]
    if isinstance(target, bool) or not isinstance(target, int) or not 3 <= target <= 100:
        raise SeedError("target_per_category must be an integer from 3 to 100")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_REVIEW_CANDIDATES:
        raise SeedError(f"max_candidates must be an integer from 1 to {MAX_REVIEW_CANDIDATES}")
    return data


def validate_media_tools() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise SeedError(f"Required media tools are unavailable: {', '.join(missing)}")


def crop_geometry(width: int, height: int):
    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError("dimensions must be positive")
    target_aspect = TARGET_WIDTH / TARGET_HEIGHT
    source_aspect = width / height
    if source_aspect >= target_aspect:
        crop_h = float(height)
        crop_w = crop_h * target_aspect
    else:
        crop_w = float(width)
        crop_h = crop_w / target_aspect
    scale = max(TARGET_WIDTH / crop_w, TARGET_HEIGHT / crop_h)
    return crop_w, crop_h, scale


def rendition_suitable(rendition: dict) -> bool:
    if not isinstance(rendition, dict) or rendition.get("file_type") != "video/mp4":
        return False
    try:
        width = int(rendition["width"])
        height = int(rendition["height"])
    except (KeyError, TypeError, ValueError):
        return False
    if width <= 0 or height <= 0 or width * height > MAX_SOURCE_PIXELS:
        return False
    try:
        _, _, scale = crop_geometry(width, height)
    except ValueError:
        return False
    return scale <= MAX_UPSCALE + 1e-9 and valid_media_url(rendition.get("link") or rendition.get("download_url"))


def _fps_value(rendition: dict) -> float:
    try:
        value = float(rendition.get("fps") or 0)
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) and value > 0 else 0.0


def _fps_rank(value: float):
    if value <= 0:
        return (3, 999.0)
    if abs(value - TARGET_FPS) <= 0.05:
        return (0, 0.0)
    if value <= TARGET_FPS + 0.05 and value >= 23.0:
        return (1, abs(TARGET_FPS - value))
    if value <= TARGET_FPS + 0.05:
        return (2, abs(TARGET_FPS - value))
    return (3, value - TARGET_FPS)


def select_rendition(video: dict):
    options = [dict(item) for item in (video.get("video_files") or []) if rendition_suitable(item)]
    if not options:
        return None
    low_fps = [item for item in options if 0 < _fps_value(item) <= TARGET_FPS + 0.05]
    if low_fps:
        options = low_fps

    def key(item):
        width, height = int(item["width"]), int(item["height"])
        _, _, scale = crop_geometry(width, height)
        native_vertical = 0 if width <= height and scale <= 1.000001 else 1
        exact = 0 if (width, height) == (TARGET_WIDTH, TARGET_HEIGHT) else 1
        area = width * height
        size = item.get("file_size_bytes", item.get("file_size"))
        reliable_size = isinstance(size, int) and not isinstance(size, bool) and size > 0
        return (
            native_vertical,
            exact,
            _fps_rank(_fps_value(item)),
            area,
            0 if reliable_size else 1,
            size if reliable_size else area,
            str(item.get("id", "")),
        )

    return sorted(options, key=key)[0]


def duration_preference(duration) -> tuple:
    try:
        value = float(duration)
    except (TypeError, ValueError):
        return (9, 999999.0)
    if 60 <= value <= 120:
        return (0, value)
    if value > 120:
        return (1, value)
    return (9, value)


def pending_review_ids(reviews_root: Path = REVIEWS, approvals_root: Path = APPROVALS) -> set[str]:
    ids = set()
    reviews_root = Path(reviews_root)
    if not reviews_root.exists():
        return ids
    for manifest_path in reviews_root.glob("*/manifest.json"):
        review_id = manifest_path.parent.name
        if (Path(approvals_root) / f"{review_id}.json").exists():
            continue
        try:
            manifest = read_json(manifest_path)
        except (OSError, json.JSONDecodeError):
            continue
        for candidate in manifest.get("candidates", []):
            if isinstance(candidate, dict) and isinstance(candidate.get("id"), str):
                ids.add(candidate["id"])
    return ids


def api_search(query: str, api_key: str, per_page: int = 30) -> list[dict]:
    params = urllib.parse.urlencode({"query": query, "size": "medium", "per_page": min(max(per_page, 1), 80)})
    request = urllib.request.Request(
        f"{PEXELS_SEARCH}?{params}",
        headers={"Authorization": api_key, "User-Agent": "WackyDramasBackgroundSeeder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    videos = payload.get("videos", [])
    return videos if isinstance(videos, list) else []


def _candidate_from_video(video: dict, category: str):
    try:
        provider_id = int(video["id"])
        duration = float(video["duration"])
    except (KeyError, TypeError, ValueError):
        return None
    if duration < MIN_DURATION:
        return None
    source_url = str(video.get("url") or "")
    if not valid_source_url(source_url):
        return None
    rendition = select_rendition(video)
    if not rendition:
        return None
    link = str(rendition.get("link") or "")
    if not valid_media_url(link):
        return None
    return {
        "id": f"px-{provider_id}",
        "category": category,
        "duration_seconds": duration,
        "source_url": source_url,
        "download_url": link,
        "expected_width": int(rendition["width"]),
        "expected_height": int(rendition["height"]),
        "expected_fps": _fps_value(rendition),
        "rendition_id": str(rendition.get("id") or ""),
    }


def collect_metadata_candidates(
    registry: dict,
    request: dict,
    api_key: str,
    reviews_root: Path = REVIEWS,
    approvals_root: Path = APPROVALS,
    search_fn=api_search,
) -> list[dict]:
    counts = {category: 0 for category in CATEGORIES}
    existing = set()
    for asset in registry["assets"]:
        counts[asset["category"]] += 1
        existing.add(asset["id"])
    excluded = existing | pending_review_ids(reviews_root, approvals_root)
    shortages = {category: max(0, request["target_per_category"] - counts[category]) for category in CATEGORIES}
    categories = [category for category in CATEGORIES if shortages[category] > 0]
    categories.sort(key=lambda category: (-shortages[category], category))
    if not categories:
        return []

    pools = {category: [] for category in categories}
    for category in categories:
        wanted = min(max(2, shortages[category] * 2), 6)
        seen = set()
        for query in SEARCH_QUERIES[category]:
            try:
                videos = search_fn(query, api_key, 30)
            except Exception as exc:
                print(f"WARN pexels search failed category={category} query={query!r}: {exc}", flush=True)
                continue
            for video in sorted(videos, key=lambda item: duration_preference(item.get("duration"))):
                candidate = _candidate_from_video(video, category)
                if not candidate:
                    continue
                asset_id = candidate["id"]
                if asset_id in excluded or asset_id in seen:
                    continue
                seen.add(asset_id)
                pools[category].append(candidate)
                if len(pools[category]) >= wanted:
                    break
            if len(pools[category]) >= wanted:
                break

    ordered = []
    indexes = {category: 0 for category in categories}
    attempt_limit = min(request["max_candidates"] * 2, MAX_REVIEW_CANDIDATES * 2)
    while len(ordered) < attempt_limit:
        progressed = False
        category_counts = {category: 0 for category in categories}
        for selected in ordered:
            category_counts[selected["category"]] += 1
        round_categories = sorted(
            categories,
            key=lambda category: (
                category_counts[category] / max(shortages[category], 1),
                -shortages[category],
                category,
            ),
        )
        for category in round_categories:
            index = indexes[category]
            if index >= len(pools[category]):
                continue
            candidate = pools[category][index]
            indexes[category] += 1
            if candidate["id"] in {item["id"] for item in ordered}:
                continue
            ordered.append(candidate)
            progressed = True
            if len(ordered) >= attempt_limit:
                break
        if not progressed:
            break
    return ordered


def parse_rate(value) -> float:
    raw = str(value or "").strip()
    if not raw:
        return 0.0
    if "/" in raw:
        left, right = raw.split("/", 1)
        try:
            right_value = float(right)
            return float(left) / right_value if right_value else 0.0
        except ValueError:
            return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def ffprobe(path: Path) -> dict:
    process = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
    )
    if process.returncode:
        raise SeedError("ffprobe could not decode downloaded candidate")
    try:
        payload = json.loads(process.stdout or "{}")
        stream = payload["streams"][0]
        duration = float(payload["format"]["duration"])
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        raise SeedError("ffprobe returned incomplete video metadata") from None
    if stream.get("codec_type") != "video":
        raise SeedError("download has no video stream")
    return {
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "fps": round(parse_rate(stream.get("r_frame_rate")), 6),
        "duration_seconds": round(duration, 3),
    }


def download_file(url: str, target: Path) -> None:
    if not valid_media_url(url):
        raise SeedError("refusing to download from unapproved media host")
    request = urllib.request.Request(url, headers={"User-Agent": "WackyDramasBackgroundSeeder/1.0"})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=180) as response, Path(target).open("wb") as output:
                if not 200 <= int(response.status) < 300:
                    raise SeedError(f"download returned HTTP {response.status}")
                shutil.copyfileobj(response, output, 1024 * 1024)
            if Path(target).stat().st_size < 10000:
                raise SeedError("downloaded candidate is suspiciously small")
            return
        except Exception as exc:
            last = exc
            Path(target).unlink(missing_ok=True)
            if attempt < 2:
                time.sleep(2)
    raise SeedError(f"download failed after 3 attempts: {last}")


def validate_physical(candidate: dict, local_file: Path) -> dict:
    probe = ffprobe(local_file)
    if probe["duration_seconds"] < MIN_DURATION:
        raise SeedError("actual downloaded duration is shorter than 60 seconds")
    if abs(probe["duration_seconds"] - float(candidate["duration_seconds"])) > 2.0:
        raise SeedError("actual downloaded duration materially differs from Pexels metadata")
    if (probe["width"], probe["height"]) != (int(candidate["expected_width"]), int(candidate["expected_height"])):
        raise SeedError("actual downloaded dimensions differ from selected rendition metadata")
    expected_fps = float(candidate.get("expected_fps") or 0)
    if expected_fps > 0 and probe["fps"] > 0 and abs(probe["fps"] - expected_fps) > 1.0:
        raise SeedError("actual downloaded fps materially differs from selected rendition metadata")
    _, _, scale = crop_geometry(probe["width"], probe["height"])
    if scale > MAX_UPSCALE + 1e-9:
        raise SeedError("actual downloaded file cannot satisfy 1080x1920 crop quality")
    return probe


def _sample_times(duration: float) -> list[float]:
    upper = min(float(duration), 100.0)
    start = min(5.0, upper * 0.05)
    end = max(start, upper - min(10.0, upper * 0.10))
    if end <= start:
        return [round(upper * value / 7.0, 3) for value in range(1, 7)]
    return [round(start + (end - start) * index / 5.0, 3) for index in range(6)]


def make_contact_sheet(video_path: Path, candidate: dict, probe: dict, target: Path) -> None:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="background-frames-") as temp_name:
        temp = Path(temp_name)
        for index, second in enumerate(_sample_times(probe["duration_seconds"])):
            frame = temp / f"frame-{index:02d}.jpg"
            process = subprocess.run(
                [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", f"{second:.3f}", "-i", str(video_path), "-frames:v", "1",
                    "-vf", "scale=360:640:force_original_aspect_ratio=increase,crop=360:640",
                    "-q:v", "3", str(frame),
                ],
                capture_output=True,
                text=True,
            )
            if process.returncode or not frame.exists():
                raise SeedError("failed to extract review frame")
        header = (
            f"{candidate['id']} | {candidate['category']} | "
            f"{probe['duration_seconds']:.1f}s | {probe['width']}x{probe['height']} | {probe['fps']:.3f}fps"
        )
        header_file = temp / "header.txt"
        header_file.write_text(header, encoding="utf-8")
        filter_value = (
            "scale=360:640,"
            "tile=3x2:padding=0:margin=0,"
            "pad=1080:1360:0:80:black,"
            f"drawtext=fontfile={FONT}:textfile={header_file}:x=20:y=24:fontsize=28:fontcolor=white"
        )
        process = subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", "1",
                "-pattern_type", "glob", "-i", str(temp / "frame-*.jpg"),
                "-vf", filter_value, "-frames:v", "1", "-q:v", "3", str(target),
            ],
            capture_output=True,
            text=True,
        )
        if process.returncode or not target.exists():
            raise SeedError("failed to generate candidate contact sheet")


def make_index(candidate_dir: Path, target: Path, count: int) -> None:
    if count <= 0:
        return
    rows = max(1, math.ceil(count / 3))
    process = subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", "1",
            "-pattern_type", "glob", "-i", str(Path(candidate_dir) / "*.jpg"),
            "-vf", f"scale=360:-2,tile=3x{rows}:nb_frames={count}:padding=2:margin=2",
            "-frames:v", "1", "-q:v", "4", str(target),
        ],
        capture_output=True,
        text=True,
    )
    if process.returncode or not Path(target).exists():
        raise SeedError("failed to generate review index")


def _manifest_candidate(candidate: dict, probe: dict) -> dict:
    return {
        "id": candidate["id"],
        "category": candidate["category"],
        "duration_seconds": round(float(probe["duration_seconds"]), 3),
        "source_url": candidate["source_url"],
        "download_url": candidate["download_url"],
        "width": int(probe["width"]),
        "height": int(probe["height"]),
        "fps": round(float(probe["fps"]), 6),
    }


def rebuild_review_artifact(manifest: dict, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    candidates_dir = output_dir / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    for candidate in manifest.get("candidates", []):
        with tempfile.TemporaryDirectory(prefix="background-media-") as temp_name:
            local_file = Path(temp_name) / f"{candidate['id']}.mp4"
            download_file(candidate["download_url"], local_file)
            probe = ffprobe(local_file)
            if (probe["width"], probe["height"]) != (int(candidate["width"]), int(candidate["height"])):
                raise SeedError(f"{candidate['id']} changed dimensions since review manifest was created")
            make_contact_sheet(local_file, candidate, probe, candidates_dir / f"{candidate['id']}.jpg")
    make_index(candidates_dir, output_dir / "index.jpg", len(manifest.get("candidates", [])))
    write_json(output_dir / "manifest.json", manifest)


def discover(request_path: Path, api_key: str, output_dir: Path, registry_path: Path = REGISTRY, reviews_root: Path = REVIEWS) -> Path:
    validate_media_tools()
    request_path = Path(request_path)
    review_id = request_id_from_path(request_path)
    request = validate_request(read_json(request_path))
    registry = load_registry(registry_path)
    manifest_path = Path(reviews_root) / review_id / "manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        rebuild_review_artifact(manifest, output_dir)
        print(f"Review already exists; regenerated evidence: {manifest_path}")
        return manifest_path

    metadata_candidates = collect_metadata_candidates(registry, request, api_key, reviews_root=reviews_root)
    accepted = []
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    candidates_dir = Path(output_dir) / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    for candidate in metadata_candidates:
        if len(accepted) >= request["max_candidates"]:
            break
        with tempfile.TemporaryDirectory(prefix="background-media-") as temp_name:
            local_file = Path(temp_name) / f"{candidate['id']}.mp4"
            try:
                download_file(candidate["download_url"], local_file)
                probe = validate_physical(candidate, local_file)
                review_candidate = _manifest_candidate(candidate, probe)
                make_contact_sheet(local_file, review_candidate, probe, candidates_dir / f"{candidate['id']}.jpg")
                accepted.append(review_candidate)
                print(f"ACCEPT technical {candidate['id']} category={candidate['category']}", flush=True)
            except Exception as exc:
                print(f"REJECT technical {candidate['id']}: {exc}", flush=True)

    manifest = {"review_id": review_id, "request": request, "candidates": accepted}
    write_json(manifest_path, manifest)
    write_json(Path(output_dir) / "manifest.json", manifest)
    make_index(candidates_dir, Path(output_dir) / "index.jpg", len(accepted))
    print(f"Review manifest created: {manifest_path}; candidates={len(accepted)}")
    return manifest_path


def validate_approval(data, path: Path | None = None) -> dict:
    if not isinstance(data, dict) or set(data) != {"review_id", "approved_ids"}:
        raise SeedError("approval must contain exactly review_id and approved_ids")
    review_id = data.get("review_id")
    if not isinstance(review_id, str) or not REQUEST_ID_RE.fullmatch(review_id):
        raise SeedError("approval review_id is invalid")
    if path is not None and Path(path).stem != review_id:
        raise SeedError("approval filename must match review_id")
    approved = data.get("approved_ids")
    if not isinstance(approved, list) or any(not isinstance(item, str) for item in approved):
        raise SeedError("approved_ids must be an array of strings")
    if len(set(approved)) != len(approved):
        raise SeedError("approved_ids must not contain duplicates")
    if any(not ASSET_ID_RE.fullmatch(item) for item in approved):
        raise SeedError("approved_ids contains an invalid asset id")
    return data


def promote(approval_path: Path, registry_path: Path = REGISTRY, reviews_root: Path = REVIEWS) -> int:
    approval_path = Path(approval_path)
    approval = validate_approval(read_json(approval_path), approval_path)
    manifest_path = Path(reviews_root) / approval["review_id"] / "manifest.json"
    if not manifest_path.exists():
        raise SeedError("matching immutable review manifest does not exist")
    manifest = read_json(manifest_path)
    if manifest.get("review_id") != approval["review_id"] or not isinstance(manifest.get("candidates"), list):
        raise SeedError("review manifest identity is invalid")
    candidates = {}
    for item in manifest["candidates"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise SeedError("review manifest candidate is invalid")
        if item["id"] in candidates:
            raise SeedError("review manifest contains duplicate candidate ids")
        candidates[item["id"]] = item
    unknown = [item for item in approval["approved_ids"] if item not in candidates]
    if unknown:
        raise SeedError(f"approval references candidate not in manifest: {unknown[0]}")

    registry = load_registry(registry_path)
    existing = {item["id"] for item in registry["assets"]}
    added = 0
    for asset_id in approval["approved_ids"]:
        if asset_id in existing:
            continue
        source = candidates[asset_id]
        promoted = {
            "id": source["id"],
            "category": source["category"],
            "duration_seconds": source["duration_seconds"],
            "source_url": source["source_url"],
            "download_url": source["download_url"],
        }
        validate_registry({"assets": [promoted]})
        registry["assets"].append(promoted)
        existing.add(asset_id)
        added += 1
    registry["assets"].sort(key=lambda item: (CATEGORIES.index(item["category"]), int(item["id"].split("-", 1)[1])))
    validate_registry(registry)
    if added:
        write_json(registry_path, registry)
    print(f"Promotion complete: review_id={approval['review_id']} added={added}")
    return added


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-registry")
    discover_parser = sub.add_parser("discover")
    discover_parser.add_argument("--request", required=True)
    discover_parser.add_argument("--output-dir", required=True)
    promote_parser = sub.add_parser("promote")
    promote_parser.add_argument("--approval", required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate-registry":
            data = load_registry()
            print(f"Background registry valid: assets={len(data['assets'])}")
        elif args.command == "discover":
            key = os.environ.get("PEXELS_API_KEY", "").strip()
            if not key:
                raise SeedError("PEXELS_API_KEY is not configured")
            discover(Path(args.request), key, Path(args.output_dir))
        elif args.command == "promote":
            promote(Path(args.approval))
    except (OSError, json.JSONDecodeError, SeedError, ValueError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()