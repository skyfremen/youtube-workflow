import argparse
import subprocess
from pathlib import Path

from validate_media_library import load_registry, validate_request_backgrounds
from workflow_common import OUTPUT_DIR, atomic_write_json, load_json

BASE = Path(__file__).parent
TMP = Path("/tmp/wacky-dramas-media-preflight.bin")


def preflight(url):
    cmd = [
        "curl", "-L", "--fail-with-body", "--silent", "--show-error",
        "--connect-timeout", "15", "--max-time", "35", "--range", "0-65535",
        "-A", "Mozilla/5.0", "-o", str(TMP), "-w", "%{http_code} %{content_type}", str(url),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "curl failed").strip()
    parts = (result.stdout or "").strip().split(" ", 1)
    code = parts[0] if parts else ""
    ctype = parts[1].lower() if len(parts) > 1 else ""
    if not code.startswith("2"):
        return False, f"HTTP {code}"
    if "text/html" in ctype:
        return False, "returned HTML instead of video media"
    return True, f"HTTP {code}, {ctype or 'unknown content-type'}"


def download(asset, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl", "-L", "--fail-with-body", "--silent", "--show-error",
        "--retry", "3", "--retry-delay", "2", "--retry-all-errors",
        "--connect-timeout", "20", "--max-time", "180", "-A", "Mozilla/5.0",
        "-o", str(target), str(asset["direct_url"]),
    ]
    subprocess.run(cmd, check=True)
    if not target.exists() or target.stat().st_size < 10000:
        raise RuntimeError(f"Downloaded background {asset['id']} is suspiciously small")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_type", "-of", "default=nw=1:nk=1", str(target)],
        capture_output=True, text=True,
    )
    if probe.returncode != 0 or "video" not in probe.stdout:
        raise RuntimeError(f"Background {asset['id']} is not a decodable video")


def resolve(request_path, registry_path=None, do_download=True, do_preflight=True):
    request = load_json(request_path)
    registry = load_registry(registry_path or BASE / "media-library" / "backgrounds.json")
    primary, backup = validate_request_backgrounds(request, registry)
    failures = []
    for selection, asset in (("primary", primary), ("backup", backup)):
        if do_preflight:
            ok, detail = preflight(asset["direct_url"])
            if not ok:
                failures.append(f"{selection} {asset['id']}: {detail}")
                continue
        else:
            detail = "registry-only resolution; network preflight skipped"
        if do_download:
            try:
                download(asset, OUTPUT_DIR / "background.asset")
            except (subprocess.CalledProcessError, RuntimeError) as exc:
                failures.append(f"{selection} {asset['id']}: full download failed: {exc}")
                continue
        result = {
            "requested_primary_id": primary["id"],
            "requested_backup_id": backup["id"],
            "background_asset_id": asset["id"],
            "background_selection": selection,
            "source": asset["source"],
            "source_page": asset["source_page"],
            "direct_url": asset["direct_url"],
            "license": asset["license"],
            "preflight": detail,
        }
        atomic_write_json(OUTPUT_DIR / "background_selection.json", result)
        print(f"Selected {selection} background {asset['id']}: {detail}")
        return result
    raise RuntimeError("Both background choices failed preflight/download: " + "; ".join(failures))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--registry")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()
    try:
        resolve(
            args.request,
            args.registry,
            do_download=not args.no_download,
            do_preflight=not args.skip_preflight,
        )
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
