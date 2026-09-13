"""Materialize exact-source Pexels preview evidence for ChatGPT/Work review.

This helper is intentionally transport-only and credential-free. It consumes an
immutable discovery result and materializes exact-source visual evidence into an
ordinary local directory. It never sets verified_preview, assigns semantic
metadata, edits the registry, or performs editorial approval.

The default evidence is the exact provider preview image. When
``--include-motion-evidence`` is supplied, ffmpeg also derives a compact
representative contact sheet and a short low-resolution motion sample from the
exact ``preview_video_url`` recorded in the immutable discovery result.

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


def _materialize_motion_evidence(candidate, destination, frame_count, sample_seconds):
    video_url = _https_url(candidate.get("preview_video_url"), "preview_video_url")
    duration = _positive_float(candidate.get("duration_seconds"), "duration_seconds")
    fps = _positive_float(candidate.get("preview_video_fps") or 30.0, "preview_video_fps")
    timestamps = _representative_timestamps(duration, frame_count)
    frame_indices = sorted({max(0, int(round(timestamp * fps))) for timestamp in timestamps})
    if len(frame_indices) != frame_count:
        raise ValueError("representative frame timestamps did not map to unique frames")

    destination.mkdir(parents=True, exist_ok=True)
    select = "+".join(f"eq(n\\,{frame})" for frame in frame_indices)
    grid_columns = 3 if frame_count > 4 else 2
    grid_rows = (frame_count + grid_columns - 1) // grid_columns
    contact_sheet = destination / "contact-sheet.jpg"
    contact_filter = (
        f"select={select},"
        "setpts=N/FRAME_RATE/TB,"
        f"scale={DEFAULT_SAMPLE_WIDTH}:-2,"
        f"tile={grid_columns}x{grid_rows}:nb_frames={frame_count}:padding=4:margin=4"
    )
    _run_ffmpeg([
        "-i", video_url, "-vf", contact_filter, "-frames:v", "1", str(contact_sheet)
    ])

    sample_seconds = min(_positive_float(sample_seconds, "sample_seconds"), duration)
    sample_start = max(0.0, (duration - sample_seconds) / 2.0)
    motion_sample = destination / "motion-sample.mp4"
    _run_ffmpeg([
        "-ss", f"{sample_start:.3f}", "-i", video_url,
        "-t", f"{sample_seconds:.3f}", "-vf", f"scale={DEFAULT_SAMPLE_WIDTH}:-2",
        "-r", "12", "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(motion_sample),
    ])

    return {
        "source_url": video_url,
        "source_duration_seconds": duration,
        "source_fps": fps,
        "representative_timestamps_seconds": timestamps,
        "contact_sheet": _file_evidence(contact_sheet),
        "motion_sample": {
            **_file_evidence(motion_sample),
            "start_seconds": round(sample_start, 3),
            "duration_seconds": round(sample_seconds, 3),
        },
    }


def materialize(
    discovery_result,
    output_dir,
    include_motion_evidence=False,
    frame_count=DEFAULT_FRAME_COUNT,
    sample_seconds=DEFAULT_SAMPLE_SECONDS,
):
    data = json.loads(Path(discovery_result).read_text(encoding="utf-8"))
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("discovery result candidates must be a list")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    evidence = []
    failures = []
    image_failures = []
    motion_failures = []
    motion_evidence_count = 0

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
            item["image"] = _download(
                image_url, output / provider_id / "preview.jpg", MAX_IMAGE_BYTES
            )
            item["image"]["source_url"] = image_url
            image_ok = True
        except Exception as exc:
            item["image_error"] = str(exc)
            image_failures.append({"provider_asset_id": provider_id, "error": str(exc)})

        if include_motion_evidence:
            try:
                item["motion"] = _materialize_motion_evidence(
                    candidate,
                    output / provider_id,
                    frame_count=frame_count,
                    sample_seconds=sample_seconds,
                )
                motion_ok = True
                motion_evidence_count += 1
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
        "discovery_result": str(discovery_result),
        "evidence_count": len(evidence),
        "failure_count": len(failures),
        "image_failure_count": len(image_failures),
        "motion_evidence_requested": bool(include_motion_evidence),
        "motion_evidence_count": motion_evidence_count,
        "motion_failure_count": len(motion_failures),
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
        "--include-motion-evidence",
        action="store_true",
        help=(
            "Also derive a representative contact sheet and short compact motion sample "
            "from each exact preview_video_url."
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
    manifest = materialize(
        args.discovery_result,
        args.output_dir,
        include_motion_evidence=args.include_motion_evidence,
        frame_count=args.representative_frames,
        sample_seconds=args.motion_sample_seconds,
    )
    print(json.dumps(manifest, indent=2))
    if manifest["evidence_count"] == 0:
        raise SystemExit(4)
    if args.include_motion_evidence and manifest["motion_evidence_count"] == 0:
        # Motion being unavailable everywhere is surfaced to the caller, but image
        # evidence remains materialized for ChatGPT/Work inspection and fallback.
        raise SystemExit(5)


if __name__ == "__main__":
    main()
