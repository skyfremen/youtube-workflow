#!/usr/bin/env python3
"""Permanent visual-rejection tracking for Wacky Dramas background seeding."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import background_seed as bs

ROOT = Path(__file__).resolve().parent
REJECTIONS = ROOT / "data" / "background-rejections.json"


def _asset_sort_key(asset_id: str) -> int:
    return int(asset_id.split("-", 1)[1])


def validate_rejections(data, registry: dict | None = None) -> dict:
    if not isinstance(data, dict) or set(data) != {"rejected_ids"}:
        raise bs.SeedError("background-rejections.json must contain exactly rejected_ids[]")
    rejected = data.get("rejected_ids")
    if not isinstance(rejected, list) or any(not isinstance(item, str) for item in rejected):
        raise bs.SeedError("rejected_ids must be an array of strings")
    if any(not bs.ASSET_ID_RE.fullmatch(item) for item in rejected):
        raise bs.SeedError("rejected_ids contains an invalid asset id")
    if len(set(rejected)) != len(rejected):
        raise bs.SeedError("rejected_ids must not contain duplicates")
    if registry is not None:
        approved = {item["id"] for item in registry.get("assets", [])}
        overlap = approved & set(rejected)
        if overlap:
            raise bs.SeedError(f"background id cannot be both approved and rejected: {sorted(overlap, key=_asset_sort_key)[0]}")
    return data


def load_rejections(path: Path = REJECTIONS, registry: dict | None = None) -> dict:
    path = Path(path)
    data = {"rejected_ids": []} if not path.exists() else bs.read_json(path)
    return validate_rejections(data, registry)


def permanent_rejected_ids(path: Path = REJECTIONS) -> set[str]:
    return set(load_rejections(path)["rejected_ids"])


def excluded_review_ids(
    reviews_root: Path = bs.REVIEWS,
    approvals_root: Path = bs.APPROVALS,
    rejections_path: Path = REJECTIONS,
    pending_fn=None,
) -> set[str]:
    pending_fn = pending_fn or bs.pending_review_ids
    return set(pending_fn(reviews_root, approvals_root)) | permanent_rejected_ids(rejections_path)


def validate_state(registry_path: Path = bs.REGISTRY, rejections_path: Path = REJECTIONS) -> tuple[dict, dict]:
    registry = bs.load_registry(registry_path)
    rejections = load_rejections(rejections_path, registry)
    print(
        f"Background state valid: assets={len(registry['assets'])} "
        f"rejected={len(rejections['rejected_ids'])}"
    )
    return registry, rejections


def discover_with_rejections(
    request_path: Path,
    api_key: str,
    output_dir: Path,
    registry_path: Path = bs.REGISTRY,
    reviews_root: Path = bs.REVIEWS,
    rejections_path: Path = REJECTIONS,
) -> Path:
    original_pending = bs.pending_review_ids

    def combined_pending(reviews_root_arg=bs.REVIEWS, approvals_root_arg=bs.APPROVALS):
        return excluded_review_ids(
            reviews_root_arg,
            approvals_root_arg,
            rejections_path,
            pending_fn=original_pending,
        )

    bs.pending_review_ids = combined_pending
    try:
        return bs.discover(request_path, api_key, output_dir, registry_path, reviews_root)
    finally:
        bs.pending_review_ids = original_pending


def _reviewed_candidate_ids(approval: dict, reviews_root: Path) -> set[str]:
    manifest_path = Path(reviews_root) / approval["review_id"] / "manifest.json"
    if not manifest_path.exists():
        raise bs.SeedError("matching immutable review manifest does not exist")
    manifest = bs.read_json(manifest_path)
    if manifest.get("review_id") != approval["review_id"] or not isinstance(manifest.get("candidates"), list):
        raise bs.SeedError("review manifest identity is invalid")
    reviewed = []
    for item in manifest["candidates"]:
        asset_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(asset_id, str) or not bs.ASSET_ID_RE.fullmatch(asset_id):
            raise bs.SeedError("review manifest candidate is invalid")
        reviewed.append(asset_id)
    if len(set(reviewed)) != len(reviewed):
        raise bs.SeedError("review manifest contains duplicate candidate ids")
    return set(reviewed)


def promote_with_rejections(
    approval_path: Path,
    registry_path: Path = bs.REGISTRY,
    reviews_root: Path = bs.REVIEWS,
    rejections_path: Path = REJECTIONS,
) -> tuple[int, int]:
    approval_path = Path(approval_path)
    approval = bs.validate_approval(bs.read_json(approval_path), approval_path)
    reviewed = _reviewed_candidate_ids(approval, reviews_root)
    approved = set(approval["approved_ids"])
    unknown = approved - reviewed
    if unknown:
        raise bs.SeedError(f"approval references candidate not in manifest: {sorted(unknown, key=_asset_sort_key)[0]}")

    registry = bs.load_registry(registry_path)
    rejection_data = load_rejections(rejections_path, registry)
    permanent = set(rejection_data["rejected_ids"])
    conflict = approved & permanent
    if conflict:
        raise bs.SeedError(
            f"approval references permanently rejected candidate: {sorted(conflict, key=_asset_sort_key)[0]}"
        )

    added = bs.promote(approval_path, registry_path, reviews_root)
    updated_registry = bs.load_registry(registry_path)
    newly_rejected = reviewed - approved - permanent
    combined = permanent | (reviewed - approved)
    validate_rejections({"rejected_ids": list(combined)}, updated_registry)

    if newly_rejected or not Path(rejections_path).exists():
        bs.write_json(
            rejections_path,
            {"rejected_ids": sorted(combined, key=_asset_sort_key)},
        )

    print(
        f"Rejection registry updated: review_id={approval['review_id']} "
        f"added={len(newly_rejected)} total={len(combined)}"
    )
    return added, len(newly_rejected)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    discover_parser = sub.add_parser("discover")
    discover_parser.add_argument("--request", required=True)
    discover_parser.add_argument("--output-dir", required=True)
    promote_parser = sub.add_parser("promote")
    promote_parser.add_argument("--approval", required=True)
    args = parser.parse_args()

    try:
        if args.command == "validate":
            validate_state()
        elif args.command == "discover":
            key = os.environ.get("PEXELS_API_KEY", "").strip()
            if not key:
                raise bs.SeedError("PEXELS_API_KEY is not configured")
            discover_with_rejections(Path(args.request), key, Path(args.output_dir))
        elif args.command == "promote":
            promote_with_rejections(Path(args.approval))
    except (OSError, json.JSONDecodeError, bs.SeedError, ValueError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
