"""Planning-time background cache safety, recency and shortlist helpers.

The canonical daily planner (ChatGPT) owns semantic story-to-background judgment.
It must inspect the checked-in cache first and only source externally when the
cache cannot supply two genuinely suitable fresh assets. This module provides
mechanical quality/recency/rendition checks and a deterministic shortlist; it is
not a replacement for the AI's semantic review.
"""

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from background_policy import rendition_is_production_suitable
from validate_media_library import REGISTRY_PATH, asset_map, load_registry

BASE = Path(__file__).parent
RESULTS_DIR = BASE / "content" / "results"

HARD_AVOID_SHORTS = 10
RECENCY_PENALTY_SHORTS = 30
MIN_SEMANTIC_SCORE = 0.45
MIN_QUALITY_SCORE = 0.78
MIN_FRESH_STRONG_CANDIDATES = 2
NEVER_USED_BONUS = 8.0


def _normal(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")


def _timestamp(record):
    raw = record.get("receipt_created_at") or record.get("youtube_verified_at") or ""
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def is_successful_receipt(record):
    """Count canonical verified private *and* scheduled successes for recency."""
    if not (
        isinstance(record, dict)
        and record.get("background_asset_id")
        and record.get("verification", {}).get("passed") is True
    ):
        return False
    state = record.get("verification_state")
    if state == "verified_private":
        return bool(
            record.get("privacy_status") == "private"
            and record.get("publish_at_absent") is True
        )
    if state in {"verified_scheduled", "verified_scheduled_published"}:
        return bool(
            record.get("publication_mode") == "scheduled"
            and record.get("publish_at")
            and record.get("privacy_status") in {"private", "public"}
        )
    return False


def load_successful_receipts(results_dir=RESULTS_DIR):
    records = []
    for path in Path(results_dir).glob("*.json") if Path(results_dir).exists() else ():
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if is_successful_receipt(record):
            records.append(record)
    return sorted(
        records,
        key=lambda item: (_timestamp(item), item.get("content_id", "")),
        reverse=True,
    )


def derive_usage_history(receipts):
    """Return immutable-receipt-derived recency; index zero is the latest Short."""
    ordered = sorted(
        (record for record in receipts if is_successful_receipt(record)),
        key=lambda item: (_timestamp(item), item.get("content_id", "")),
        reverse=True,
    )
    history = {}
    counts = defaultdict(int)
    for shorts_ago, record in enumerate(ordered):
        asset_id = record["background_asset_id"]
        counts[asset_id] += 1
        if asset_id not in history:
            history[asset_id] = {
                "shorts_ago": shorts_ago,
                "last_content_id": record.get("content_id"),
                "last_receipt_created_at": record.get("receipt_created_at"),
            }
    for asset_id, count in counts.items():
        history[asset_id]["successful_use_count"] = count
    return history


def semantic_score(asset, requirements):
    """Cheap metadata score used for cache shortlist ordering, not AI truth."""
    required_tags = {
        _normal(tag) for tag in requirements.get("visual_tags", []) if _normal(tag)
    }
    asset_tags = {
        _normal(tag) for tag in asset.get("visual_tags", []) if _normal(tag)
    }
    asset_tags.update(_normal(asset.get("title", "")).split("-"))
    if required_tags:
        tag_score = len(required_tags & asset_tags) / len(required_tags)
    else:
        tag_score = 0.65

    motion_type = _normal(requirements.get("motion_type"))
    type_score = 1.0 if not motion_type else float(
        motion_type == _normal(asset.get("motion_type"))
    )
    intensity = _normal(requirements.get("motion_intensity"))
    intensity_score = 1.0 if not intensity else float(
        intensity == _normal(asset.get("motion_intensity"))
    )
    orientation = _normal(requirements.get("orientation"))
    orientation_score = 1.0 if not orientation else float(
        _normal(asset.get("orientation")) in {orientation, "unknown"}
    )
    return round(
        0.70 * tag_score
        + 0.12 * type_score
        + 0.10 * intensity_score
        + 0.08 * orientation_score,
        6,
    )


def quality_score(asset):
    visual = float(asset.get("visual_satisfaction_score", 0)) / 100.0
    loop = float(asset.get("loopability_score", 0)) / 100.0
    captions = float(asset.get("caption_readability_score", 0)) / 100.0
    return round(0.40 * visual + 0.25 * loop + 0.35 * captions, 6)


def rendition_ready(asset):
    """True when the cache has a production-suitable non-UHD physical rendition."""
    return any(
        isinstance(item, dict) and rendition_is_production_suitable(item)
        for item in asset.get("renditions", [])
    )


def recency_penalty(shorts_ago):
    if shorts_ago is None:
        return -NEVER_USED_BONUS
    if shorts_ago < HARD_AVOID_SHORTS:
        return 1000.0
    if shorts_ago < 20:
        return 48.0 - ((shorts_ago - HARD_AVOID_SHORTS) * 2.0)
    if shorts_ago < RECENCY_PENALTY_SHORTS:
        return 24.0 - ((shorts_ago - 20) * 2.0)
    return 0.0


def rank_assets(registry, requirements, receipts):
    """Return a cache-first mechanical shortlist for the AI planner to inspect."""
    usage = derive_usage_history(receipts)
    ranked = []
    for asset in registry["assets"]:
        if asset.get("status") != "active" or asset.get("verified") is not True:
            continue
        semantic = semantic_score(asset, requirements)
        quality = quality_score(asset)
        recent = usage.get(asset["id"])
        shorts_ago = recent["shorts_ago"] if recent else None
        penalty = recency_penalty(shorts_ago)
        technically_ready = rendition_ready(asset)
        strong = (
            semantic >= MIN_SEMANTIC_SCORE
            and quality >= MIN_QUALITY_SCORE
            and technically_ready
        )
        hard_avoided = shorts_ago is not None and shorts_ago < HARD_AVOID_SHORTS
        base = (semantic * 62.0) + (quality * 38.0)
        ranked.append({
            "id": asset["id"],
            "semantic_score": semantic,
            "quality_score": quality,
            "strong_match": strong,
            "rendition_ready": technically_ready,
            "shorts_ago": shorts_ago,
            "never_used": recent is None,
            "hard_avoided": hard_avoided,
            "recency_penalty": penalty,
            "score": round(base - penalty, 6),
            "last_content_id": recent.get("last_content_id") if recent else None,
        })
    return sorted(ranked, key=lambda item: (-item["score"], item["id"]))


def audit_ai_selection(registry, primary_id, backup_id, receipts, requirements=None):
    """Mechanical safety gate for two IDs chosen semantically by ChatGPT.

    Semantic metadata scores are returned for audit visibility but are not a hard
    rejection here: the AI may understand a story/background fit that sparse cache
    tags do not capture. Quality, freshness, verification and production rendition
    cost remain hard requirements.
    """
    errors = []
    if not primary_id or not backup_id or primary_id == backup_id:
        errors.append("AI background primary and backup must be two different IDs")
    mapping = asset_map(registry)
    usage = derive_usage_history(receipts)
    audited = {}
    for slot, asset_id in (("primary", primary_id), ("backup", backup_id)):
        asset = mapping.get(asset_id)
        if not asset:
            errors.append(f"{slot} background {asset_id} is not in the cache")
            continue
        quality = quality_score(asset)
        recent = usage.get(asset_id)
        shorts_ago = recent["shorts_ago"] if recent else None
        info = {
            "id": asset_id,
            "quality_score": quality,
            "rendition_ready": rendition_ready(asset),
            "shorts_ago": shorts_ago,
            "hard_avoided": shorts_ago is not None and shorts_ago < HARD_AVOID_SHORTS,
            "semantic_score": semantic_score(asset, requirements or {}),
        }
        audited[slot] = info
        if asset.get("status") != "active" or asset.get("verified") is not True:
            errors.append(f"{slot} background {asset_id} is not active and verified")
        if quality < MIN_QUALITY_SCORE:
            errors.append(f"{slot} background {asset_id} is below quality threshold")
        if not info["rendition_ready"]:
            errors.append(
                f"{slot} background {asset_id} has no production-suitable <=1080p rendition"
            )
        if info["hard_avoided"]:
            errors.append(
                f"{slot} background {asset_id} was used within the last {HARD_AVOID_SHORTS} Shorts"
            )
    return {"passed": not errors, "errors": errors, **audited}


def select_logical_backgrounds(registry, requirements, receipts):
    """Deterministic cache shortlist/fallback; AI semantic review remains canonical."""
    ranked = rank_assets(registry, requirements, receipts)
    strong = [item for item in ranked if item["strong_match"]]
    fresh = [item for item in strong if not item["hard_avoided"]]
    expansion_required = len(fresh) < MIN_FRESH_STRONG_CANDIDATES
    selected = fresh[:2] if not expansion_required else []
    return {
        "policy": {
            "hard_avoid_shorts": HARD_AVOID_SHORTS,
            "recency_penalty_shorts": RECENCY_PENALTY_SHORTS,
            "min_semantic_score": MIN_SEMANTIC_SCORE,
            "min_quality_score": MIN_QUALITY_SCORE,
            "min_fresh_strong_candidates": MIN_FRESH_STRONG_CANDIDATES,
            "semantic_owner": "chatgpt_planner",
        },
        "requirements": requirements,
        "successful_receipts_considered": len(
            [r for r in receipts if is_successful_receipt(r)]
        ),
        "fresh_strong_candidate_count": len(fresh),
        "expansion_required": expansion_required,
        "expansion_reason": (
            "fewer_than_two_strong_fresh_cached_backgrounds"
            if expansion_required
            else None
        ),
        "primary": selected[0] if len(selected) > 0 else None,
        "backup": selected[1] if len(selected) > 1 else None,
        "ranked_candidates": ranked,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Planning-only Wacky Dramas background cache shortlist"
    )
    parser.add_argument("--tags", required=True, help="Comma-separated visual requirements")
    parser.add_argument("--motion-type", default="")
    parser.add_argument("--motion-intensity", default="medium")
    parser.add_argument("--orientation", default="")
    parser.add_argument("--registry", default=str(REGISTRY_PATH))
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    args = parser.parse_args()
    requirements = {
        "visual_tags": [tag.strip() for tag in args.tags.split(",") if tag.strip()],
        "motion_type": args.motion_type,
        "motion_intensity": args.motion_intensity,
        "orientation": args.orientation,
    }
    decision = select_logical_backgrounds(
        load_registry(args.registry),
        requirements,
        load_successful_receipts(args.results_dir),
    )
    print(json.dumps(decision, indent=2, ensure_ascii=False))
    if decision["expansion_required"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
