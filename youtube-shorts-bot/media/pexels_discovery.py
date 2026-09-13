"""Deterministic Pexels discovery for long, production-suitable background clips.

Provider/API eligibility only. Schema v2 adds bounded replenishment-session inputs so
ChatGPT can target deficits and exclude already-reviewed provider assets. Schema v1
remains accepted for existing immutable requests.

Review decisions are durable repository state. For schema-v2 requests, discovery
automatically excludes every provider asset already reviewed in the same
replenishment session, even if the caller omits it from exclude_provider_asset_ids.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from media.background_policy import rendition_is_production_suitable
from media.continuous_background import MIN_SEQUENCE_CLIP_SECONDS
from media.pexels_registry_base import api_get, renditions_from_video

DISCOVERY_SCHEMA_VERSION = 1
LEGACY_REQUEST_SCHEMA_VERSION = 1
REQUEST_SCHEMA_VERSION = 2
REVIEW_DECISION_SCHEMA_VERSION = 1
DEFAULT_MAX_CANDIDATES = 48
MAX_MAX_CANDIDATES = 80
SEARCH_PER_PAGE = 80
SEARCH_MAX_PAGES = 3
MAX_REPLENISH_ATTEMPTS = 5
REVIEW_DECISIONS_DIR = (
    Path(__file__).resolve().parents[1]
    / "content"
    / "background-sourcing"
    / "review-decisions"
)

CATEGORY_QUERIES = {
    "cooking": ("cooking process", "cooking food"),
    "baking": ("baking process", "bread baking", "pastry making"),
    "food_prep": ("food preparation", "meal prep", "cutting vegetables"),
    "satisfying_process": ("satisfying process", "oddly satisfying process"),
    "crafting": ("craft making", "woodworking", "pottery making"),
    "cleaning": (
        "cleaning restoration",
        "pressure washing",
        "deep cleaning",
        "car washing",
        "surface scrubbing",
        "window cleaning",
        "industrial cleaning",
        "car detailing",
        "vehicle detailing",
        "house cleaning",
        "floor cleaning",
        "floor mopping",
        "vacuum cleaning",
        "carpet cleaning",
        "rug cleaning",
        "kitchen cleaning",
        "bathroom cleaning",
        "dish washing",
        "window washing",
        "driveway pressure washing",
        "patio pressure washing",
        "steam cleaning",
        "upholstery cleaning",
    ),
    "assembly": (
        "industrial assembly",
        "factory assembly",
        "manufacturing process",
    ),
    "pov_movement": ("walking pov", "driving pov", "train window travel"),
    "city_motion": ("city traffic", "city walking", "urban motion"),
}

CATEGORY_TARGETS_48 = {
    "cooking": 6,
    "baking": 5,
    "food_prep": 5,
    "satisfying_process": 6,
    "crafting": 5,
    "cleaning": 6,
    "assembly": 5,
    "pov_movement": 5,
    "city_motion": 5,
}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _load_request(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    version = data.get("schema_version") if isinstance(data, dict) else None
    base = {"schema_version", "plan_date", "request_id", "max_candidates"}

    if version == LEGACY_REQUEST_SCHEMA_VERSION:
        if set(data) != base:
            raise ValueError("schema-v1 discovery request has invalid fields")
        data = {
            **data,
            "target_categories": None,
            "exclude_provider_asset_ids": [],
            "replenishment_session_id": None,
            "attempt": 1,
        }
    elif version == REQUEST_SCHEMA_VERSION:
        expected = base | {
            "target_categories",
            "exclude_provider_asset_ids",
            "replenishment_session_id",
            "attempt",
        }
        if set(data) != expected:
            raise ValueError("schema-v2 discovery request has invalid fields")
    else:
        raise ValueError("discovery request schema_version must be 1 or 2")

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data["plan_date"])):
        raise ValueError("plan_date must be YYYY-MM-DD")
    if not re.fullmatch(r"dr-[A-Za-z0-9-]{8,96}", str(data["request_id"])):
        raise ValueError("request_id must match dr-[A-Za-z0-9-]{8,96}")

    max_candidates = data["max_candidates"]
    if (
        isinstance(max_candidates, bool)
        or not isinstance(max_candidates, int)
        or not 1 <= max_candidates <= MAX_MAX_CANDIDATES
    ):
        raise ValueError(f"max_candidates must be 1-{MAX_MAX_CANDIDATES}")

    targets = data["target_categories"]
    if targets is not None and (
        not isinstance(targets, list)
        or not targets
        or len(set(targets)) != len(targets)
        or any(value not in CATEGORY_QUERIES for value in targets)
    ):
        raise ValueError(
            "target_categories must be null or a unique non-empty list of known categories"
        )

    excluded = data["exclude_provider_asset_ids"]
    normalized = [str(value) for value in excluded] if isinstance(excluded, list) else []
    if (
        not isinstance(excluded, list)
        or len(set(normalized)) != len(normalized)
        or any(not value.isdigit() for value in normalized)
    ):
        raise ValueError(
            "exclude_provider_asset_ids must contain unique numeric provider IDs"
        )

    attempt = data["attempt"]
    if (
        isinstance(attempt, bool)
        or not isinstance(attempt, int)
        or not 1 <= attempt <= MAX_REPLENISH_ATTEMPTS
    ):
        raise ValueError(f"attempt must be 1-{MAX_REPLENISH_ATTEMPTS}")

    session_id = data["replenishment_session_id"]
    if version == REQUEST_SCHEMA_VERSION and not re.fullmatch(
        r"rs-[A-Za-z0-9-]{8,96}", str(session_id or "")
    ):
        raise ValueError(
            "replenishment_session_id must match rs-[A-Za-z0-9-]{8,96}"
        )
    return data


def _validate_review_decision_doc(data, path="<memory>"):
    expected = {
        "schema_version",
        "replenishment_session_id",
        "request_id",
        "attempt",
        "decisions",
    }
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError(f"{path}: invalid review-decision fields")
    if data["schema_version"] != REVIEW_DECISION_SCHEMA_VERSION:
        raise ValueError(f"{path}: review-decision schema_version must be 1")
    if not re.fullmatch(
        r"rs-[A-Za-z0-9-]{8,96}", str(data.get("replenishment_session_id") or "")
    ):
        raise ValueError(f"{path}: invalid replenishment_session_id")
    if not re.fullmatch(r"dr-[A-Za-z0-9-]{8,96}", str(data.get("request_id") or "")):
        raise ValueError(f"{path}: invalid request_id")
    attempt = data.get("attempt")
    if (
        isinstance(attempt, bool)
        or not isinstance(attempt, int)
        or not 1 <= attempt <= MAX_REPLENISH_ATTEMPTS
    ):
        raise ValueError(f"{path}: invalid attempt")

    decisions = data.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise ValueError(f"{path}: decisions must be a non-empty list")

    expected_decision = {
        "provider_asset_id",
        "decision",
        "discovery_category",
        "reviewed_category",
        "category_match",
        "reason_code",
    }
    seen = set()
    for index, decision in enumerate(decisions):
        label = f"{path}: decision {index}"
        if not isinstance(decision, dict) or set(decision) != expected_decision:
            raise ValueError(f"{label}: invalid fields")
        provider_id = str(decision.get("provider_asset_id") or "")
        if not provider_id.isdigit():
            raise ValueError(f"{label}: provider_asset_id must be numeric")
        if provider_id in seen:
            raise ValueError(f"{label}: duplicate provider_asset_id")
        seen.add(provider_id)

        if decision.get("decision") not in {"approve", "reject"}:
            raise ValueError(f"{label}: decision must be approve or reject")
        discovery_category = decision.get("discovery_category")
        if discovery_category not in CATEGORY_QUERIES:
            raise ValueError(f"{label}: invalid discovery_category")
        reviewed_category = decision.get("reviewed_category")
        if reviewed_category is not None and reviewed_category not in CATEGORY_QUERIES:
            raise ValueError(f"{label}: invalid reviewed_category")
        if not isinstance(decision.get("category_match"), bool):
            raise ValueError(f"{label}: category_match must be boolean")
        if not str(decision.get("reason_code") or "").strip():
            raise ValueError(f"{label}: reason_code is required")

        if decision["decision"] == "approve" and (
            decision["category_match"] is not True
            or reviewed_category != discovery_category
            or decision["reason_code"] != "APPROVED"
        ):
            raise ValueError(
                f"{label}: approved candidates must match their discovery category "
                "and use reason_code=APPROVED"
            )
    return data


def _load_reviewed_provider_ids(
    replenishment_session_id, directory=REVIEW_DECISIONS_DIR
):
    if not replenishment_session_id:
        return set()
    directory = Path(directory)
    if not directory.exists():
        return set()

    reviewed = set()
    for path in sorted(directory.glob("*.json")):
        data = _validate_review_decision_doc(
            json.loads(path.read_text(encoding="utf-8")), path=str(path)
        )
        if data["replenishment_session_id"] != replenishment_session_id:
            continue
        reviewed.update(
            str(decision["provider_asset_id"]) for decision in data["decisions"]
        )
    return reviewed


def _eligible_candidate(video, category, query):
    try:
        duration = float(video.get("duration"))
    except (TypeError, ValueError):
        return None
    if duration < MIN_SEQUENCE_CLIP_SECONDS:
        return None

    renditions = renditions_from_video(video)
    suitable = [item for item in renditions if rendition_is_production_suitable(item)]
    if not suitable:
        return None

    review = [
        item
        for item in renditions
        if int(item.get("width") or 0) >= 360
        and int(item.get("height") or 0) >= 360
    ] or list(renditions)
    review.sort(
        key=lambda item: (
            int(item.get("width") or 0) * int(item.get("height") or 0),
            float(item.get("fps") or 999),
            str(item.get("id") or ""),
        )
    )
    preview = review[0]

    provider_id = str(video.get("id") or "").strip()
    page = str(video.get("url") or "").strip()
    image = str(video.get("image") or "").strip()
    if not provider_id.isdigit() or not page or not image:
        return None

    return {
        "provider_asset_id": provider_id,
        "source_page": page,
        "duration_seconds": duration,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "creator": str(video.get("user", {}).get("name") or "Unknown"),
        "discovery_category": category,
        "discovery_query": query,
        "preview_image_url": image,
        "preview_video_url": str(preview["direct_url"]),
        "preview_video_width": int(preview["width"]),
        "preview_video_height": int(preview["height"]),
        "preview_video_fps": preview.get("fps"),
        "production_suitable_rendition_count": len(suitable),
    }


def _category_targets(max_candidates, categories=None):
    categories = list(categories or CATEGORY_QUERIES)
    if (
        categories == list(CATEGORY_QUERIES)
        and max_candidates == DEFAULT_MAX_CANDIDATES
    ):
        return dict(CATEGORY_TARGETS_48)
    base, remainder = divmod(max_candidates, len(categories))
    return {
        category: base + (1 if index < remainder else 0)
        for index, category in enumerate(categories)
    }


def discover(
    max_candidates=DEFAULT_MAX_CANDIDATES,
    key=None,
    target_categories=None,
    exclude_provider_asset_ids=None,
    attempt=1,
):
    categories = list(target_categories or CATEGORY_QUERIES)
    accepted = []
    seen = set(map(str, exclude_provider_asset_ids or []))
    diagnostics = []
    targets = _category_targets(max_candidates, categories)

    for category in categories:
        count = 0
        target = targets[category]
        queries = CATEGORY_QUERIES[category]
        offset = (attempt - 1) % len(queries)
        queries = queries[offset:] + queries[:offset]

        for query in queries:
            for page in range(1, SEARCH_MAX_PAGES + 1):
                payload = api_get(
                    f"search?query={quote_plus(query)}&per_page={SEARCH_PER_PAGE}&page={page}",
                    key=key,
                )
                videos = payload.get("videos", []) if isinstance(payload, dict) else []
                new_eligible = 0
                excluded_count = 0

                for video in videos:
                    provider_id = str(video.get("id") or "").strip()
                    if not provider_id or provider_id in seen:
                        if provider_id in seen:
                            excluded_count += 1
                        continue
                    candidate = _eligible_candidate(video, category, query)
                    if not candidate:
                        continue
                    seen.add(provider_id)
                    accepted.append(candidate)
                    count += 1
                    new_eligible += 1
                    if count >= target or len(accepted) >= max_candidates:
                        break

                diagnostics.append(
                    {
                        "category": category,
                        "target": target,
                        "query": query,
                        "attempt": attempt,
                        "page": page,
                        "returned": len(videos),
                        "excluded": excluded_count,
                        "new_eligible": new_eligible,
                    }
                )
                if count >= target or len(accepted) >= max_candidates or not videos:
                    break
            if count >= target or len(accepted) >= max_candidates:
                break
        if len(accepted) >= max_candidates:
            break
    return accepted, diagnostics


def build_report(request, key=None, review_decisions_dir=REVIEW_DECISIONS_DIR):
    requested_exclusions = set(
        map(str, request.get("exclude_provider_asset_ids") or [])
    )
    durable_reviewed = _load_reviewed_provider_ids(
        request.get("replenishment_session_id"),
        directory=review_decisions_dir,
    )
    effective_exclusions = requested_exclusions | durable_reviewed

    candidates, diagnostics = discover(
        request["max_candidates"],
        key=key,
        target_categories=request.get("target_categories"),
        exclude_provider_asset_ids=effective_exclusions,
        attempt=request.get("attempt", 1),
    )
    categories = request.get("target_categories") or list(CATEGORY_QUERIES)
    return {
        "schema_version": DISCOVERY_SCHEMA_VERSION,
        "request_id": request["request_id"],
        "plan_date": request["plan_date"],
        "provider": "Pexels",
        "generated_at": _utc_now(),
        "replenishment_session_id": request.get("replenishment_session_id"),
        "attempt": request.get("attempt", 1),
        "requested_excluded_provider_asset_ids": sorted(requested_exclusions),
        "durably_reviewed_provider_asset_ids": sorted(durable_reviewed),
        "effective_excluded_provider_asset_ids": sorted(effective_exclusions),
        "eligibility": {
            "minimum_duration_seconds": float(MIN_SEQUENCE_CLIP_SECONDS),
            "production_rendition_required": True,
            "visual_review_complete": False,
            "rule": (
                "API eligibility only; ChatGPT must review preview evidence before "
                "verified_preview=true."
            ),
        },
        "candidate_count": len(candidates),
        "category_targets": _category_targets(request["max_candidates"], categories),
        "candidates": candidates,
        "query_diagnostics": diagnostics,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Discover eligible long Pexels background candidates"
    )
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = build_report(_load_request(args.request))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"output": str(output), "candidate_count": report["candidate_count"]},
            indent=2,
        )
    )
    raise SystemExit(0 if report["candidate_count"] else 4)


if __name__ == "__main__":
    main()