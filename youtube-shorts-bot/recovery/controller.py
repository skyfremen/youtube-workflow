"""Private, fail-closed automatic recovery controller."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CID = re.compile(r"wd-[A-Za-z0-9-]+")
SHA = re.compile(r"[0-9a-f]{40}")
VIDEO = re.compile(r"[A-Za-z0-9_-]{11}")
BATCH = re.compile(r"[br]_[0-9a-f]{30}")


@dataclass(frozen=True)
class Policy:
    active_grace_minutes: int = 210
    schedule_buffer_minutes: int = 10
    max_automatic_attempts: int = 3
    retry_backoff_minutes: tuple[int, ...] = (0, 120, 240)


@dataclass(frozen=True)
class Snapshot:
    content_id: str
    source_commit_sha: str
    source_started_at: datetime
    publish_at: datetime
    receipt_state: str
    has_intent: bool
    has_upload: bool
    automatic_attempts: int
    latest_batch_id: str
    latest_batch_started_at: datetime
    latest_event: str
    latest_event_at: datetime | None
    latest_retryable: bool | None
    latest_error_code: str | None
    latest_stage: str | None
    terminal_exists: bool = False
    forced_source_failure: bool = False


@dataclass(frozen=True)
class Decision:
    state: str
    reason: str
    dispatch: bool = False
    terminal: bool = False


def parse_instant(raw):
    value = str(raw or "")
    if not value.endswith("Z"):
        raise ValueError("timestamp must end in Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def iso_z(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def blob_sha(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def normal_batch_id(source_sha):
    if not SHA.fullmatch(source_sha):
        raise ValueError("invalid source SHA")
    return "b_" + hashlib.sha256(source_sha.encode()).hexdigest()[:30]


def automatic_batch_id(items):
    core = [
        {
            "content_id": item["content_id"],
            "source_commit_sha": item["source_commit_sha"],
            "automatic_attempt": int(item["automatic_attempt"]),
        }
        for item in sorted(items, key=lambda item: item["content_id"])
    ]
    raw = json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    return "r_" + hashlib.sha256(raw).hexdigest()[:30]


def decide(s, now, policy):
    now = now.astimezone(timezone.utc)
    if s.receipt_state == "valid":
        return Decision("completed", "authoritative_receipt")
    if s.receipt_state == "invalid":
        return Decision("terminal", "invalid_immutable_receipt", terminal=True)
    if s.terminal_exists:
        return Decision("terminal", "terminal_state_exists")

    age = now - s.latest_batch_started_at.astimezone(timezone.utc)
    if s.latest_event == "none" and not s.forced_source_failure:
        if age < timedelta(minutes=policy.active_grace_minutes):
            return Decision("active", "production_or_recovery_still_within_grace")

    durable = s.has_intent or s.has_upload
    if s.publish_at <= now + timedelta(minutes=policy.schedule_buffer_minutes) and not durable:
        return Decision("terminal", "scheduled_window_closed_without_upload_evidence", terminal=True)

    if s.latest_event == "diagnostic":
        if s.latest_retryable is False:
            return Decision("terminal", "latest_failure_is_non_retryable", terminal=True)
        if s.latest_retryable is None:
            return Decision("terminal", "latest_failure_retryability_unknown", terminal=True)

    if s.automatic_attempts >= policy.max_automatic_attempts:
        return Decision("terminal", "maximum_automatic_attempts_reached", terminal=True)

    if s.latest_event == "diagnostic" and s.latest_retryable is True:
        index = min(s.automatic_attempts, len(policy.retry_backoff_minutes) - 1)
        delay = timedelta(minutes=policy.retry_backoff_minutes[index])
        if now - (s.latest_event_at or s.latest_batch_started_at) < delay:
            return Decision("pending", "retry_backoff_not_elapsed")

    if durable:
        return Decision("recoverable", "durable_upload_state_needs_reconciliation", True)
    if s.forced_source_failure:
        return Decision("recoverable", "private_dispatch_failed", True)
    if s.latest_event == "diagnostic":
        return Decision("recoverable", "retryable_runtime_failure", True)
    if s.latest_event == "completion":
        return Decision("recoverable", "batch_completed_without_authoritative_receipt", True)
    return Decision("recoverable", "stale_unresolved_request", True)


class Repository:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.repo = self.root.parent
        self.content = self.root / "content"
        self.requests = self.content / "requests"
        self.results = self.content / "results"
        self.recovery = self.content / "recovery"
        self.batches = self.recovery / "batches"
        self.terminal = self.recovery / "terminal"
        self.diagnostics = self.content / "diagnostics"
        self.completions = self.content / "completions"

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def relative(self, path):
        return path.resolve().relative_to(self.repo).as_posix()

    def added_commit(self, path):
        commits = self.git("log", "--diff-filter=A", "--format=%H", "--", self.relative(path)).splitlines()
        if not commits or not SHA.fullmatch(commits[-1]):
            raise ValueError("cannot resolve immutable request source")
        return commits[-1]

    def commit_time(self, sha):
        return datetime.fromisoformat(self.git("show", "-s", "--format=%cI", sha)).astimezone(timezone.utc)

    def path_time(self, path, fallback):
        try:
            value = self.git("log", "-1", "--format=%cI", "--", self.relative(path))
            return datetime.fromisoformat(value).astimezone(timezone.utc) if value else fallback
        except (subprocess.CalledProcessError, ValueError):
            return fallback

    @staticmethod
    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))

    def receipt_state(self, request_path, source_sha):
        path = self.results / request_path.name
        if not path.exists():
            return "missing"
        try:
            receipt = self.load(path)
            valid = (
                receipt.get("content_id") == request_path.stem
                and receipt.get("request_path") == f"youtube-shorts-bot/content/requests/{request_path.name}"
                and receipt.get("request_blob_sha") == blob_sha(request_path.read_bytes())
                and receipt.get("source_commit_sha") == source_sha
                and receipt.get("verification", {}).get("passed") is True
                and str(receipt.get("verification_state", "")).startswith("verified_scheduled")
                and VIDEO.fullmatch(str(receipt.get("youtube_video_id", ""))) is not None
            )
        except (OSError, ValueError, json.JSONDecodeError):
            valid = False
        return "valid" if valid else "invalid"

    def manifests(self):
        for path in sorted(self.batches.glob("*.json")) if self.batches.exists() else []:
            try:
                payload = self.load(path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if BATCH.fullmatch(str(payload.get("batch_id", ""))):
                yield path, payload

    def batches_for(self, content_id, source_sha):
        normal_started = self.commit_time(source_sha)
        batches = [{"batch_id": normal_batch_id(source_sha), "started_at": normal_started,
                    "automatic": False, "automatic_attempt": 0}]
        for path, payload in self.manifests():
            item = next((x for x in payload.get("items", []) if x.get("content_id") == content_id), None)
            if not item:
                continue
            batches.append({
                "batch_id": payload["batch_id"],
                "started_at": self.path_time(path, normal_started),
                "automatic": payload.get("recovery_control", {}).get("kind") == "automatic",
                "automatic_attempt": int(item.get("automatic_attempt", 0) or 0),
            })
        return batches

    def batch_event(self, batch):
        events = []
        completion = self.completions / f"{batch['batch_id']}.json"
        if completion.exists():
            events.append({"kind": "completion", "at": self.path_time(completion, batch["started_at"]),
                           "retryable": None, "error_code": None, "stage": None})
        diag_dir = self.diagnostics / batch["batch_id"]
        if diag_dir.exists():
            for path in diag_dir.glob("*.json"):
                try:
                    payload = self.load(path)
                except (OSError, ValueError, json.JSONDecodeError):
                    continue
                retryable = payload.get("retryable")
                events.append({
                    "kind": "diagnostic", "at": self.path_time(path, batch["started_at"]),
                    "retryable": retryable if isinstance(retryable, bool) else None,
                    "error_code": str(payload.get("error_code") or "") or None,
                    "stage": str(payload.get("stage") or "") or None,
                })
        return max(events, key=lambda x: x["at"]) if events else {
            "kind": "none", "at": None, "retryable": None, "error_code": None, "stage": None,
        }

    def snapshot(self, request_path, *, now, failed_source_sha=""):
        request = self.load(request_path)
        content_id = str(request.get("content_id", ""))
        if content_id != request_path.stem or not CID.fullmatch(content_id):
            raise ValueError("invalid immutable request identity")
        publication = request.get("publication")
        if not isinstance(publication, dict) or publication.get("mode") != "scheduled":
            raise ValueError("automatic recovery requires scheduled publication")
        source_sha = self.added_commit(request_path)
        source_started = self.commit_time(source_sha)
        batches = self.batches_for(content_id, source_sha)
        latest = max(batches, key=lambda x: x["started_at"])
        event = self.batch_event(latest)
        attempts = max([x["automatic_attempt"] for x in batches if x["automatic"]] or [0])
        return Snapshot(
            content_id, source_sha, source_started, parse_instant(publication.get("publish_at")),
            self.receipt_state(request_path, source_sha),
            (self.recovery / content_id / "intent.json").is_file(),
            (self.recovery / content_id / "upload.json").is_file(),
            attempts, latest["batch_id"], latest["started_at"], event["kind"], event["at"],
            event["retryable"], event["error_code"], event["stage"],
            (self.terminal / f"{content_id}.json").is_file(), source_sha == failed_source_sha,
        )

    def write_terminal(self, s, decision, *, now, policy):
        path = self.terminal / f"{s.content_id}.json"
        if path.exists():
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1, "content_id": s.content_id, "source_commit_sha": s.source_commit_sha,
            "state": "terminal", "reason": decision.reason, "detected_at": iso_z(now),
            "automatic_attempts": s.automatic_attempts, "latest_batch_id": s.latest_batch_id,
            "latest_error_code": s.latest_error_code, "latest_stage": s.latest_stage,
            "latest_retryable": s.latest_retryable, "publish_at": iso_z(s.publish_at),
            "manual_recovery_available": True,
            "policy": {"active_grace_minutes": policy.active_grace_minutes,
                       "schedule_buffer_minutes": policy.schedule_buffer_minutes,
                       "max_automatic_attempts": policy.max_automatic_attempts},
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def write_batch(self, recoverable, *, now, policy):
        items = [{"content_id": s.content_id, "source_commit_sha": s.source_commit_sha,
                  "automatic_attempt": s.automatic_attempts + 1, "reason": d.reason}
                 for s, d in sorted(recoverable, key=lambda x: x[0].content_id)]
        batch_id = automatic_batch_id(items)
        path = self.batches / f"{batch_id}.json"
        if path.exists():
            existing = self.load(path)
            old = [(x.get("content_id"), x.get("source_commit_sha"), x.get("automatic_attempt"))
                   for x in existing.get("items", [])]
            new = [(x["content_id"], x["source_commit_sha"], x["automatic_attempt"]) for x in items]
            if existing.get("batch_id") != batch_id or old != new:
                raise ValueError("existing automatic recovery manifest differs")
            return batch_id, path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": 1, "batch_id": batch_id, "items": items,
                   "recovery_control": {"kind": "automatic", "created_at": iso_z(now),
                    "policy": {"active_grace_minutes": policy.active_grace_minutes,
                               "schedule_buffer_minutes": policy.schedule_buffer_minutes,
                               "max_automatic_attempts": policy.max_automatic_attempts,
                               "retry_backoff_minutes": list(policy.retry_backoff_minutes)}}}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return batch_id, path


def reconcile(repo, *, now, policy, write, failed_source_sha=""):
    decisions, recoverable, terminal = [], [], []
    for path in sorted(repo.requests.glob("*.json")):
        try:
            snap = repo.snapshot(path, now=now, failed_source_sha=failed_source_sha)
            decision = decide(snap, now, policy)
        except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
            decisions.append({"content_id": path.stem, "state": "terminal",
                              "reason": f"invalid_private_state:{type(exc).__name__}"})
            continue
        decisions.append({"content_id": snap.content_id, "state": decision.state,
                          "reason": decision.reason, "automatic_attempts": snap.automatic_attempts,
                          "latest_batch_id": snap.latest_batch_id})
        if decision.dispatch:
            recoverable.append((snap, decision))
        elif decision.terminal and not snap.terminal_exists:
            terminal.append((snap, decision))

    recoverable = recoverable[:24]
    written, batch_id = [], None
    if write:
        for snap, decision in terminal:
            written.append(str(repo.write_terminal(snap, decision, now=now, policy=policy)))
        if recoverable:
            batch_id, path = repo.write_batch(recoverable, now=now, policy=policy)
            written.append(str(path))
    return {"schema_version": 1, "evaluated_at": iso_z(now), "dispatch": bool(recoverable),
            "batch_id": batch_id, "item_count": len(recoverable),
            "content_ids": [s.content_id for s, _ in recoverable], "terminal_count": len(terminal),
            "written": written, "decisions": decisions}


def policy_from_env():
    backoff = tuple(int(x) for x in os.getenv("RECOVERY_BACKOFF_MINUTES", "0,120,240").split(",") if x.strip())
    policy = Policy(int(os.getenv("RECOVERY_ACTIVE_GRACE_MINUTES", "210")),
                    int(os.getenv("RECOVERY_SCHEDULE_BUFFER_MINUTES", "10")),
                    int(os.getenv("RECOVERY_MAX_AUTOMATIC_ATTEMPTS", "3")), backoff)
    if policy.active_grace_minutes < 30 or policy.schedule_buffer_minutes < 0 \
            or not 1 <= policy.max_automatic_attempts <= 10 or not backoff:
        raise ValueError("invalid automatic recovery policy")
    return policy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--failed-source-sha", default="")
    parser.add_argument("--now", default="")
    args = parser.parse_args()
    if args.failed_source_sha and not SHA.fullmatch(args.failed_source_sha):
        raise SystemExit("failed source SHA must be an exact 40-character SHA")
    now = parse_instant(args.now) if args.now else datetime.now(timezone.utc)
    result = reconcile(Repository(), now=now, policy=policy_from_env(), write=args.write,
                       failed_source_sha=args.failed_source_sha)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
