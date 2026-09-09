"""Production-only logical-background rendition resolver.

The immutable request decides *which* logical primary and backup may be used.
This module only chooses and downloads a physical rendition of those IDs.
"""

import argparse
import hashlib
import json
import math
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from validate_media_library import load_registry, validate_request_backgrounds
from workflow_common import OUTPUT_DIR, atomic_write_json, load_json

BASE = Path(__file__).parent
TMP = Path("/tmp/wacky-dramas-media-preflight.bin")
SUPPORTED_TYPES = {"video/mp4"}


def parse_rate(value):
    raw = str(value or "").strip()
    if not raw:
        return 0.0
    if "/" in raw:
        numerator, denominator = raw.split("/", 1)
        try:
            denominator = float(denominator)
            return float(numerator) / denominator if denominator else 0.0
        except ValueError:
            return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def crop_fill_geometry(width, height, target_width=720, target_height=1280):
    """Match FFmpeg scale=...:force_original_aspect_ratio=increase,crop=... ."""
    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError("source dimensions must be positive")
    scale = max(target_width / width, target_height / height)
    return {
        "scale_factor": scale,
        "scaled_width": math.ceil(width * scale),
        "scaled_height": math.ceil(height * scale),
        "source_crop_width": target_width / scale,
        "source_crop_height": target_height / scale,
        "upscaling_required": scale > 1.000001,
    }


def rendition_is_suitable(rendition, target_width=720, target_height=1280):
    if rendition.get("file_type") not in SUPPORTED_TYPES:
        return False
    try:
        geometry = crop_fill_geometry(
            rendition["width"], rendition["height"], target_width, target_height
        )
    except (KeyError, TypeError, ValueError):
        return False
    return not geometry["upscaling_required"]


def _fps_rank(value, target_fps):
    fps = float(value or 0)
    if fps <= 0:
        return (3, 999.0)
    if abs(fps - target_fps) <= 0.05:
        return (0, 0.0)
    if 23.0 <= fps < target_fps:
        return (1, target_fps - fps)
    if fps > target_fps:
        return (2, fps - target_fps)
    return (3, target_fps - fps)


def rendition_sort_key(rendition, target_width=720, target_height=1280, target_fps=30):
    width, height = int(rendition["width"]), int(rendition["height"])
    exact = 0 if (width, height) == (target_width, target_height) else 1
    fps_rank = _fps_rank(rendition.get("fps"), target_fps)
    size = rendition.get("file_size_bytes")
    reliable_size = isinstance(size, int) and size > 0
    physical_size = size if reliable_size else width * height
    return (
        exact, fps_rank, 0 if reliable_size else 1, physical_size,
        width * height, str(rendition.get("id", "")),
    )


def suitable_renditions(asset, target_width=720, target_height=1280, target_fps=30):
    candidates = [
        dict(rendition) for rendition in asset.get("renditions", [])
        if rendition_is_suitable(rendition, target_width, target_height)
    ]
    return sorted(
        candidates,
        key=lambda rendition: rendition_sort_key(
            rendition, target_width, target_height, target_fps
        ),
    )


def select_best_rendition(asset, target_width=720, target_height=1280, target_fps=30):
    candidates = suitable_renditions(asset, target_width, target_height, target_fps)
    return candidates[0] if candidates else None


def generic_fallback(asset):
    url = str(asset.get("direct_url") or "").strip()
    if not url:
        return None
    return {
        "id": "generic-original-fallback", "width": asset.get("width"),
        "height": asset.get("height"), "fps": asset.get("fps"),
        "file_type": "video/mp4", "quality": "original", "direct_url": url,
    }


def preflight(url):
    cmd = [
        "curl", "-L", "--fail-with-body", "--silent", "--show-error",
        "--connect-timeout", "15", "--max-time", "35", "--range", "0-0",
        "--max-filesize", "1048576", "-A", "Mozilla/5.0", "-o", str(TMP),
        "-w", "%{http_code} %{content_type} %{url_effective}", str(url),
    ]
    started = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = round(time.monotonic() - started, 6)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "curl failed").strip(), elapsed
    parts = (result.stdout or "").strip().split(" ", 2)
    code = parts[0] if parts else ""
    content_type = parts[1].lower() if len(parts) > 1 else ""
    if not code.startswith("2"):
        return False, f"HTTP {code}", elapsed
    if "text/html" in content_type:
        return False, "returned HTML instead of video media", elapsed
    return True, f"HTTP {code}, {content_type or 'unknown content-type'}", elapsed


def probe_video(target):
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate",
            "-of", "json", str(target),
        ],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        raise RuntimeError("download is not a decodable video")
    try:
        stream = json.loads(probe.stdout or "{}").get("streams", [])[0]
    except (IndexError, json.JSONDecodeError):
        raise RuntimeError("download has no video stream")
    if stream.get("codec_type") != "video":
        raise RuntimeError("download has no video stream")
    return {
        "codec": stream.get("codec_name"), "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "fps": round(parse_rate(stream.get("r_frame_rate")), 6),
    }


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(asset, rendition, target, target_width=720, target_height=1280):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    cmd = [
        "curl", "-L", "--fail-with-body", "--silent", "--show-error",
        "--retry", "3", "--retry-delay", "2", "--retry-all-errors",
        "--connect-timeout", "20", "--max-time", "180", "-A", "Mozilla/5.0",
        "-o", str(target), str(rendition["direct_url"]),
    ]
    started = time.monotonic()
    subprocess.run(cmd, check=True)
    elapsed = round(time.monotonic() - started, 6)
    if not target.exists() or target.stat().st_size < 10000:
        raise RuntimeError(f"Downloaded background {asset['id']} is suspiciously small")
    probe = probe_video(target)
    if not rendition_is_suitable(
        {"file_type": "video/mp4", **probe}, target_width, target_height
    ):
        raise RuntimeError(
            f"downloaded rendition {probe['width']}x{probe['height']} would require material upscaling"
        )
    return {
        "downloaded_bytes": target.stat().st_size,
        "download_duration_seconds": elapsed,
        "background_sha256": sha256_file(target),
        "source_probe": probe,
    }


def resolve(request_path, registry_path=None, do_download=True, do_preflight=True):
    resolution_started_at = datetime.now(timezone.utc)
    timer_started = time.monotonic()
    request = load_json(request_path)
    registry = load_registry(registry_path or BASE / "media-library" / "backgrounds.json")
    primary, backup = validate_request_backgrounds(request, registry)
    target = {"width": 720, "height": 1280, "fps": 30}
    failures = []
    for selection, asset in (("primary", primary), ("backup", backup)):
        registered = suitable_renditions(
            asset, target["width"], target["height"], target["fps"]
        )
        candidates = [(rendition, False) for rendition in registered]
        fallback = generic_fallback(asset)
        if fallback:
            candidates.append((fallback, True))
        if not candidates:
            failures.append(f"{selection} {asset['id']}: no suitable rendition or generic fallback")
            continue
        physical_failures = 0
        for rendition, is_generic in candidates:
            if do_preflight:
                ok, detail, preflight_seconds = preflight(rendition["direct_url"])
                if not ok:
                    failures.append(f"{selection} {asset['id']} rendition {rendition['id']}: {detail}")
                    physical_failures += 1
                    continue
            else:
                detail, preflight_seconds = "registry-only resolution; network preflight skipped", 0.0
            metrics = {}
            if do_download:
                try:
                    metrics = download(
                        asset, rendition, OUTPUT_DIR / "background.asset",
                        target["width"], target["height"],
                    )
                except (subprocess.CalledProcessError, RuntimeError) as exc:
                    failures.append(
                        f"{selection} {asset['id']} rendition {rendition['id']}: full download failed: {exc}"
                    )
                    physical_failures += 1
                    continue
            recorded_rendition = dict(rendition)
            if metrics.get("source_probe"):
                recorded_rendition.update({
                    "width": metrics["source_probe"]["width"],
                    "height": metrics["source_probe"]["height"],
                    "fps": metrics["source_probe"]["fps"],
                    "codec": metrics["source_probe"]["codec"],
                })
            recorded_rendition["selection_reason"] = (
                "controlled_generic_original_fallback" if is_generic
                else "next_suitable_rendition_after_failure" if physical_failures
                else "smallest_sufficient_rendition"
            )
            result = {
                "requested_primary_id": primary["id"],
                "requested_backup_id": backup["id"],
                "background_asset_id": asset["id"],
                "background_selection": selection,
                "source": asset["source"], "source_page": asset["source_page"],
                "creator": asset.get("creator"), "license": asset["license"],
                "commercial_use": asset.get("commercial_use"),
                "attribution_required": asset.get("attribution_required"),
                "rendition": recorded_rendition,
                "direct_url": recorded_rendition["direct_url"],
                "target": target,
                "rendition_fallback_used": physical_failures > 0,
                "logical_fallback_used": selection == "backup",
                "generic_source_fallback_used": is_generic,
                "preflight": detail,
                "failures_before_selection": list(failures),
                "metrics": {
                    "resolution_started_at": resolution_started_at.isoformat(),
                    "preflight_duration_seconds": preflight_seconds,
                    "background_resolution_duration_seconds": round(time.monotonic() - timer_started, 6),
                    **metrics,
                },
            }
            atomic_write_json(OUTPUT_DIR / "background_selection.json", result)
            print(
                f"Selected {selection} background {asset['id']} rendition {rendition['id']}: "
                f"{detail}; generic={is_generic}; physical_fallbacks={physical_failures}"
            )
            return result
    raise RuntimeError("Both requested background choices failed rendition resolution: " + "; ".join(failures))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--registry")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()
    try:
        resolve(
            args.request, args.registry,
            do_download=not args.no_download,
            do_preflight=not args.skip_preflight,
        )
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
