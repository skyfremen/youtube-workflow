"""Append-only dispatch evidence for private orchestration state."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "content" / "recovery"
BATCH = re.compile(r"[br]_[0-9a-f]{30}")
SHA = re.compile(r"[0-9a-f]{40}")
CONTRACT = re.compile(r"[0-9a-f]{64}")
DISPATCH = re.compile(r"d_[0-9a-f]{24}")
KINDS = {"initial", "adhoc", "automatic", "no-start-retry"}


def iso_z(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def make_dispatch_id(batch_id, source_sha, contract_hash, run_id, run_attempt, kind):
    if not BATCH.fullmatch(batch_id):
        raise ValueError("invalid batch id")
    if not SHA.fullmatch(source_sha):
        raise ValueError("invalid source sha")
    if not CONTRACT.fullmatch(contract_hash):
        raise ValueError("invalid contract hash")
    if not str(run_id).isdigit() or not str(run_attempt).isdigit():
        raise ValueError("invalid private workflow identity")
    if kind not in KINDS:
        raise ValueError("invalid dispatch kind")
    raw = json.dumps(
        {
            "batch_id": batch_id,
            "source_sha": source_sha,
            "contract_hash": contract_hash,
            "run_id": str(run_id),
            "run_attempt": str(run_attempt),
            "kind": kind,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "d_" + hashlib.sha256(raw).hexdigest()[:24]


def _path(state, batch_id, dispatch_id):
    roots = {
        "prepared": "dispatch-intents",
        "dispatched": "dispatches",
        "failed": "dispatch-failures",
    }
    return RECOVERY / roots[state] / batch_id / f"{dispatch_id}.json"


def _identity(payload):
    return {
        key: payload.get(key)
        for key in (
            "schema_version",
            "batch_id",
            "dispatch_id",
            "source_sha",
            "contract_hash",
            "dispatch_kind",
            "private_workflow_run_id",
            "private_workflow_run_attempt",
        )
    }


def write_evidence(
    state,
    *,
    batch_id,
    source_sha,
    contract_hash,
    dispatch_id,
    dispatch_kind,
    private_run_id,
    private_run_attempt,
    now=None,
):
    if state not in {"prepared", "dispatched", "failed"}:
        raise ValueError("invalid evidence state")
    if not BATCH.fullmatch(batch_id) or not SHA.fullmatch(source_sha):
        raise ValueError("invalid dispatch identity")
    if not CONTRACT.fullmatch(contract_hash) or not DISPATCH.fullmatch(dispatch_id):
        raise ValueError("invalid dispatch correlation")
    if dispatch_kind not in KINDS:
        raise ValueError("invalid dispatch kind")
    if not str(private_run_id).isdigit() or not str(private_run_attempt).isdigit():
        raise ValueError("invalid private workflow identity")
    now = now or datetime.now(timezone.utc)
    timestamp_key = {
        "prepared": "prepared_at",
        "dispatched": "dispatched_at",
        "failed": "failed_at",
    }[state]
    payload = {
        "schema_version": 1,
        "state": state,
        "batch_id": batch_id,
        "dispatch_id": dispatch_id,
        "source_sha": source_sha,
        "contract_hash": contract_hash,
        "dispatch_kind": dispatch_kind,
        "private_workflow_run_id": str(private_run_id),
        "private_workflow_run_attempt": str(private_run_attempt),
        timestamp_key: iso_z(now),
    }
    path = _path(state, batch_id, dispatch_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if _identity(existing) != _identity(payload) or existing.get("state") != state:
            raise ValueError("existing dispatch evidence differs")
        return path
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("state", choices=("prepare", "accept", "fail"))
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--contract-hash", required=True)
    parser.add_argument("--dispatch-kind", required=True, choices=sorted(KINDS))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--dispatch-id", default="")
    args = parser.parse_args()

    dispatch_id = args.dispatch_id or make_dispatch_id(
        args.batch_id,
        args.source_sha,
        args.contract_hash,
        args.run_id,
        args.run_attempt,
        args.dispatch_kind,
    )
    state = {"prepare": "prepared", "accept": "dispatched", "fail": "failed"}[args.state]
    write_evidence(
        state,
        batch_id=args.batch_id,
        source_sha=args.source_sha,
        contract_hash=args.contract_hash,
        dispatch_id=dispatch_id,
        dispatch_kind=args.dispatch_kind,
        private_run_id=args.run_id,
        private_run_attempt=args.run_attempt,
    )
    print(dispatch_id)


if __name__ == "__main__":
    main()
