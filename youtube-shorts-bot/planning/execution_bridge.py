"""Repository-side execution bridge for ChatGPT/Work planning checkpoints.

The bridge is intentionally narrow: callers commit an input envelope, GitHub Actions
runs this module from a real checkout, and commits the deterministic result. It does
not render, synthesize, upload, or replace planner semantics.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from common.runtime_contract import contract_hash
from media.background_selector import load_successful_receipts
from media.background_treatment import select_pair_treatments
from media.validate_media_library import load_registry
from planning.planning_runner import execute as execute_planning
from publishing.upload import build_upload_body
from validation.validate_content import validate_request_data

SCHEMA_VERSION = 1
EXECUTION_ID_RE = re.compile(r"pe-[A-Za-z0-9-]{8,96}")
OPERATIONS = {
    "planning.raw-filter",
    "planning.final-select",
    "background.treatment",
    "request.validate",
}
ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parents[1]


def source_sha() -> str:
    value = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("cannot resolve full checked-out source SHA")
    return value


def _require_object(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def execute_envelope(envelope):
    envelope = _require_object(envelope, "execution envelope")
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported execution bridge schema")
    execution_id = str(envelope.get("execution_id") or "")
    if not EXECUTION_ID_RE.fullmatch(execution_id):
        raise ValueError("invalid execution_id")
    operation = str(envelope.get("operation") or "")
    if operation not in OPERATIONS:
        raise ValueError("unsupported bridge operation")
    payload = _require_object(envelope.get("payload"), "payload")

    if operation == "planning.raw-filter":
        result = execute_planning("raw-filter", payload)
    elif operation == "planning.final-select":
        result = execute_planning("final-select", payload)
    elif operation == "background.treatment":
        primary_id = str(payload.get("primary_id") or "")
        backup_id = str(payload.get("backup_id") or "")
        planned = payload.get("planned_treatments") or []
        if not isinstance(planned, list):
            raise ValueError("planned_treatments must be an array")
        result = select_pair_treatments(
            load_registry(),
            primary_id,
            backup_id,
            load_successful_receipts(BASE / "content" / "results"),
            planned_treatments=planned,
        )
    else:
        request = _require_object(payload.get("request"), "payload.request")
        content_id = str(request.get("content_id") or "")
        if not content_id:
            raise ValueError("request content_id is required")
        errors = validate_request_data(
            request,
            request_path=Path(f"{content_id}.json"),
        )
        if errors:
            raise ValueError("request validation failed: " + "; ".join(errors))
        upload_body = build_upload_body(request, require_future=False)
        result = {
            "request_valid": True,
            "runtime_contract_hash": contract_hash(),
            "upload_body": upload_body,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "execution_id": execution_id,
        "operation": operation,
        "source_sha": source_sha(),
        "result": result,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.unlink(missing_ok=True)
    try:
        envelope = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = execute_envelope(envelope)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        output.unlink(missing_ok=True)
        raise SystemExit(f"planner execution bridge failed closed: {exc}") from exc


if __name__ == "__main__":
    main()
