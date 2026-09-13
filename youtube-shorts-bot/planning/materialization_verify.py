"""Verify an exact-SHA connector materialization before planner checkpoints.

This module is intentionally standard-library only so it can validate a Gitless
planner snapshot before importing the rest of the planner stack.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import py_compile
import re
import sys
from pathlib import Path
from typing import Any


SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
DEFAULT_MANIFEST = "youtube-shorts-bot/planning/PLANNER_MATERIALIZATION.json"
EVIDENCE_SCHEMA_VERSION = 1


def git_blob_sha(data: bytes) -> str:
    """Return the Git blob object id for *data* without requiring Git."""
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _error(code: str, detail: str, path: str | None = None) -> dict[str, str]:
    result = {"code": code, "detail": detail}
    if path is not None:
        result["path"] = path
    return result


def _load_json(path: Path, label: str, errors: list[dict[str, str]]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(_error(f"{label}_missing", f"{label} file does not exist", str(path)))
    except (OSError, UnicodeError) as exc:
        errors.append(_error(f"{label}_read_failed", str(exc), str(path)))
    except json.JSONDecodeError as exc:
        errors.append(_error(f"{label}_invalid_json", str(exc), str(path)))
    return None


def _required_paths(manifest: dict[str, Any], profile: str) -> tuple[list[str], list[str]]:
    profiles = manifest.get("profile_required_files")
    if not isinstance(profiles, dict) or profile not in profiles:
        raise ValueError(f"unknown profile: {profile}")

    profile_entry = profiles[profile]
    if not isinstance(profile_entry, dict):
        raise ValueError(f"invalid profile entry: {profile}")

    python_files = list(manifest.get("shared_required_python_files", []))
    python_files.extend(profile_entry.get("python_files", []))
    data_files = list(manifest.get("shared_required_data_files", []))
    data_files.extend(profile_entry.get("data_files", []))

    for group_name, values in (("python_files", python_files), ("data_files", data_files)):
        if not all(isinstance(value, str) and value for value in values):
            raise ValueError(f"manifest {group_name} must contain non-empty strings")

    return python_files, data_files


def verify_materialization(
    *,
    root: Path,
    profile: str,
    rules_source_sha: str,
    evidence_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []

    if not SHA1_RE.fullmatch(rules_source_sha):
        errors.append(
            _error(
                "invalid_rules_source_sha",
                "rules_source_sha must be a lowercase 40-character SHA-1",
            )
        )

    manifest = _load_json(manifest_path, "manifest", errors)
    evidence = _load_json(evidence_path, "evidence", errors)

    if not isinstance(manifest, dict) or not isinstance(evidence, dict):
        return {
            "status": "FAIL",
            "profile": profile,
            "rules_source_sha": rules_source_sha,
            "manifest": str(manifest_path),
            "evidence": str(evidence_path),
            "required_files": 0,
            "verified_files": 0,
            "compiled_python_files": 0,
            "critical_imports_verified": [],
            "errors": errors,
        }

    if evidence.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        errors.append(
            _error(
                "unsupported_evidence_schema",
                f"expected evidence schema {EVIDENCE_SCHEMA_VERSION}, "
                f"got {evidence.get('schema_version')!r}",
                str(evidence_path),
            )
        )

    evidence_source_sha = evidence.get("rules_source_sha")
    if evidence_source_sha != rules_source_sha:
        errors.append(
            _error(
                "mixed_source_sha",
                f"evidence rules_source_sha {evidence_source_sha!r} does not match "
                f"{rules_source_sha!r}",
                str(evidence_path),
            )
        )

    try:
        python_files, data_files = _required_paths(manifest, profile)
    except (TypeError, ValueError) as exc:
        errors.append(_error("manifest_contract_invalid", str(exc), str(manifest_path)))
        python_files, data_files = [], []

    manifest_relative = manifest.get("connector_materialization", {}).get(
        "manifest_path", DEFAULT_MANIFEST
    )
    if not isinstance(manifest_relative, str) or not manifest_relative:
        errors.append(
            _error(
                "manifest_contract_invalid",
                "connector_materialization.manifest_path must be a non-empty string",
                str(manifest_path),
            )
        )
        manifest_relative = DEFAULT_MANIFEST

    required_paths = [manifest_relative, *python_files, *data_files]
    required_paths = list(dict.fromkeys(required_paths))

    files_evidence = evidence.get("files")
    if not isinstance(files_evidence, dict):
        errors.append(
            _error(
                "evidence_files_invalid",
                "evidence.files must be an object keyed by repository-relative path",
                str(evidence_path),
            )
        )
        files_evidence = {}

    verified_files = 0
    compiled_python_files = 0

    for relative in required_paths:
        if not isinstance(relative, str) or not relative:
            errors.append(
                _error(
                    "manifest_contract_invalid",
                    "required materialization path must be a non-empty string",
                    str(manifest_path),
                )
            )
            continue

        local_path = root / relative
        entry = files_evidence.get(relative)

        if not local_path.is_file():
            errors.append(_error("required_file_missing", "required file is absent", relative))
            continue

        if not isinstance(entry, dict):
            errors.append(
                _error(
                    "evidence_missing",
                    "connector-returned source/blob evidence is required for this file",
                    relative,
                )
            )
            continue

        file_source_sha = entry.get("rules_source_sha")
        if file_source_sha != rules_source_sha:
            errors.append(
                _error(
                    "mixed_source_sha",
                    f"file evidence source SHA {file_source_sha!r} does not match "
                    f"{rules_source_sha!r}",
                    relative,
                )
            )

        expected_blob_sha = entry.get("blob_sha")
        if not isinstance(expected_blob_sha, str) or not SHA1_RE.fullmatch(expected_blob_sha):
            errors.append(
                _error(
                    "invalid_blob_sha",
                    f"expected connector Git blob SHA, got {expected_blob_sha!r}",
                    relative,
                )
            )
            continue

        try:
            actual_blob_sha = git_blob_sha(local_path.read_bytes())
        except OSError as exc:
            errors.append(_error("required_file_read_failed", str(exc), relative))
            continue

        if actual_blob_sha != expected_blob_sha:
            errors.append(
                _error(
                    "blob_sha_mismatch",
                    f"expected {expected_blob_sha}, got {actual_blob_sha}",
                    relative,
                )
            )
            continue

        verified_files += 1

    for relative in python_files:
        local_path = root / relative
        if not local_path.is_file():
            continue
        try:
            py_compile.compile(str(local_path), doraise=True)
            compiled_python_files += 1
        except py_compile.PyCompileError as exc:
            errors.append(_error("python_compile_failed", str(exc), relative))
        except OSError as exc:
            errors.append(_error("python_compile_failed", str(exc), relative))

    critical_imports = manifest.get("connector_materialization", {}).get(
        "critical_imports",
        ["planning.planner_contract", "media.media_readiness", "planning.planner_precommit"],
    )
    if not isinstance(critical_imports, list) or not all(
        isinstance(value, str) and value for value in critical_imports
    ):
        errors.append(
            _error(
                "manifest_contract_invalid",
                "connector_materialization.critical_imports must be a list of module names",
                str(manifest_path),
            )
        )
        critical_imports = []

    verified_imports: list[str] = []
    pythonpath_root = manifest.get("pythonpath_root", "youtube-shorts-bot")
    if not isinstance(pythonpath_root, str) or not pythonpath_root:
        errors.append(
            _error(
                "manifest_contract_invalid",
                "pythonpath_root must be a non-empty string",
                str(manifest_path),
            )
        )
    elif not errors:
        import_root = str((root / pythonpath_root).resolve())
        inserted = False
        if import_root not in sys.path:
            sys.path.insert(0, import_root)
            inserted = True
        try:
            for module_name in critical_imports:
                try:
                    importlib.import_module(module_name)
                    verified_imports.append(module_name)
                except Exception as exc:  # import side effects are part of this readiness gate
                    errors.append(
                        _error(
                            "critical_import_failed",
                            f"{module_name}: {exc.__class__.__name__}: {exc}",
                        )
                    )
        finally:
            if inserted and sys.path and sys.path[0] == import_root:
                sys.path.pop(0)

    return {
        "status": "PASS" if not errors else "FAIL",
        "profile": profile,
        "rules_source_sha": rules_source_sha,
        "manifest": str(manifest_path),
        "evidence": str(evidence_path),
        "required_files": len(required_paths),
        "verified_files": verified_files,
        "compiled_python_files": compiled_python_files,
        "critical_imports_verified": verified_imports,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify exact-SHA connector materialization before planner checkpoints."
    )
    parser.add_argument("--profile", required=True, choices=("daily", "adhoc"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--rules-source-sha", required=True)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Manifest path. Defaults to <root>/youtube-shorts-bot/planning/PLANNER_MATERIALIZATION.json.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    manifest_path = (
        args.manifest.resolve()
        if args.manifest is not None
        else root / DEFAULT_MANIFEST
    )
    evidence_path = args.evidence.resolve()

    result = verify_materialization(
        root=root,
        profile=args.profile,
        rules_source_sha=args.rules_source_sha,
        evidence_path=evidence_path,
        manifest_path=manifest_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
