import subprocess


def git(args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    )


def check_immutable_changes(base, head):
    """Reject edits or deletions to append-only production JSON."""
    result = git(
        [
            "diff",
            "--name-status",
            "--no-renames",
            base,
            head,
            "--",
            "youtube-shorts-bot/content/requests",
            "youtube-shorts-bot/content/results",
            "youtube-shorts-bot/content/recovery",
            "youtube-shorts-bot/content/planning",
            "youtube-shorts-bot/content/background-sourcing",
        ]
    )
    for line in result.stdout.splitlines():
        status, path = line.split("\t", 1)
        if path.endswith(".json") and status != "A":
            raise ValueError(
                "Immutable request/result/recovery/planning/background-sourcing "
                f"file changed: {path}"
            )
