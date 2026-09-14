#!/usr/bin/env python3
"""Permanent visual-rejection tracking for Wacky Dramas background seeding."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import background_seed as bs

ROOT = Path(__file__).resolve().parent
REJECTIONS = ROOT / "data" / "background-rejections.json"
SEARCH_PAGE_SIZE = 30
MAX_SEARCH_PAGES_PER_QUERY = 4
MAX_TECHNICAL_ATTEMPTS = 200


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


def api_search_page(
    query: str,
    api_key: str,
    per_page: int = SEARCH_PAGE_SIZE,
    page: int = 1,
) -> list[dict]:
    """Search one deterministic Pexels page so discovery can backfill failures."""
    params = urllib.parse.urlencode(
        {
            "query": query,
            "size": "medium",
            "per_page": min(max(int(per_page), 1), 80),
            "page": max(int(page), 1),
        }
    )
    request = urllib.request.Request(
        f"{bs.PEXELS_SEARCH}?{params}",
        headers={"Authorization": api_key, "User-Agent": "WackyDramasBackgroundSeeder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    videos = payload.get("videos", [])
    return videos if isinstance(videos, list) else []


def _inventory_shortages(registry: dict, target_per_category: int) -> dict[str, int]:
    counts = {category: 0 for category in bs.CATEGORIES}
    for asset in registry["assets"]:
        counts[asset["category"]] += 1
    return {
        category: max(0, int(target_per_category) - counts[category])
        for category in bs.CATEGORIES
    }


def _candidate_stream(
    category: str,
    api_key: str,
    excluded: set[str],
    search_fn=None,
    max_pages_per_query: int = MAX_SEARCH_PAGES_PER_QUERY,
):
    """Yield unseen metadata candidates across queries and Pexels pages."""
    search_fn = search_fn or api_search_page
    seen = set()
    for query in bs.SEARCH_QUERIES[category]:
        for page in range(1, max(1, int(max_pages_per_query)) + 1):
            try:
                videos = search_fn(query, api_key, SEARCH_PAGE_SIZE, page)
            except Exception as exc:
                print(
                    f"WARN pexels search failed category={category} query={query!r} page={page}: {exc}",
                    flush=True,
                )
                break
            if not videos:
                break
            for video in sorted(videos, key=lambda item: bs.duration_preference(item.get("duration"))):
                candidate = bs._candidate_from_video(video, category)
                if not candidate:
                    continue
                asset_id = candidate["id"]
                if asset_id in excluded or asset_id in seen:
                    continue
                seen.add(asset_id)
                excluded.add(asset_id)
                yield candidate


def discover_with_rejections(
    request_path: Path,
    api_key: str,
    output_dir: Path,
    registry_path: Path = bs.REGISTRY,
    reviews_root: Path = bs.REVIEWS,
    rejections_path: Path = REJECTIONS,
    approvals_root: Path = bs.APPROVALS,
    search_fn=None,
) -> Path:
    """Discover until shortages are filled, review cap is reached, or search is exhausted.

    Unlike V1 discovery, a technical failure does not consume a category slot. The
    next unseen candidate is fetched (including later Pexels pages) and validated.
    """
    bs.validate_media_tools()
    request_path = Path(request_path)
    review_id = bs.request_id_from_path(request_path)
    request = bs.validate_request(bs.read_json(request_path))
    registry = bs.load_registry(registry_path)
    manifest_path = Path(reviews_root) / review_id / "manifest.json"
    if manifest_path.exists():
        manifest = bs.read_json(manifest_path)
        bs.rebuild_review_artifact(manifest, output_dir)
        print(f"Review already exists; regenerated evidence: {manifest_path}")
        return manifest_path

    shortages = _inventory_shortages(registry, request["target_per_category"])
    categories = [category for category in bs.CATEGORIES if shortages[category] > 0]
    categories.sort(key=lambda category: (-shortages[category], category))

    existing = {asset["id"] for asset in registry["assets"]}
    excluded = existing | excluded_review_ids(
        reviews_root,
        approvals_root,
        rejections_path,
    )
    streams = {
        category: iter(_candidate_stream(category, api_key, excluded, search_fn=search_fn))
        for category in categories
    }

    target_accepts = min(request["max_candidates"], sum(shortages.values()))
    technical_attempt_limit = min(
        MAX_TECHNICAL_ATTEMPTS,
        max(24, request["max_candidates"] * 2, target_accepts * 6),
    )
    accepted = []
    accepted_by_category = {category: 0 for category in categories}
    exhausted = set()
    attempts = 0

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    candidates_dir = Path(output_dir) / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    while len(accepted) < target_accepts and attempts < technical_attempt_limit:
        active = [
            category
            for category in categories
            if category not in exhausted and accepted_by_category[category] < shortages[category]
        ]
        if not active:
            break
        active.sort(
            key=lambda category: (
                accepted_by_category[category] / max(shortages[category], 1),
                -(shortages[category] - accepted_by_category[category]),
                category,
            )
        )
        progressed = False
        for category in active:
            if len(accepted) >= target_accepts or attempts >= technical_attempt_limit:
                break
            if accepted_by_category[category] >= shortages[category]:
                continue
            try:
                candidate = next(streams[category])
            except StopIteration:
                exhausted.add(category)
                continue

            progressed = True
            attempts += 1
            with tempfile.TemporaryDirectory(prefix="background-media-") as temp_name:
                local_file = Path(temp_name) / f"{candidate['id']}.mp4"
                try:
                    bs.download_file(candidate["download_url"], local_file)
                    probe = bs.validate_physical(candidate, local_file)
                    review_candidate = bs._manifest_candidate(candidate, probe)
                    bs.make_contact_sheet(
                        local_file,
                        review_candidate,
                        probe,
                        candidates_dir / f"{candidate['id']}.jpg",
                    )
                    accepted.append(review_candidate)
                    accepted_by_category[category] += 1
                    print(f"ACCEPT technical {candidate['id']} category={category}", flush=True)
                except Exception as exc:
                    print(f"REJECT technical {candidate['id']}: {exc}", flush=True)

        if not progressed and all(category in exhausted for category in active):
            break

    unfilled = {
        category: shortages[category] - accepted_by_category[category]
        for category in categories
        if accepted_by_category[category] < shortages[category]
    }
    if unfilled:
        if len(accepted) >= request["max_candidates"]:
            reason = "max_candidates accepted cap reached"
        elif attempts >= technical_attempt_limit:
            reason = "technical attempt safety limit reached"
        else:
            reason = "configured Pexels queries/pages exhausted"
        print(
            f"WARN discovery ended before all shortages were filled: reason={reason}; "
            f"accepted={len(accepted)} attempts={attempts} unfilled={unfilled}",
            flush=True,
        )

    manifest = {"review_id": review_id, "request": request, "candidates": accepted}
    bs.write_json(manifest_path, manifest)
    bs.write_json(Path(output_dir) / "manifest.json", manifest)
    bs.make_index(candidates_dir, Path(output_dir) / "index.jpg", len(accepted))
    print(
        f"Review manifest created: {manifest_path}; candidates={len(accepted)}; attempts={attempts}",
        flush=True,
    )
    return manifest_path


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
