"""Build and verify the private content-to-video reconciliation index.

The index is derived only from trusted private upload evidence and verified
receipts. It is append-only per content ID and never silently overwrites a
conflicting mapping.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
RECOVERY = CONTENT / "recovery"
RESULTS = CONTENT / "results"
INDEX = RECOVERY / "index"
BOOTSTRAP = INDEX / "bootstrap.json"
CID = re.compile(r"wd-[A-Za-z0-9-]+")
VIDEO = re.compile(r"[A-Za-z0-9_-]{11}")
SHA = re.compile(r"[0-9a-f]{40}")


class IndexConflict(RuntimeError):
    pass


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _identity(payload):
    content_id = str(payload.get("content_id", ""))
    request_path = str(payload.get("request_path", ""))
    request_blob_sha = str(payload.get("request_blob_sha", ""))
    source_commit_sha = str(payload.get("source_commit_sha", ""))
    if not CID.fullmatch(content_id):
        raise IndexConflict("invalid content identity")
    if request_path != f"youtube-shorts-bot/content/requests/{content_id}.json":
        raise IndexConflict(f"request path mismatch for {content_id}")
    if not SHA.fullmatch(request_blob_sha) or not SHA.fullmatch(source_commit_sha):
        raise IndexConflict(f"invalid immutable SHA for {content_id}")
    return {
        "content_id": content_id,
        "request_path": request_path,
        "request_blob_sha": request_blob_sha,
        "source_commit_sha": source_commit_sha,
    }


def _mapping(identity, video_id, channel_id):
    if not VIDEO.fullmatch(str(video_id or "")):
        raise IndexConflict(f"invalid video ID for {identity['content_id']}")
    if not str(channel_id or ""):
        raise IndexConflict(f"missing channel ID for {identity['content_id']}")
    return {
        "schema_version": 1,
        "record_type": "mapping",
        **identity,
        "youtube_video_id": str(video_id),
        "expected_channel_id": str(channel_id),
    }


def from_upload(payload):
    if payload.get("record_type") != "upload":
        raise IndexConflict("upload evidence has unexpected record type")
    identity = _identity(payload)
    return _mapping(
        identity,
        payload.get("youtube_video_id"),
        payload.get("expected_channel_id"),
    )


def from_receipt(payload):
    verification = payload.get("verification", {})
    if (
        verification.get("passed") is not True
        or not str(payload.get("verification_state", "")).startswith("verified_scheduled")
    ):
        return None
    identity = _identity(payload)
    return _mapping(
        identity,
        payload.get("youtube_video_id"),
        payload.get("youtube_channel_id"),
    )


def _merge(records, candidate, source):
    content_id = candidate["content_id"]
    prior = records.get(content_id)
    if prior is not None and prior != candidate:
        raise IndexConflict(
            f"conflicting mapping for {content_id}: {source} disagrees with trusted evidence"
        )
    records[content_id] = candidate


def collect(root=ROOT):
    root = Path(root)
    recovery = root / "content" / "recovery"
    results = root / "content" / "results"
    records = {}
    upload_count = 0
    receipt_count = 0

    for path in sorted(recovery.glob("*/upload.json")):
        candidate = from_upload(load(path))
        _merge(records, candidate, str(path))
        upload_count += 1

    for path in sorted(results.glob("*.json")):
        candidate = from_receipt(load(path))
        if candidate is None:
            continue
        _merge(records, candidate, str(path))
        receipt_count += 1

    return records, upload_count, receipt_count


def bootstrap(root=ROOT, *, write=False, cutover_source_commit_sha=None):
    root = Path(root)
    index = root / "content" / "recovery" / "index"
    bootstrap_path = index / "bootstrap.json"
    records, upload_count, receipt_count = collect(root)
    created = 0
    reused = 0

    for content_id, candidate in sorted(records.items()):
        path = index / f"{content_id}.json"
        if path.exists():
            if load(path) != candidate:
                raise IndexConflict(f"existing index mapping conflicts for {content_id}")
            reused += 1
        elif write:
            dump(path, candidate)
            created += 1

    if write:
        missing = [
            content_id for content_id, candidate in records.items()
            if not (index / f"{content_id}.json").exists()
            or load(index / f"{content_id}.json") != candidate
        ]
        if missing:
            raise IndexConflict("index write verification failed")

        if bootstrap_path.exists():
            marker = load(bootstrap_path)
            if (
                marker.get("schema_version") != 1
                or marker.get("status") != "complete"
                or marker.get("conflicts") != 0
            ):
                raise IndexConflict("existing bootstrap marker is invalid")
        else:
            if not SHA.fullmatch(str(cutover_source_commit_sha or "")):
                raise IndexConflict("first bootstrap write requires exact cutover source commit SHA")
            dump(
                bootstrap_path,
                {
                    "schema_version": 1,
                    "status": "complete",
                    "historical_mapping_count": len(records),
                    "upload_record_count": upload_count,
                    "verified_receipt_count": receipt_count,
                    "conflicts": 0,
                    "youtube_api_required": False,
                    "source": "trusted_private_evidence",
                    "cutover_source_commit_sha": cutover_source_commit_sha,
                },
            )

    return {
        "mapping_count": len(records),
        "upload_record_count": upload_count,
        "verified_receipt_count": receipt_count,
        "created": created,
        "reused": reused,
        "conflicts": 0,
        "youtube_api_required": False,
        "bootstrap_present": bootstrap_path.exists(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--cutover-source-commit-sha")
    args = parser.parse_args()
    report = bootstrap(
        write=args.write,
        cutover_source_commit_sha=args.cutover_source_commit_sha,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
