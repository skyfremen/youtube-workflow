"""Materialize exact-source Pexels preview evidence for ChatGPT/Work review.

This helper is intentionally transport-only and credential-free. It consumes an
immutable discovery result and materializes exact-source visual evidence into an
ordinary local directory. It never sets verified_preview, assigns semantic
metadata, edits the registry, or performs editorial approval.

The default evidence is the exact provider preview image. When
``--contact-sheets-only`` is supplied, FFmpeg derives compact JPEG contact sheets
from the exact ``preview_video_url`` without creating motion-sample MP4 files.
Representative frames are extracted with timestamp seeking so remote high-resolution
previews do not need to be decoded sequentially from the beginning. When
``--include-motion-evidence`` is supplied, the short motion sample is also produced.

Python HTTP is not a correctness dependency. If another trustworthy transport has
already downloaded the exact immutable preview bytes, ``--input-dir`` may point at
those files. Local exact-source files are preferred over network retrieval, using
this deterministic layout per Pexels provider ID::

    <input-dir>/<provider_asset_id>/preview.jpg
    <input-dir>/<provider_asset_id>/preview.mp4

The image extension may also be jpeg/png/webp and the video extension may also be
mov/webm. The immutable discovery-result URL remains the source identity recorded
in the evidence manifest; local files are only a transport fallback.

Image and video transports are deliberately independent. Failure to acquire the
preview image must not prevent exact preview-video review, and failure of either
transport affects only that candidate. A candidate is materialized when at least
one requested trustworthy exact-source visual transport succeeds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

USER_AGENT = "WackyDramas/1.0 preview-review-materializer"
MAX_IMAGE_BYTES = 12 * 1024 * 1024
DEFAULT_FRAME_COUNT = 5
DEFAULT_SAMPLE_SECONDS = 6.0
DEFAULT_SAMPLE_WIDTH = 480
FFMPEG_TIMEOUT_SECONDS = 240
_ALLOWED_PREVIEW_HOST_SUFFIX = ".pexels.com"
LOCAL_IMAGE_FILENAMES = ("preview.jpg", "preview.jpeg", "preview.png", "preview.webp")
LOCAL_VIDEO_FILENAMES = ("preview.mp4", "preview.mov", "preview.webm")


def _safe_provider_id(value):
    value = str(value or "").strip()
    if not re.fullmatch(r"\d+", value):
        raise ValueError("provider_asset_id must be numeric")
    return value


def _https_url(value, field):
    value = str(value or "").strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{field} must be an https URL")
    hostname = parsed.hostname.lower()
    if hostname != "pexels.com" and not hostname.endswith(_ALLOWED_PREVIEW_HOST_SUFFIX):
        raise ValueError(f"{field} must use a pexels.com host")
    return value


def _download(url, destination, max_bytes):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    digest = hashlib.sha256()
    total = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(request, timeout=45) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"preview evidence exceeds byte limit: {url}")
            digest.update(chunk)
            handle.write(chunk)
    if total == 0:
        raise ValueError(f"empty preview evidence: {url}")
    return {"path": str(destination), "bytes": total, "sha256": digest.hexdigest()}


def _file_evidence(path):
    path = Path(path)
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            digest.update(chunk)
    if total == 0:
        raise ValueError(f"empty derived evidence: {path}")
    return {"path": str(path), "bytes": total, "sha256": digest.hexdigest()}


def _local_transport_file(input_dir, provider_id, filenames):
    if input_dir is None:
        return None
    candidate_dir = Path(input_dir) / _safe_provider_id(provider_id)
    for filename in filenames:
        path = candidate_dir / filename
        if path.is_file():
            if path.stat().st_size <= 0:
                raise ValueError(f"local preview evidence is empty: {path}")
            return path
    return None


def _copy_local_evidence(source, destination):
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)
    return _file_evidence(destination)


def _positive_float(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if number <= 0:
        raise ValueError(f"{field} must be > 0")
    return number


def _run_ffmpeg(arguments):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for motion evidence")
    completed = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=FFMPEG_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "ffmpeg failed").strip()
        raise RuntimeError(error[-2000:])
    return completed


def _representative_timestamps(duration_seconds, frame_count):
    if frame_count < 3 or frame_count > 9:
        raise ValueError("representative frame count must be between 3 and 9")
    return [
        round(duration_seconds * (index + 1) / (frame_count + 1), 3)
        for index in range(frame_count)
    ]


def _materialize_contact_sheet(ffmpeg_input, destination, timestamps):
    """Seek directly to representative timestamps and tile the resulting JPEGs.

    Input-side ``-ss`` allows HTTP-capable FFmpeg builds to use provider range
    requests/keyframe seeking instead of decoding a long remote preview from frame
    zero to the last sample. The extracted small JPEGs are then tiled locally.
    """
    frame_dir = destination / ".contact-frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    contact_sheet = destination / "contact-sheet.jpg"
    try:
        for index, timestamp in enumerate(timestamps):
            frame_path = frame_dir / f"frame-{index:03d}.jpg"
            _run_ffmpeg([
                "-ss", f"{timestamp:.3f}",
                "-i", ffmpeg_input,
                "-frames:v", "1",
                "-vf", f"scale={DEFAULT_SAMPLE_WIDTH}:-2",
                "-q:v", "5",
                str(frame_path),
            ])
            _file_evidence(frame_path)

        frame_count = len(timestamps)
        grid_columns = 3 if frame_count > 4 else 2
        grid_rows = (frame_count + grid_columns - 1) // grid_columns
        _run_ffmpeg([
            "-framerate", "1",
            "-start_number", "0",
            "-i", str(frame_dir / "frame-%03d.jpg"),
            "-vf", (
                f"tile={grid_columns}x{grid_rows}:nb_frames={frame_count}:"
                "padding=4:margin=4"
            ),
            "-frames:v", "1",
            "-q:v", "5",
            str(contact_sheet),
        ])
    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)
    return _file_evidence(contact_sheet)


def _materialize_motion_evidence(
    candidate,
    destination,
    frame_count,
    sample_seconds,
    video_input=None,
    include_motion_sample=True,
):
    video_url = _https_url(candidate.get("preview_video_url"), "preview_video_url")
    duration = _positive_float(candidate.get("duration_seconds"), "duration_seconds")
    fps = _positive_float(candidate.get("preview_video_fps") or 30.0, "preview_video_fps")
    timestamps = _representative_timestamps(duration, frame_count)

    local_video = Path(video_input) if video_input is not None else None
    if local_video is not None:
        source_file = _file_evidence(local_video)
        ffmpeg_input = str(local_video)
        transport = "local_file"
    else:
        source_file = None
        ffmpeg_input = video_url
        transport = "direct_url"

    destination.mkdir(parents=True, exist_ok=True)
    contact_sheet_evidence = _materialize_contact_sheet(
        ffmpeg_input,
        destination,
        timestamps,
    )

    result = {
        "source_url": video_url,
        "transport": transport,
        "source_duration_seconds": duration,
        "source_fps": fps,
        "representative_timestamps_seconds": timestamps,
        "contact_sheet_strategy": "timestamp_seek",
        "contact_sheet": contact_sheet_evidence,
    }
    if local_video is not None:
        result["source_input"] = source_file

    if include_motion_sample:
        sample_seconds = min(_positive_float(sample_seconds, "sample_seconds"), duration)
        sample_start = max(0.0, (duration - sample_seconds) / 2.0)
        motion_sample = destination / "motion-sample.mp4"
        _run_ffmpeg([
            "-ss", f"{sample_start:.3f}", "-i", ffmpeg_input,
            "-t", f"{sample_seconds:.3f}", "-vf", f"scale={DEFAULT_SAMPLE_WIDTH}:-2",
            "-r", "12", "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(motion_sample),
        ])
        result["motion_sample"] = {
            **_file_evidence(motion_sample),
            "start_seconds": round(sample_start, 3),
            "duration_seconds": round(sample_seconds, 3),
        }
    return result


def materialize(
    discovery_result,
    output_dir,
    include_motion_evidence=False,
    frame_count=DEFAULT_FRAME_COUNT,
    sample_seconds=DEFAULT_SAMPLE_SECONDS,
    input_dir=None,
    contact_sheets_only=False,
):
    data = json.loads(Path(discovery_result).read_text(encoding="utf-8"))
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("discovery result candidates must be a list")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    local_input_root = Path(input_dir) if input_dir is not None else None
    evidence = []
    failures = []
    image_failures = []
    motion_failures = []
    motion_evidence_count = 0
    local_file_evidence_count = 0

    for candidate in candidates:
        provider_id = _safe_provider_id(candidate.get("provider_asset_id"))
        item = {
            "provider_asset_id": provider_id,
            "source_page": _https_url(candidate.get("source_page"), "source_page"),
        }
        image_ok = False
        motion_ok = False

        # Image and video are independent exact-source transports. Never `continue`
        # here: a broken/blocked still must fall through to motion evidence.
        try:
            image_url = _https_url(candidate.get("preview_image_url"), "preview_image_url")
            local_image = _local_transport_file(
                local_input_root,
                provider_id,
                LOCAL_IMAGE_FILENAMES,
            )
            if local_image is not None:
                item["image"] = _copy_local_evidence(
                    local_image,
                    output / provider_id / "preview.jpg",
                )
                item["image"]["transport"] = "local_file"
                item["image"]["source_input_path"] = str(local_image)
                local_file_evidence_count += 1
            else:
                item["image"] = _download(
                    image_url,
                    output / provider_id / "preview.jpg",
                    MAX_IMAGE_BYTES,
                )
                item["image"]["transport"] = "direct_url"
            item["image"]["source_url"] = image_url
            image_ok = True
        except Exception as exc:
            item["image_error"] = str(exc)
            image_failures.append({"provider_asset_id": provider_id, "error": str(exc)})

        if include_motion_evidence:
            try:
                local_video = _local_transport_file(
                    local_input_root,
                    provider_id,
                    LOCAL_VIDEO_FILENAMES,
                )
                item["motion"] = _materialize_motion_evidence(
                    candidate,
                    output / provider_id,
                    frame_count=frame_count,
                    sample_seconds=sample_seconds,
                    video_input=local_video,
                    include_motion_sample=not contact_sheets_only,
                )
                motion_ok = True
                motion_evidence_count += 1
                if local_video is not None:
                    local_file_evidence_count += 1
            except Exception as exc:
                item["motion_error"] = str(exc)
                motion_failures.append({"provider_asset_id": provider_id, "error": str(exc)})

        if image_ok or motion_ok:
            item["available_visual_transports"] = [
                name for name, ok in (("image", image_ok), ("motion", motion_ok)) if ok
            ]
            evidence.append(item)
        else:
            failures.append({
                "provider_asset_id": provider_id,
                "error": "no requested exact-source visual transport succeeded",
                "image_error": item.get("image_error"),
                "motion_error": item.get("motion_error"),
            })

    manifest = {
        "schema_version": 2,
        "request_id": data.get("request_id"),
        "replenishment_session_id": data.get("replenishment_session_id"),
        "planner_invocation": data.get("planner_invocation"),
        "attempt": data.get("attempt"),
        "discovery_result": str(discovery_result),
        "discovery_candidate_count": len(data.get("candidates", [])),
        "input_dir": str(local_input_root) if local_input_root is not None else None,
        "evidence_count": len(evidence),
        "failure_count": len(failures),
        "image_failure_count": len(image_failures),
        "motion_evidence_requested": bool(include_motion_evidence),
        "contact_sheets_only": bool(contact_sheets_only),
        "motion_sample_requested": bool(include_motion_evidence and not contact_sheets_only),
        "motion_evidence_count": motion_evidence_count,
        "motion_failure_count": len(motion_failures),
        "local_file_evidence_count": local_file_evidence_count,
        "representative_frame_count": frame_count if include_motion_evidence else 0,
        "motion_sample_seconds": sample_seconds if include_motion_evidence else 0,
        "evidence": evidence,
        "failures": failures,
        "image_failures": image_failures,
        "motion_failures": motion_failures,
        "rule": (
            "Transport evidence only; ChatGPT/Work must inspect the actual pixels/"
            "motion before verified_preview=true. Image and motion transports are "
            "independent; candidate-specific transport failure must not abort the set."
        ),
    }
    manifest_path = output / "evidence-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Materialize Pexels preview evidence locally")
    parser.add_argument("--discovery-result", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--input-dir",
        help=(
            "Optional directory containing exact preview bytes staged by another transport. "
            "Use <input-dir>/<provider_asset_id>/preview.jpg and/or preview.mp4."
        ),
    )
    parser.add_argument(
        "--contact-sheets-only",
        action="store_true",
        help="Derive representative JPEG contact sheets without motion-sample MP4 files.",
    )
    parser.add_argument(
        "--include-motion-evidence",
        action="store_true",
        help=(
            "Also derive a representative contact sheet and short compact motion sample "
            "from each exact preview_video_url or staged preview.mp4."
        ),
    )
    parser.add_argument(
        "--representative-frames",
        type=int,
        default=DEFAULT_FRAME_COUNT,
        help="Number of evenly distributed source frames to place in each contact sheet (3-9).",
    )
    parser.add_argument(
        "--motion-sample-seconds",
        type=float,
        default=DEFAULT_SAMPLE_SECONDS,
        help="Duration of the compact midpoint motion sample.",
    )
    args = parser.parse_args()
    motion_requested = bool(args.include_motion_evidence or args.contact_sheets_only)
    manifest = materialize(
        args.discovery_result,
        args.output_dir,
        include_motion_evidence=motion_requested,
        frame_count=args.representative_frames,
        sample_seconds=args.motion_sample_seconds,
        input_dir=args.input_dir,
        contact_sheets_only=args.contact_sheets_only,
    )
    print(json.dumps(manifest, indent=2))
    if manifest["evidence_count"] == 0 and manifest["discovery_candidate_count"] > 0:
        raise SystemExit(4)
    if (
        motion_requested
        and manifest["discovery_candidate_count"] > 0
        and manifest["motion_evidence_count"] == 0
    ):
        # Motion being unavailable everywhere is surfaced to the caller, but image
        # evidence remains materialized for ChatGPT/Work inspection and fallback.
        raise SystemExit(5)


if __name__ == "__main__":
    main()
