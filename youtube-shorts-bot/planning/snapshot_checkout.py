"""Verify an existing real Git checkout against an exact planner source SHA.

This compatibility helper no longer creates synthetic Git metadata. Preferred
planner execution uses a real fetched detached Git snapshot. Connector fallback
stays Git-less and passes ``rules_source_sha`` explicitly.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from planning import ranked_promotion
from planning.snapshot_precommit import verify_snapshot_manifest


def bootstrap_snapshot(rules_source_sha: str, snapshot_manifest: str):
    if not ranked_promotion.HEX40_RE.fullmatch(str(rules_source_sha or "")):
        return {
            "status": "FAIL",
            "ready": False,
            "errors": ["rules_source_sha must be a lowercase full 40-character commit SHA"],
        }

    errors = verify_snapshot_manifest(Path(snapshot_manifest), rules_source_sha)
    if errors:
        return {
            "status": "FAIL",
            "ready": False,
            "source_sha": rules_source_sha,
            "errors": errors,
        }

    root = ranked_promotion.REPO_ROOT.resolve()
    git_dir = root / ".git"
    if not git_dir.exists():
        return {
            "status": "FAIL",
            "ready": False,
            "source_sha": rules_source_sha,
            "errors": [
                "synthetic Git metadata is prohibited; use connector materialization "
                "fallback without Git metadata or a real fetched checkout"
            ],
        }

    try:
        actual = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=root,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        output = getattr(exc, "output", "") or ""
        return {
            "status": "FAIL",
            "ready": False,
            "source_sha": rules_source_sha,
            "errors": [
                f"existing .git cannot resolve/verify checkout: "
                f"{output.strip() or type(exc).__name__}"
            ],
        }

    if actual != rules_source_sha:
        return {
            "status": "FAIL",
            "ready": False,
            "source_sha": rules_source_sha,
            "resolved_head": actual,
            "errors": ["existing checkout HEAD does not match rules_source_sha"],
        }

    if dirty:
        return {
            "status": "FAIL",
            "ready": False,
            "source_sha": rules_source_sha,
            "resolved_head": actual,
            "errors": ["existing planner checkout is dirty"],
        }

    return {
        "status": "PASS",
        "ready": True,
        "source_mode": "checkout",
        "source_sha": rules_source_sha,
        "resolved_head": actual,
        "repo_root": str(root),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-source-sha", required=True)
    parser.add_argument("--snapshot-manifest", required=True)
    args = parser.parse_args()
    result = bootstrap_snapshot(args.rules_source_sha, args.snapshot_manifest)
    import json

    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
