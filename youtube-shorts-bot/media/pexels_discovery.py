"""Deterministic Pexels discovery for long, production-suitable background clips.

This module performs provider/API eligibility filtering only. It does not mark
candidates as visually reviewed and does not write to the active registry.
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
REQUEST_SCHEMA_VERSION = 1
DEFAULT_MAX_CANDIDATES = 48
MAX_MAX_CANDIDATES = 80
SEARCH_PER_PAGE = 80
SEARCH_MAX_PAGES = 3

CATEGORY_QUERIES = {
    "cooking": ("cooking process", "cooking food"),
    "baking": ("baking process", "bread baking", "pastry making"),
    "food_prep": ("food preparation", "meal prep", "cutting vegetables"),
    "satisfying_process": ("satisfying process", "oddly satisfying process"),
    "crafting": ("craft making", "woodworking", "pottery making"),
    "cleaning": ("cleaning restoration", "pressure washing", "deep cleaning"),
    "assembly": ("industrial assembly", "factory assembly", "manufacturing process"),
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
    expected = {"schema_version", "plan_date", "request_id", "max_candidates"}
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("discovery request must contain exactly schema_version, plan_date, request_id, max_candidates")
    if data["schema_version"] != REQUEST_SCHEMA_VERSION:
        raise ValueError(f"discovery request schema_version must be {REQUEST_SCHEMA_VERSION}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data["plan_date"])):
        raise ValueError("plan_date must be YYYY-MM-DD")
    if not re.fullmatch(r"dr-[A-Za-z0-9-]{8,96}", str(data["request_id"])):
        raise ValueError("request_id must match dr-[A-Za-z0-9-]{8,96}")
    max_candidates = data["max_candidates"]
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
        raise ValueError("max_candidates must be an integer")
    if not 1 <= max_candidates <= MAX_MAX_CANDIDATES:
        raise ValueError(f"max_candidates must be 1-{MAX_MAX_CANDIDATES}")
    return data


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
    suitable.sort(key=lambda item: (int(item["width"]) * int(item["height"]), float(item.get("fps") or 999), str(item.get("id") or "")))

    # Review transport only needs exact asset identity and enough pixels for a contact
    # sheet. Prefer a small provider rendition while independently requiring at least
    # one production-suitable rendition above.
    review_renditions = [
        item for item in renditions
        if int(item.get("width") or 0) >= 360 and int(item.get("height") or 0) >= 360
    ] or list(renditions)
    review_renditions.sort(
        key=lambda item: (
            int(item.get("width") or 0) * int(item.get("height") or 0),
            float(item.get("fps") or 999),
            str(item.get("id") or ""),
        )
    )
    preview_rendition = review_renditions[0]
    provider_id = str(video.get("id") or "").strip()
    source_page = str(video.get("url") or "").strip()
    preview_image = str(video.get("image") or "").strip()
    if not provider_id.isdigit() or not source_page or not preview_image:
        return None
    return {
        "provider_asset_id": provider_id,
        "source_page": source_page,
        "duration_seconds": duration,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "creator": str(video.get("user", {}).get("name") or "Unknown"),
        "discovery_category": category,
        "discovery_query": query,
        "preview_image_url": preview_image,
        "preview_video_url": str(preview_rendition["direct_url"]),
        "preview_video_width": int(preview_rendition["width"]),
        "preview_video_height": int(preview_rendition["height"]),
        "preview_video_fps": preview_rendition.get("fps"),
        "production_suitable_rendition_count": len(suitable),
    }


def _category_targets(max_candidates):
    categories = list(CATEGORY_QUERIES)
    if max_candidates == DEFAULT_MAX_CANDIDATES:
        return dict(CATEGORY_TARGETS_48)
    base, remainder = divmod(max_candidates, len(categories))
    return {category: base + (1 if index < remainder else 0) for index, category in enumerate(categories)}


def discover(max_candidates=DEFAULT_MAX_CANDIDATES, key=None):
    accepted, seen, diagnostics = [], set(), []
    targets = _category_targets(max_candidates)
    for category, queries in CATEGORY_QUERIES.items():
        accepted_for_category = 0
        target = targets[category]
        if target <= 0:
            continue
        for query in queries:
            for page in range(1, SEARCH_MAX_PAGES + 1):
                payload = api_get(f"search?query={quote_plus(query)}&per_page={SEARCH_PER_PAGE}&page={page}", key=key)
                videos = payload.get("videos", []) if isinstance(payload, dict) else []
                eligible_for_page = 0
                for video in videos:
                    provider_id = str(video.get("id") or "").strip()
                    if not provider_id or provider_id in seen:
                        continue
                    candidate = _eligible_candidate(video, category, query)
                    if not candidate:
                        continue
                    seen.add(provider_id)
                    accepted.append(candidate)
                    accepted_for_category += 1
                    eligible_for_page += 1
                    if accepted_for_category >= target or len(accepted) >= max_candidates:
                        break
                diagnostics.append({"category": category, "target": target, "query": query, "page": page, "returned": len(videos), "new_eligible": eligible_for_page})
                if accepted_for_category >= target or len(accepted) >= max_candidates or not videos:
                    break
            if accepted_for_category >= target or len(accepted) >= max_candidates:
                break
        if len(accepted) >= max_candidates:
            break
    return accepted, diagnostics


def build_report(request, key=None):
    candidates, diagnostics = discover(request["max_candidates"], key=key)
    return {
        "schema_version": DISCOVERY_SCHEMA_VERSION,
        "request_id": request["request_id"],
        "plan_date": request["plan_date"],
        "provider": "Pexels",
        "generated_at": _utc_now(),
        "eligibility": {
            "minimum_duration_seconds": float(MIN_SEQUENCE_CLIP_SECONDS),
            "production_rendition_required": True,
            "visual_review_complete": False,
            "rule": "API eligibility only; ChatGPT must review preview evidence before verified_preview=true.",
        },
        "candidate_count": len(candidates),
        "category_targets": _category_targets(request["max_candidates"]),
        "candidates": candidates,
        "query_diagnostics": diagnostics,
    }


def main():
    parser = argparse.ArgumentParser(description="Discover eligible long Pexels background candidates")
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    request = _load_request(args.request)
    report = build_report(request)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "candidate_count": report["candidate_count"]}, indent=2))
    if report["candidate_count"] == 0:
        raise SystemExit(4)


if __name__ == "__main__":
    main()
