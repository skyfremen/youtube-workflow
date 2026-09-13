"""Materialize exact-source Pexels preview evidence for ChatGPT/Work review.

This helper is intentionally planner-side and credential-free. It consumes an
immutable discovery result, downloads the exact public preview image for each
candidate into an ordinary local directory, and optionally downloads the selected
preview video. It never sets verified_preview, assigns semantic metadata, edits the
registry, or performs editorial approval.

The purpose is to remove a fragile assumption that ChatGPT/Work can visually open
provider URLs directly through a connector/browser. The planner can instead inspect
local image/video evidence produced by this ordinary Python file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

USER_AGENT = "WackyDramas/1.0 preview-review-materializer"
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_VIDEO_BYTES = 160 * 1024 * 1024


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


def materialize(discovery_result, output_dir, include_video=False):
    data = json.loads(Path(discovery_result).read_text(encoding="utf-8"))
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("discovery result candidates must be a list")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    evidence = []
    failures = []
    for candidate in candidates:
        provider_id = _safe_provider_id(candidate.get("provider_asset_id"))
        item = {"provider_asset_id": provider_id, "source_page": candidate.get("source_page")}
        try:
            image_url = _https_url(candidate.get("preview_image_url"), "preview_image_url")
            item["image"] = _download(
                image_url, output / provider_id / "preview.jpg", MAX_IMAGE_BYTES
            )
            item["image"]["source_url"] = image_url
            if include_video:
                video_url = _https_url(candidate.get("preview_video_url"), "preview_video_url")
                item["video"] = _download(
                    video_url, output / provider_id / "preview.mp4", MAX_VIDEO_BYTES
                )
                item["video"]["source_url"] = video_url
            evidence.append(item)
        except Exception as exc:
            failures.append({"provider_asset_id": provider_id, "error": str(exc)})

    manifest = {
        "schema_version": 1,
        "request_id": data.get("request_id"),
        "discovery_result": str(discovery_result),
        "evidence_count": len(evidence),
        "failure_count": len(failures),
        "evidence": evidence,
        "failures": failures,
        "rule": "Local evidence only; ChatGPT/Work must inspect pixels before verified_preview=true.",
    }
    manifest_path = output / "evidence-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Materialize Pexels preview evidence locally")
    parser.add_argument("--discovery-result", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--include-video",
        action="store_true",
        help="Also download the exact production-suitable preview rendition when image evidence is insufficient.",
    )
    args = parser.parse_args()
    manifest = materialize(args.discovery_result, args.output_dir, args.include_video)
    print(json.dumps(manifest, indent=2))
    if manifest["evidence_count"] == 0:
        raise SystemExit(4)


if __name__ == "__main__":
    main()
