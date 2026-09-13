"""Classify planner-relevant drift between immutable repository SHAs.

The classifier is deterministic and owns no creative decisions. ChatGPT/Work
uses connector/API current-main SHA comparison plus connector-supplied changed
paths; developer/CI real-Git checkouts may still use the legacy Git comparison
helpers when Git metadata is genuinely available.
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


def _conservative_full_refresh() -> dict:
    return {
        "refresh": "full_refresh",
        "actions": [
            "refresh_source_snapshot",
            "rerun_planner_contract",
            "rerun_media_readiness",
            "refresh_planner_state",
            "rerun_complete_precommit",
        ],
        "changed_paths": {
            "rules": [],
            "media": [],
            "history": [],
            "operational": [],
            "unknown": [],
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


def classify_connector_transition(
    base_sha: str,
    current_main_sha: str,
    changed_paths=None,
) -> dict:
    """Classify a connector/API-observed current-main transition without Git.

    ``changed_paths`` should come from connector/API compare evidence. When the
    branch moved but a trustworthy path set is unavailable, the shared policy is
    deliberately conservative and performs a full refresh.
    """
    _require_sha(base_sha)
    _require_sha(current_main_sha)
    moved = base_sha != current_main_sha
    if not moved:
        result = classify_paths([])
        path_source = "not_required"
    elif changed_paths is None:
        result = _conservative_full_refresh()
        path_source = "unavailable_full_refresh"
    else:
        result = classify_paths(changed_paths)
        path_source = "connector_compare"
    result.update(
        {
            "base_sha": base_sha,
            "head_sha": current_main_sha,
            "main_changed": moved,
            "source": "connector_sha_compare",
            "changed_path_source": path_source,
        }
    )
    return result


def fingerprint(sha: str, paths: tuple[str, ...]) -> str:
    """Developer/CI real-Git fingerprint helper; not used by ChatGPT/Work."""
    _require_sha(sha)
    tree = _git("ls-tree", "-r", "--full-tree", sha, "--", *paths)
    return hashlib.sha256(tree.encode("utf-8")).hexdigest()


def fingerprints(sha: str) -> dict[str, str]:
    return {
        name: fingerprint(sha, paths)
        for name, paths in FINGERPRINT_PATHS.items()
    }


def compare(base_sha: str, head_sha: str) -> dict:
    """Developer/CI real-Git comparison retained for genuine Git checkouts."""
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
        "--connector-current-main-sha",
        help=(
            "Current main SHA returned by the authorized GitHub connector/API. "
            "This mode never invokes Git."
        ),
    )
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        help=(
            "Classify a connector/API-supplied changed path without invoking Git; "
            "repeatable."
        ),
    )
    args = parser.parse_args()

    try:
        if args.connector_current_main_sha:
            if not args.base_sha:
                parser.error(
                    "--base-sha is required with --connector-current-main-sha"
                )
            result = classify_connector_transition(
                args.base_sha,
                args.connector_current_main_sha,
                args.changed_path if args.changed_path else None,
            )
        elif args.changed_path:
            result = classify_paths(args.changed_path)
            result["source"] = "supplied_changed_paths"
        else:
            if not args.base_sha or not args.head_sha:
                parser.error(
                    "--base-sha and --head-sha are required unless connector "
                    "current-main SHA or --changed-path is supplied"
                )
            result = compare(args.base_sha, args.head_sha)
            result["source"] = "git_compare_developer_mode"
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
