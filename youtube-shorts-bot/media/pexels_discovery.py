"""Deterministic Pexels discovery for long, production-suitable background clips.

Provider/API eligibility only. Schema v3 binds targeted attempts to one frozen
planner invocation and readiness deficit snapshot. Schemas v1/v2 remain accepted
for existing immutable requests.

Review decisions are durable repository state. For session requests, discovery
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
from media.replenishment_state import (
    MAX_REPLENISH_ATTEMPTS,
    validate_planner_invocation,
    validate_review_decision,
)

DISCOVERY_SCHEMA_VERSION = 1
LEGACY_REQUEST_SCHEMA_VERSION = 1
SESSION_REQUEST_SCHEMA_VERSION = 2
REQUEST_SCHEMA_VERSION = 3
DEFAULT_MAX_CANDIDATES = 48
MAX_MAX_CANDIDATES = 80
SEARCH_PER_PAGE = 80
SEARCH_MAX_PAGES = 3
REVIEW_DECISIONS_DIR = (
    Path(__file__).resolve().parents[1]
    / "content"
    / "background-sourcing"
    / "review-decisions"
)
DISCOVERY_RESULTS_DIR = REVIEW_DECISIONS_DIR.parent / "discovery-results"
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "media-library" / "backgrounds.json"

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

ATTEMPT_QUERY_SUFFIXES = (
    "",
    " close up",
    " professional",
    " detailed process",
    " continuous action",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _load_request_dict(data):
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
    elif version == SESSION_REQUEST_SCHEMA_VERSION:
        expected = base | {
            "target_categories",
            "exclude_provider_asset_ids",
            "replenishment_session_id",
            "attempt",
        }
        if set(data) != expected:
            raise ValueError("schema-v2 discovery request has invalid fields")
    elif version == REQUEST_SCHEMA_VERSION:
        expected = base | {
            "target_categories",
            "category_deficits",
            "required_new_assets_at_least",
            "exclude_provider_asset_ids",
            "replenishment_session_id",
            "planner_invocation",
            "attempt",
        }
        if set(data) != expected:
            raise ValueError("schema-v3 discovery request has invalid fields")
    else:
        raise ValueError("discovery request schema_version must be 1, 2, or 3")

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
    if version in {SESSION_REQUEST_SCHEMA_VERSION, REQUEST_SCHEMA_VERSION} and not re.fullmatch(
        r"rs-[A-Za-z0-9-]{8,96}", str(session_id or "")
    ):
        raise ValueError(
            "replenishment_session_id must match rs-[A-Za-z0-9-]{8,96}"
        )
    if version == REQUEST_SCHEMA_VERSION:
        invocation_errors = validate_planner_invocation(data["planner_invocation"])
        if invocation_errors:
            raise ValueError("invalid planner_invocation: " + "; ".join(invocation_errors))
        if data["plan_date"] != data["planner_invocation"]["singapore_date"]:
            raise ValueError("plan_date must equal planner_invocation.singapore_date")
        deficits = data["category_deficits"]
        if not isinstance(deficits, dict) or set(deficits) != set(CATEGORY_QUERIES):
            raise ValueError("category_deficits must contain every known category")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in deficits.values()):
            raise ValueError("category deficits must be non-negative integers")
        expected_targets = [category for category in CATEGORY_QUERIES if deficits[category] > 0]
        if targets != expected_targets:
            raise ValueError("target_categories must exactly match positive category deficits")
        required = data["required_new_assets_at_least"]
        if isinstance(required, bool) or not isinstance(required, int) or required < 1:
            raise ValueError("required_new_assets_at_least must be a positive integer")
    return data


def _load_request(path):
    return _load_request_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _validate_review_decision_doc(data, path="<memory>"):
    state_errors = validate_review_decision(data)
    if state_errors:
        raise ValueError(f"{path}: " + "; ".join(state_errors))
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


def _load_prior_discovered_provider_ids(replenishment_session_id, directory=DISCOVERY_RESULTS_DIR):
    if not replenishment_session_id or not Path(directory).exists():
        return set()
    discovered = set()
    for path in sorted(Path(directory).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("replenishment_session_id") != replenishment_session_id:
            continue
        discovered.update(
            str(item.get("provider_asset_id"))
            for item in data.get("candidates", [])
            if str(item.get("provider_asset_id") or "").isdigit()
        )
    return discovered


def _load_active_verified_provider_ids(path=REGISTRY_PATH):
    path = Path(path)
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(item.get("provider_asset_id"))
        for item in data.get("assets", [])
        if item.get("status") == "active"
        and item.get("verified") is True
        and str(item.get("provider_asset_id") or "").isdigit()
    }


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


def queries_for_attempt(category, attempt, request_schema_version=REQUEST_SCHEMA_VERSION):
    """Return a deterministic query strategy that changes across bounded retries."""
    queries = CATEGORY_QUERIES[category]
    offset = (attempt - 1) % len(queries)
    rotated = queries[offset:] + queries[:offset]
    if request_schema_version < REQUEST_SCHEMA_VERSION:
        return tuple(rotated)
    suffix = ATTEMPT_QUERY_SUFFIXES[attempt - 1]
    return tuple(query + suffix for query in rotated)


def discover(
    max_candidates=DEFAULT_MAX_CANDIDATES,
    key=None,
    target_categories=None,
    exclude_provider_asset_ids=None,
    attempt=1,
    request_schema_version=LEGACY_REQUEST_SCHEMA_VERSION,
):
    categories = list(target_categories or CATEGORY_QUERIES)
    accepted = []
    seen = set(map(str, exclude_provider_asset_ids or []))
    diagnostics = []
    targets = _category_targets(max_candidates, categories)

    for category in categories:
        count = 0
        target = targets[category]
        queries = queries_for_attempt(category, attempt, request_schema_version)

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


def build_report(
    request,
    key=None,
    review_decisions_dir=REVIEW_DECISIONS_DIR,
    discovery_results_dir=DISCOVERY_RESULTS_DIR,
    registry_path=REGISTRY_PATH,
):
    requested_exclusions = set(
        map(str, request.get("exclude_provider_asset_ids") or [])
    )
    durable_reviewed = _load_reviewed_provider_ids(
        request.get("replenishment_session_id"),
        directory=review_decisions_dir,
    )
    prior_discovered = _load_prior_discovered_provider_ids(
        request.get("replenishment_session_id"), discovery_results_dir
    )
    active_verified = _load_active_verified_provider_ids(registry_path)
    effective_exclusions = requested_exclusions | durable_reviewed | prior_discovered | active_verified

    candidates, diagnostics = discover(
        request["max_candidates"],
        key=key,
        target_categories=request.get("target_categories"),
        exclude_provider_asset_ids=effective_exclusions,
        attempt=request.get("attempt", 1),
        request_schema_version=request.get("schema_version", LEGACY_REQUEST_SCHEMA_VERSION),
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
        "planner_invocation": request.get("planner_invocation"),
        "category_deficits": request.get("category_deficits"),
        "required_new_assets_at_least": request.get("required_new_assets_at_least"),
        "requested_excluded_provider_asset_ids": sorted(requested_exclusions),
        "durably_reviewed_provider_asset_ids": sorted(durable_reviewed),
        "prior_discovered_provider_asset_ids": sorted(prior_discovered),
        "active_verified_provider_asset_ids": sorted(active_verified),
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

    request = _load_request(args.request)
    report = build_report(request)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"output": str(output), "candidate_count": report["candidate_count"]},
            indent=2,
        )
    )
    # Empty bounded-session rounds are valid deterministic results: the planner
    # advances the same session with a diversified next attempt. Historical
    # one-shot schema-v1 callers retain their established no-candidate exit code.
    raise SystemExit(
        0
        if report["candidate_count"] or request["schema_version"] >= SESSION_REQUEST_SCHEMA_VERSION
        else 4
    )


if __name__ == "__main__":
    main()
