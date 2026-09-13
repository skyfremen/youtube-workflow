"""Verified pre-commit validation for isolated ChatGPT repository snapshots.

ChatGPT/Work may materialize planner inputs from one explicit immutable GitHub
commit without carrying a .git directory. A snapshot manifest records that
commit and the Git blob SHA for every materialized repository file. This module
verifies those bytes first, then reuses the canonical Daily/Ad-hoc validator.

Only the checkout-specific HEAD proof is replaced. Schema, pool, media,
uniqueness, publication and candidate validation remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from planning import adhoc_precommit, daily_precommit
from planning import ranked_promotion

MANIFEST_VERSION = 1


def _git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def verify_snapshot_manifest(manifest_path: Path, rules_source_sha: str):
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"cannot read snapshot manifest {manifest_path}: {exc}"]

    errors = []
    if manifest.get("schema_version") != MANIFEST_VERSION:
        errors.append(f"snapshot manifest schema_version must be {MANIFEST_VERSION}")
    if manifest.get("source_sha") != rules_source_sha:
        errors.append("snapshot manifest source_sha must equal rules_source_sha")
    if not ranked_promotion.HEX40_RE.fullmatch(str(rules_source_sha or "")):
        errors.append("rules_source_sha must be a lowercase full 40-character commit SHA")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        errors.append("snapshot manifest files must be a non-empty list")
        return errors

    seen = set()
    root = ranked_promotion.REPO_ROOT.resolve()
    for index, item in enumerate(files):
        if not isinstance(item, dict) or set(item) != {"path", "blob_sha"}:
            errors.append(f"snapshot manifest files[{index}] must contain path and blob_sha")
            continue
        raw_path = item.get("path")
        blob_sha = str(item.get("blob_sha", ""))
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(f"snapshot manifest files[{index}].path must be non-empty")
            continue
        pure = PurePosixPath(raw_path)
        if pure.is_absolute() or ".." in pure.parts:
            errors.append(f"snapshot manifest path is not repository-relative: {raw_path}")
            continue
        if raw_path in seen:
            errors.append(f"snapshot manifest contains duplicate path: {raw_path}")
            continue
        seen.add(raw_path)
        if not ranked_promotion.HEX40_RE.fullmatch(blob_sha):
            errors.append(f"snapshot manifest blob_sha is invalid for {raw_path}")
            continue
        path = (root / raw_path).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            errors.append(f"snapshot manifest path escapes repository root: {raw_path}")
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            errors.append(f"snapshot file unavailable {raw_path}: {exc}")
            continue
        actual = _git_blob_sha(data)
        if actual != blob_sha:
            errors.append(
                f"snapshot blob mismatch for {raw_path}: expected {blob_sha}, got {actual}"
            )
    return errors


def validate_snapshot(kind, pool, rules_source_sha, manifest_path, *, raw_bytes=b""):
    manifest_errors = verify_snapshot_manifest(Path(manifest_path), rules_source_sha)
    if manifest_errors:
        return {
            "status": "FAIL",
            "commit_allowed": False,
            "source_mode": "github_snapshot",
            "rules_source_sha": rules_source_sha,
            "pool_errors": manifest_errors,
            "candidate_results": [],
        }

    validator = {
        "adhoc": adhoc_precommit.validate_draft,
        "daily": daily_precommit.validate_draft,
    }[kind]
    result = validator(
        pool,
        rules_source_sha,
        raw_bytes=raw_bytes,
        check_checkout_head=False,
    )
    result["source_mode"] = "github_snapshot"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=("adhoc", "daily"))
    parser.add_argument("--pool", required=True)
    parser.add_argument("--rules-source-sha", required=True)
    parser.add_argument("--snapshot-manifest", required=True)
    args = parser.parse_args()

    path = Path(args.pool)
    try:
        raw = path.read_bytes()
        pool = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = {
            "status": "FAIL",
            "commit_allowed": False,
            "source_mode": "github_snapshot",
            "pool_errors": [f"cannot read planning draft {path}: {exc}"],
            "candidate_results": [],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(2)

    result = validate_snapshot(
        args.kind,
        pool,
        args.rules_source_sha,
        args.snapshot_manifest,
        raw_bytes=raw,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
