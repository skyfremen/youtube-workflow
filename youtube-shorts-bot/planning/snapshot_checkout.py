"""Bootstrap Git-compatible HEAD metadata for an isolated ChatGPT snapshot.

The snapshot is assembled from files fetched at one immutable GitHub commit and
verified with ``planning.snapshot_precommit`` manifest logic. This command does
not clone, fetch, authenticate to GitHub, or create commit objects. It creates
only enough temporary .git metadata for ``git rev-parse HEAD`` to attest the
already-verified source SHA used by the planner pre-commit validators.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from planning import ranked_promotion
from planning.snapshot_precommit import verify_snapshot_manifest

SNAPSHOT_BRANCH = "chatgpt-snapshot"


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
    head_file = git_dir / "HEAD"

    if git_dir.exists():
        # Never rewrite a real checkout. Existing Git metadata must already
        # resolve to the requested source SHA.
        try:
            import subprocess

            actual = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
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
                "errors": [f"existing .git cannot resolve HEAD: {output.strip() or type(exc).__name__}"],
            }
        if actual != rules_source_sha:
            return {
                "status": "FAIL",
                "ready": False,
                "source_sha": rules_source_sha,
                "resolved_head": actual,
                "errors": ["existing checkout HEAD does not match rules_source_sha"],
            }
        return {
            "status": "PASS",
            "ready": True,
            "source_mode": "checkout",
            "source_sha": rules_source_sha,
            "resolved_head": actual,
            "repo_root": str(root),
        }

    ref_dir = git_dir / "refs" / "heads"
    ref_dir.mkdir(parents=True, exist_ok=False)
    (git_dir / "config").write_text(
        "[core]\n\trepositoryformatversion = 0\n\tbare = false\n",
        encoding="utf-8",
    )
    (ref_dir / SNAPSHOT_BRANCH).write_text(rules_source_sha + "\n", encoding="ascii")
    head_file.write_text(f"ref: refs/heads/{SNAPSHOT_BRANCH}\n", encoding="ascii")
    (git_dir / "CHATGPT_SNAPSHOT").write_text(
        json.dumps(
            {
                "source_sha": rules_source_sha,
                "snapshot_manifest": str(Path(snapshot_manifest).resolve()),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "status": "PASS",
        "ready": True,
        "source_mode": "github_snapshot",
        "source_sha": rules_source_sha,
        "resolved_head": rules_source_sha,
        "repo_root": str(root),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-source-sha", required=True)
    parser.add_argument("--snapshot-manifest", required=True)
    args = parser.parse_args()
    result = bootstrap_snapshot(args.rules_source_sha, args.snapshot_manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
