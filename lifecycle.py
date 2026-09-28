"""Deterministic, read-only audit of immutable production lifecycle records."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

CID_RE = re.compile(r"^wd-[0-9a-f]{24}$")
MAX_ERRORS = 20


def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _blob(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def _read(path, errors, label):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: invalid JSON ({type(exc).__name__})")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label}: expected JSON object")
        return None
    return value


def _evidence_errors(evidence, execution):
    version = evidence.get("evidence_version")
    if version == 2:
        fields = (
            "execution_id",
            "content_id",
            "request_id",
            "request_path",
            "request_source_sha",
            "request_blob_sha",
            "item_blob_sha",
        )
        expected = {field: execution.get(field) for field in fields}
    elif version == 1:
        cid = execution.get("content_id")
        if execution.get("execution_version") == 1:
            expected = {
                "content_id": cid,
                "request_path": execution.get("request_path"),
                "request_blob_sha": execution.get("request_blob_sha"),
                "source_commit_sha": execution.get("request_source_sha"),
            }
        else:
            expected = {
                "content_id": cid,
                "request_path": f"content/requests/{cid}.json",
                "request_blob_sha": execution.get("item_blob_sha"),
                "source_commit_sha": execution.get("request_source_sha"),
            }
    else:
        return ["upload evidence has unsupported evidence_version"]
    return [
        f"upload evidence {field} does not match execution"
        for field, value in expected.items()
        if evidence.get(field) != value
    ]


def audit_lifecycle(root: Path) -> dict:
    """Return lifecycle classifications without writing files or using the network."""
    root = Path(root)
    request_records = defaultdict(list)
    executions = defaultdict(list)
    uploads = {}
    upload_errors = defaultdict(list)
    results = {}
    global_errors = []

    for path in sorted((root / "content/requests").glob("*.json")):
        errors = []
        request = _read(path, errors, path.relative_to(root).as_posix())
        if request is None:
            global_errors.extend(errors)
            continue
        if request.get("request_version") == 1 and CID_RE.fullmatch(str(request.get("content_id") or "")):
            request_records[request["content_id"]].append(
                {"request": request, "item": request, "path": path.relative_to(root).as_posix(), "raw": path.read_bytes()}
            )
            continue
        items = request.get("items")
        if not isinstance(items, list):
            global_errors.append(f"{path.relative_to(root).as_posix()}: items must be an array")
            continue
        raw = path.read_bytes()
        for item in items:
            cid = item.get("content_id") if isinstance(item, dict) else None
            if not CID_RE.fullmatch(str(cid or "")):
                global_errors.append(f"{path.relative_to(root).as_posix()}: item has invalid content_id")
                continue
            request_records[cid].append(
                {
                    "request": request,
                    "item": item,
                    "path": path.relative_to(root).as_posix(),
                    "raw": raw,
                }
            )

    for path in sorted((root / "content/executions").glob("*.json")):
        errors = []
        execution = _read(path, errors, path.relative_to(root).as_posix())
        if execution is None:
            global_errors.extend(errors)
            continue
        cid = execution.get("content_id")
        if not CID_RE.fullmatch(str(cid or "")):
            global_errors.append(f"{path.relative_to(root).as_posix()}: invalid content_id")
            continue
        executions[cid].append(execution)

    evidence_root = root / "content/executions/evidence"
    if evidence_root.is_dir():
        for directory in sorted(path for path in evidence_root.iterdir() if path.is_dir()):
            cid = directory.name
            if not CID_RE.fullmatch(cid):
                global_errors.append(f"{directory.relative_to(root).as_posix()}: invalid content_id directory")
                continue
            path = directory / "upload.json"
            if path.exists():
                errors = []
                upload = _read(path, errors, path.relative_to(root).as_posix())
                upload_errors[cid].extend(errors)
                if upload is not None:
                    uploads[cid] = upload

    for path in sorted((root / "content/results").glob("*.json")):
        errors = []
        result = _read(path, errors, path.relative_to(root).as_posix())
        if result is None:
            global_errors.extend(errors)
            continue
        cid = result.get("content_id")
        if not CID_RE.fullmatch(str(cid or "")):
            global_errors.append(f"{path.relative_to(root).as_posix()}: invalid content_id")
            continue
        if cid in results:
            global_errors.append(f"duplicate results for {cid}")
        results[cid] = result

    history_by_content = defaultdict(list)
    history_path = root / "data/history.json"
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            history = []
            global_errors.append(f"data/history.json: invalid JSON ({type(exc).__name__})")
        if not isinstance(history, list):
            global_errors.append("data/history.json: expected JSON array")
            history = []
        for record in history:
            if isinstance(record, dict) and CID_RE.fullmatch(str(record.get("content_id") or "")):
                history_by_content[record["content_id"]].append(record)

    content_ids = sorted(set(request_records) | set(executions) | set(uploads) | set(upload_errors) | set(results))
    items = []
    for cid in content_ids:
        errors = list(upload_errors[cid])
        requests = request_records[cid]
        execution_list = executions[cid]
        request = requests[0] if len(requests) == 1 else None
        execution = execution_list[0] if len(execution_list) == 1 else None
        upload = uploads.get(cid)
        result = results.get(cid)

        if len(requests) > 1:
            errors.append("content_id occurs in multiple request items")
        elif not requests:
            errors.append("request item is missing")
        if len(execution_list) > 1:
            errors.append("content_id has multiple executions")

        if request is not None and execution is not None:
            if execution.get("execution_version") == 1 and request["request"].get("request_version") == 1:
                expected = {"content_id": cid, "request_path": request["path"], "request_blob_sha": _blob(request["raw"])}
            else:
                request_id = request["request"].get("request_id")
                expected = {
                    "content_id": cid,
                    "request_id": request_id,
                    "request_path": request["path"],
                    "request_blob_sha": _blob(request["raw"]),
                    "item_blob_sha": _blob(_encoded(request["item"])),
                }
            for field, value in expected.items():
                if execution.get(field) != value:
                    errors.append(f"execution {field} does not match request")

        if upload is not None:
            if execution is None:
                errors.append("upload evidence has no unique execution")
            else:
                errors.extend(_evidence_errors(upload, execution))

        if result is not None:
            if execution is None or request is None:
                errors.append("result has no unique execution/request join")
            else:
                if result.get("content_id") != cid or result.get("execution_id") != execution.get("execution_id"):
                    errors.append("result identity does not match execution")
                if result.get("result_version") == 2:
                    publish_at = (request["item"].get("publication") or {}).get("publish_at")
                    if result.get("publish_at") != publish_at:
                        errors.append("result publish_at does not match request")
            if upload is None:
                errors.append("result is missing upload evidence")
            elif result.get("youtube_video_id") != upload.get("youtube_video_id"):
                errors.append("result youtube_video_id does not match upload evidence")
            history_records = history_by_content[cid]
            if len(history_records) != 1:
                errors.append("result must have exactly one history record")
            else:
                time_field = "published_at" if result.get("result_version") == 1 else "publish_at"
                if history_records[0].get(time_field) != result.get(time_field):
                    errors.append(f"history {time_field} does not match result")

        if errors:
            status = "invalid_cross_repository_relationship"
        elif execution is None:
            status = "request_only"
        elif upload is None:
            status = "execution_without_evidence"
        elif result is None:
            status = "uploaded_without_result"
        elif upload.get("evidence_version") == 1 or execution.get("execution_version") == 1:
            status = "legacy_evidence_alias"
        else:
            status = "complete"

        items.append(
            {
                "content_id": cid,
                "request_id": request["request"].get("request_id") if request else None,
                "execution_id": execution.get("execution_id") if execution else None,
                "evidence_version": upload.get("evidence_version") if upload else None,
                "status": status,
                "errors": sorted(set(errors))[:MAX_ERRORS],
            }
        )

    counts = Counter(item["status"] for item in items)
    statuses = (
        "request_only",
        "execution_without_evidence",
        "uploaded_without_result",
        "complete",
        "legacy_evidence_alias",
        "invalid_cross_repository_relationship",
    )
    return {
        "audit_version": 1,
        "counts": {status: counts.get(status, 0) for status in statuses},
        "items": items,
        "validation_errors": sorted(set(global_errors))[:MAX_ERRORS],
    }
