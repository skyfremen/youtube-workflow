import argparse
import os
import subprocess
from pathlib import Path

from workflow_common import REQUESTS_DIR, result_path_for_id, validate_content_id

ALLOWED_EXTRA_PRODUCTION_PATHS = {"youtube-shorts-bot/media-library/backgrounds.json"}


def is_sensitive(path):
    if path.startswith(".github/workflows/"):
        return True
    if path.startswith("youtube-shorts-bot/"):
        return path not in ALLOWED_EXTRA_PRODUCTION_PATHS
    return False


def git(args, check=True):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def changed_files(commit):
    result = git(["diff-tree", "--no-commit-id", "--name-status", "-r", commit])
    rows = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            rows.append((parts[0], parts[-1]))
    return rows


def parent_has_path(commit, path):
    parent = git(["rev-parse", f"{commit}^"]).stdout.strip()
    result = git(["cat-file", "-e", f"{parent}:{path}"], check=False)
    return result.returncode == 0


def request_added_commit(path):
    result = git(["log", "--diff-filter=A", "--format=%H", "--", path])
    commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not commits:
        raise ValueError(f"Could not determine source commit for immutable request {path}")
    return commits[-1]


def resolve_push_request(commit):
    rows = changed_files(commit)
    request_rows = [
        (status, path) for status, path in rows
        if path.startswith("youtube-shorts-bot/content/requests/") and path.endswith(".json")
    ]
    added = [(s, p) for s, p in request_rows if s.startswith("A")]
    if len(request_rows) != 1 or len(added) != 1:
        raise ValueError(
            "Automatic ad-hoc production requires exactly one newly added "
            "youtube-shorts-bot/content/requests/*.json file in the triggering commit."
        )
    request_path = added[0][1]
    sensitive = [path for _status, path in rows if path != request_path and is_sensitive(path)]
    if sensitive:
        raise ValueError(
            "Ad-hoc production content commit also changes sensitive implementation files: "
            + ", ".join(sorted(sensitive))
        )
    if parent_has_path(commit, request_path):
        content_id = Path(request_path).stem
        raise ValueError(f"Request {content_id} already exists and is immutable.")
    return request_path


def resolve_manual_request(content_id):
    validate_content_id(content_id)
    path = REQUESTS_DIR / f"{content_id}.json"
    if not path.exists():
        raise ValueError(f"Request does not exist: {path}")
    return path.as_posix()


def check_immutable_changes(base, head):
    result = git([
        "diff", "--name-status", "--no-renames", base, head, "--",
        "youtube-shorts-bot/content/requests", "youtube-shorts-bot/content/results",
        "youtube-shorts-bot/content/recovery", "youtube-shorts-bot/content/planning",
    ])
    for line in result.stdout.splitlines():
        status, path = line.split("\t", 1)
        if path.endswith(".json") and status != "A":
            raise ValueError(f"Immutable request/result/recovery/planning file changed: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", choices=("push", "manual"), required=True)
    parser.add_argument("--commit")
    parser.add_argument("--content-id")
    parser.add_argument("--github-output", default=os.getenv("GITHUB_OUTPUT", ""))
    args = parser.parse_args()

    if args.event == "push":
        if not args.commit:
            raise SystemExit("--commit is required for push resolution")
        try:
            request_path = resolve_push_request(args.commit)
        except ValueError as exc:
            raise SystemExit(str(exc))
    else:
        if not args.content_id:
            raise SystemExit("--content-id is required for manual resolution")
        try:
            request_path = resolve_manual_request(args.content_id)
        except ValueError as exc:
            raise SystemExit(str(exc))

    content_id = Path(request_path).stem
    source_commit_sha = args.commit if args.event == "push" else request_added_commit(request_path)
    receipt = result_path_for_id(content_id)
    already_complete = receipt.exists()
    if not already_complete:
        result = git(["show", f"origin/main:{receipt.as_posix()}"], check=False)
        already_complete = result.returncode == 0

    print(f"Resolved request: {request_path}")
    print(f"already_complete={'true' if already_complete else 'false'}")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as f:
            f.write(f"request_path={request_path}\n")
            f.write(f"content_id={content_id}\n")
            f.write(f"already_complete={'true' if already_complete else 'false'}\n")
            f.write(f"source_commit_sha={source_commit_sha}\n")


if __name__ == "__main__":
    main()
