"""Classify planner-relevant Git drift between immutable repository SHAs.

The classifier is deterministic and owns no creative decisions. It tells
ChatGPT/Work which planner inputs need to be refreshed when ``main`` advances
while a ranked pool is being authored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import defaultdict

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")

RULE_PREFIXES = (
    "docs/private/PLANNER_PROMPT.md",
    "docs/private/shared-planner-architecture.md",
    "youtube-shorts-bot/planning/",
    "youtube-shorts-bot/validation/",
    "youtube-shorts-bot/media/",
)
RULE_EXACT = {
    ".github/workflows/background-management.yml",
}
MEDIA_PREFIXES = (
    "youtube-shorts-bot/media-library/backgrounds.json",
    "youtube-shorts-bot/content/background-sourcing/",
)
HISTORY_PREFIXES = (
    "youtube-shorts-bot/analytics/",
    "youtube-shorts-bot/content/requests/",
    "youtube-shorts-bot/content/results/",
    "youtube-shorts-bot/content/planning/",
    "youtube-shorts-bot/content/planning-pools/",
)
OPERATIONAL_PREFIXES = (
    ".state/observations/",
    "youtube-shorts-bot/content/recovery/",
    "youtube-shorts-bot/content/completions/",
    "youtube-shorts-bot/content/diagnostics/",
)

FINGERPRINT_PATHS = {
    "planner_contract_digest": (
        "docs/private/PLANNER_PROMPT.md",
        "docs/private/shared-planner-architecture.md",
        "youtube-shorts-bot/planning",
        "youtube-shorts-bot/validation",
        "youtube-shorts-bot/media",
        ".github/workflows/background-management.yml",
    ),
    "media_state_digest": (
        "youtube-shorts-bot/media-library/backgrounds.json",
        "youtube-shorts-bot/content/background-sourcing",
    ),
    "creative_history_digest": (
        "youtube-shorts-bot/analytics",
        "youtube-shorts-bot/content/requests",
        "youtube-shorts-bot/content/results",
        "youtube-shorts-bot/content/planning",
        "youtube-shorts-bot/content/planning-pools",
    ),
}


def _normalize_path(path: str) -> str:
    normalized = str(path).strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def _matches(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in prefixes)


def classify_path(path: str) -> str:
    normalized = _normalize_path(path)
    if normalized in RULE_EXACT or _matches(normalized, RULE_PREFIXES):
        return "rules"
    if _matches(normalized, MEDIA_PREFIXES):
        return "media"
    if _matches(normalized, HISTORY_PREFIXES):
        return "history"
    if _matches(normalized, OPERATIONAL_PREFIXES):
        return "operational"
    return "unknown"


def classify_paths(paths) -> dict:
    grouped = defaultdict(list)
    for path in sorted({_normalize_path(item) for item in paths if str(item).strip()}):
        grouped[classify_path(path)].append(path)

    if grouped["rules"] or grouped["unknown"]:
        refresh = "full_refresh"
        actions = [
            "refresh_source_snapshot",
            "rerun_planner_contract",
            "rerun_media_readiness",
            "refresh_planner_state",
            "rerun_complete_precommit",
        ]
    elif grouped["media"]:
        refresh = "media_refresh"
        actions = [
            "refresh_media_state",
            "rerun_media_readiness",
            "revalidate_background_selections",
            "rerun_complete_precommit",
        ]
    elif grouped["history"]:
        refresh = "history_refresh"
        actions = [
            "refresh_creative_history",
            "rerun_duplicate_analytics_and_recent_background_checks",
            "rerun_complete_precommit_if_pool_bytes_change",
        ]
    elif grouped["operational"]:
        refresh = "operational_only"
        actions = ["continue_without_planner_restart"]
    else:
        refresh = "none"
        actions = ["continue"]

    return {
        "refresh": refresh,
        "actions": actions,
        "changed_paths": {
            key: grouped[key]
            for key in ("rules", "media", "history", "operational", "unknown")
        },
    }


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git command failed")
    return completed.stdout


def _require_sha(value: str) -> str:
    if not HEX40_RE.fullmatch(value or ""):
        raise ValueError("SHA must be a lowercase full 40-character Git commit SHA")
    return value


def fingerprint(sha: str, paths: tuple[str, ...]) -> str:
    _require_sha(sha)
    tree = _git("ls-tree", "-r", "--full-tree", sha, "--", *paths)
    return hashlib.sha256(tree.encode("utf-8")).hexdigest()


def fingerprints(sha: str) -> dict[str, str]:
    return {
        name: fingerprint(sha, paths)
        for name, paths in FINGERPRINT_PATHS.items()
    }


def compare(base_sha: str, head_sha: str) -> dict:
    _require_sha(base_sha)
    _require_sha(head_sha)
    changed = [
        line.strip()
        for line in _git("diff", "--name-only", base_sha, head_sha, "--").splitlines()
        if line.strip()
    ]
    result = classify_paths(changed)
    result.update(
        {
            "base_sha": base_sha,
            "head_sha": head_sha,
            "base_fingerprints": fingerprints(base_sha),
            "head_fingerprints": fingerprints(head_sha),
        }
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        help="Classify an already-known changed path without invoking Git; repeatable.",
    )
    args = parser.parse_args()

    try:
        if args.changed_path:
            result = classify_paths(args.changed_path)
            result["source"] = "supplied_changed_paths"
        else:
            if not args.base_sha or not args.head_sha:
                parser.error(
                    "--base-sha and --head-sha are required unless --changed-path is supplied"
                )
            result = compare(args.base_sha, args.head_sha)
            result["source"] = "git_compare"
    except (ValueError, RuntimeError) as exc:
        print(
            json.dumps(
                {"status": "FAIL", "errors": [str(exc)]},
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(2)

    print(json.dumps({"status": "PASS", **result}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
