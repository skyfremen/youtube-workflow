import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
import re
import subprocess
import time

from workflow_common import atomic_write_json, OUTPUT_DIR, PRODUCTION_MAX_SECONDS, env_bool, expected_video_config, load_json


def parse_rate(value):
    raw = str(value or "").strip()
    if not raw:
        return 0.0
    if "/" in raw:
        num, den = raw.split("/", 1)
        try:
            den_value = float(den)
            return float(num) / den_value if den_value else 0.0
        except ValueError:
            return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def parse_black_durations(stderr):
    return [float(x) for x in re.findall(r"black_duration:([0-9]+(?:\.[0-9]+)?)", stderr or "")]


def legacy_blackdetect(video):
    """Compatibility fallback for renders created before inline blackdetect existed."""
    black = subprocess.run([
        "ffmpeg", "-hide_banner", "-v", "info", "-i", str(video),
        "-vf", "blackdetect=d=0.50:pic_th=0.98:pix_th=0.10", "-an", "-f", "null", "-"
    ], capture_output=True, text=True)
    if black.returncode != 0:
        raise SystemExit("Render verification failed: fallback blackdetect could not decode short.mp4")
    maximum = max(parse_black_durations(black.stderr), default=0.0)
    if maximum >= 0.75:
        raise SystemExit("Render verification failed: sustained near-black section detected")
    return maximum


def resolve_blackdetect(render_meta, video, legacy_runner=legacy_blackdetect):
    """Use render-pass evidence when present; decode the full video only for legacy metadata."""
    inline_blackdetect = render_meta.get("inline_blackdetect_passed")
    if inline_blackdetect is False:
        raise SystemExit("Render verification failed: inline black detection reported a sustained near-black section")
    if inline_blackdetect is True:
        maximum = float(render_meta.get("inline_blackdetect_max_duration_seconds") or 0.0)
        if maximum >= 0.75:
            raise SystemExit("Render verification failed: inline blackdetect metadata exceeds safety threshold")
        return "inline_during_render", maximum
    return "legacy_second_pass", float(legacy_runner(video))


def main():
    verification_started = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    _request = load_json(args.request)
    video = OUTPUT_DIR / "short.mp4"
    metadata_path = OUTPUT_DIR / "render-metadata.json"
    if not video.exists() or video.stat().st_size < 100000:
        raise SystemExit("Render verification failed: short.mp4 is missing or suspiciously small")
    if not metadata_path.exists():
        raise SystemExit("Render verification failed: render-metadata.json is missing")

    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate",
        "-of", "json", str(video),
    ], capture_output=True, text=True)
    if probe.returncode != 0:
        raise SystemExit("Render verification failed: ffprobe could not read short.mp4")
    info = json.loads(probe.stdout or "{}")
    streams = info.get("streams", [])
    videos = [x for x in streams if x.get("codec_type") == "video"]
    audios = [x for x in streams if x.get("codec_type") == "audio"]
    if len(videos) != 1:
        raise SystemExit(f"Render verification failed: expected one video stream, got {len(videos)}")
    if len(audios) != 1:
        raise SystemExit(f"Render verification failed: expected exactly one narration audio stream, got {len(audios)}")
    cfg = expected_video_config()
    vs = videos[0]
    if (int(vs.get("width") or 0), int(vs.get("height") or 0)) != (cfg["width"], cfg["height"]):
        raise SystemExit(
            f"Render verification failed: expected {cfg['width']}x{cfg['height']}, got {vs.get('width')}x{vs.get('height')}"
        )
    actual_fps = parse_rate(vs.get("r_frame_rate"))
    if abs(actual_fps - float(cfg["fps"])) > 0.01:
        raise SystemExit(
            f"Render verification failed: expected {cfg['fps']} fps, got {vs.get('r_frame_rate')} ({actual_fps:.3f})"
        )
    if vs.get("codec_name") != "h264":
        raise SystemExit(f"Render verification failed: video codec must be h264, got {vs.get('codec_name')}")
    if audios[0].get("codec_name") != "aac":
        raise SystemExit(f"Render verification failed: audio codec must be aac, got {audios[0].get('codec_name')}")

    duration = float(info.get("format", {}).get("duration") or 0)
    test_mode = env_bool("STORY_TEST_MODE", False)
    if test_mode:
        max_seconds = float(os.getenv("STORY_RENDER_MAX_SECONDS", "5"))
        if duration > max_seconds + 0.55:
            raise SystemExit(
                f"Render verification failed: test duration {duration:.3f}s exceeds {max_seconds + 0.55:.3f}s tolerance"
            )
    elif duration > PRODUCTION_MAX_SECONDS:
        raise SystemExit(f"Render verification failed: production duration {duration:.3f}s exceeds {PRODUCTION_MAX_SECONDS:.0f}s")

    for fraction in (0.25, 0.50, 0.75):
        ts = max(0.05, duration * fraction)
        check = subprocess.run([
            "ffmpeg", "-v", "error", "-ss", f"{ts:.3f}", "-i", str(video),
            "-frames:v", "1", "-f", "null", "-"
        ], capture_output=True, text=True)
        if check.returncode != 0:
            raise SystemExit(f"Render verification failed: frame at {ts:.2f}s cannot be decoded")

    render_meta = load_json(metadata_path)
    blackdetect_mode, blackdetect_max = resolve_blackdetect(render_meta, video)

    if abs(float(render_meta["video_seconds"]) - duration) > 0.25:
        raise SystemExit("Render verification failed: metadata/video duration mismatch")
    render_meta.update({
        "render_verified": True,
        "render_verified_at": datetime.now(timezone.utc).isoformat(),
        "render_verification_source": "ffprobe_frame_decode_and_blackdetect",
        "render_verification_duration_seconds": round(time.monotonic() - verification_started, 6),
        "blackdetect_verification_mode": blackdetect_mode,
        "verified_blackdetect_max_duration_seconds": round(blackdetect_max, 6),
        "configured_video_seconds": render_meta["video_seconds"],
        "video_seconds": duration,
        "fps": actual_fps,
        "video_codec": vs["codec_name"],
        "audio_codec": audios[0]["codec_name"],
        "audio_stream_count": len(audios),
        "video_stream_count": len(videos),
        "narration_engine": _request["narration"]["engine"],
        "audio_source": "narration.wav only (input 3:a:0)",
        "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
    })
    atomic_write_json(metadata_path, render_meta)
    print(
        f"Render verified: {duration:.3f}s, {cfg['width']}x{cfg['height']}, "
        f"{actual_fps:.3f} fps, H.264 + one AAC narration stream; blackdetect={blackdetect_mode}."
    )


if __name__ == "__main__":
    main()
