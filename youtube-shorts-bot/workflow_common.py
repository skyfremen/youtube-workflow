import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
REQUESTS_DIR = BASE / "content" / "requests"
RESULTS_DIR = BASE / "content" / "results"
PLANNING_DIR = BASE / "content" / "planning"
OUTPUT_DIR = Path(os.getenv("STORY_OUTPUT_DIR", str(BASE / "output")))
CONTENT_ID_RE = re.compile(r"^wd-\d{8}T\d{6}-[a-z0-9]+(?:-[a-z0-9]+)*-[a-z0-9]{6}$")
PRODUCTION_MAX_SECONDS = 178.0
PRODUCTION_TARGET_MIN_SECONDS = 120.0
PRODUCTION_TARGET_MAX_SECONDS = 175.0
START_LEAD_SECONDS = 0.50
END_TAIL_SECONDS = 0.35
PRODUCTION_ENCODE_SAFETY_SECONDS = 0.10
YOUTUBE_TAG_MAX_CHARS = 30
EXPECTED_YOUTUBE_CHANNEL_ID = "UCvrq2m9G4yrwPfL_X-QPzMA"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def request_content_id(data):
    return str(data.get("content_id", "")).strip()


def validate_content_id(content_id):
    if not CONTENT_ID_RE.fullmatch(str(content_id or "").strip()):
        raise ValueError("content_id must match wd-YYYYMMDDTHHMMSS-topic-slug-random6")
    return content_id


def marker_tag(content_id):
    """Return a deterministic non-viewer-facing YouTube recovery tag."""
    validate_content_id(content_id)
    digest = hashlib.sha256(content_id.encode("utf-8")).hexdigest()[:20]
    marker = f"wd-id-{digest}"
    if len(marker) > YOUTUBE_TAG_MAX_CHARS:
        raise AssertionError("Recovery marker unexpectedly exceeds local tag budget")
    return marker


def request_path_for_id(content_id):
    validate_content_id(content_id)
    return REQUESTS_DIR / f"{content_id}.json"


def result_path_for_id(content_id):
    validate_content_id(content_id)
    return RESULTS_DIR / f"{content_id}.json"


def ensure_request_path_matches(path, data):
    path = Path(path)
    content_id = request_content_id(data)
    validate_content_id(content_id)
    expected = f"{content_id}.json"
    if path.name != expected:
        raise ValueError(f"Request filename must be {expected}")
    return content_id


def git_blob_sha(path, ref="HEAD"):
    path = Path(path)
    try:
        relative = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        relative = path.as_posix()
    result = subprocess.run(["git", "rev-parse", f"{ref}:{relative}"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    raw = path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def expected_video_config():
    return {
        "width": int(os.getenv("VIDEO_WIDTH", "720")),
        "height": int(os.getenv("VIDEO_HEIGHT", "1280")),
        "fps": int(os.getenv("VIDEO_FPS", "30")),
    }


def load_recent_results(limit=50):
    records = []
    if not RESULTS_DIR.exists():
        return records
    for path in sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            records.append(data)
        if len(records) >= limit:
            break
    return records
