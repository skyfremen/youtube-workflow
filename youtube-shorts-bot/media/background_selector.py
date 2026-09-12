"""Private planning-time background ranking and anti-repetition helpers.

The private planner owns logical background choice and persistent creative history.
The public runtime only validates the frozen logical IDs and resolves physical
renditions. This module therefore ranks registered logical assets using immutable
private receipts, with retention/motion/readability as the primary signal and
story-topic relevance as a secondary boost.

Older registry entries remain valid: retention categories are inferred lazily from
existing title/tags/motion metadata unless an explicit category is present. The
previous topic-aware eligibility rule remains as a fallback when the retention-first
pool cannot safely provide two distinct assets.
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from media.background_policy import rendition_is_production_suitable
from media.validate_media_library import REGISTRY_PATH, asset_map, load_registry

BASE = Path(__file__).resolve().parents[1]
RESULTS_DIR = BASE / "content" / "results"

HARD_AVOID_SHORTS = 10
RECENCY_PENALTY_SHORTS = 30
RECENT_CATEGORY_WINDOW = 24
MIN_QUALITY_SCORE = 0.78
MIN_RETENTION_SCORE = 0.72
LEGACY_MIN_SEMANTIC_SCORE = 0.45
MIN_FRESH_STRONG_CANDIDATES = 2
NEVER_USED_BONUS = 8.0

# Canonical logical categories. Existing registry vocabulary is normalized into
# these values instead of requiring a destructive registry migration.
HIGH_RETENTION_CATEGORIES = {
    "cooking",
    "baking",
    "food_prep",
    "satisfying_process",
    "crafting",
    "cleaning",
    "assembly",
    "pov_movement",
    "city_motion",
    "licensed_gameplay",
}
GENERIC_CATEGORY = "generic"
SOCIAL_CREATOR_SOURCES = {"youtube", "tiktok", "instagram", "twitch"}

_CATEGORY_TERMS = (
    ("baking", {"baking", "bake", "bakery", "cake", "decorating", "cookie", "cookies", "dough", "pastry", "icing"}),
    ("cooking", {"cooking", "cook", "kitchen", "frying", "grilling", "saute", "stir-fry", "stirfry"}),
    ("food_prep", {"food", "food-prep", "preparation", "chopping", "slicing", "cutting", "ingredients", "meal-prep"}),
    ("cleaning", {"cleaning", "clean", "washing", "wash", "scrubbing", "scrub", "pressure-washing", "pressure-wash"}),
    ("crafting", {"craft", "crafting", "pottery", "woodworking", "knitting", "sewing", "carving", "painting"}),
    ("assembly", {"assembly", "assembling", "manufacturing", "factory", "packaging", "building", "construction"}),
    ("pov_movement", {"pov", "walking", "walk", "driving", "drive", "cycling", "ride", "riding", "train-ride", "travel-motion"}),
    ("city_motion", {"city", "urban", "traffic", "street", "streets", "timelapse", "time-lapse", "transit", "metro"}),
    ("satisfying_process", {"satisfying", "process", "kinetic", "fluid", "loop", "seamless-loop", "pouring", "mixing", "sorting"}),
)


def _normal(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")


def _timestamp(record):
    raw = record.get("receipt_created_at") or record.get("youtube_verified_at") or ""
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def is_successful_receipt(record):
    """Count canonical verified public, historical private and scheduled successes."""
    if not (
        isinstance(record, dict)
        and record.get("background_asset_id")
        and record.get("verification", {}).get("passed") is True
    ):
        return False
    state = record.get("verification_state")
    if state == "verified_public":
        return bool(
            record.get("privacy_status") == "public"
            and record.get("publish_at_absent") is True
        )
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


def _ordered_successes(receipts):
    return sorted(
        (record for record in receipts if is_successful_receipt(record)),
        key=lambda item: (_timestamp(item), item.get("content_id", "")),
        reverse=True,
    )


def derive_usage_history(receipts):
    """Return immutable-receipt-derived recency; index zero is the latest Short."""
    ordered = _ordered_successes(receipts)
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


def _asset_tokens(asset):
    tokens = set()
    for value in asset.get("visual_tags", []):
        normal = _normal(value)
        if normal:
            tokens.add(normal)
            tokens.update(part for part in normal.split("-") if part)
    for field in ("title", "motion_type"):
        normal = _normal(asset.get(field, ""))
        if normal:
            tokens.add(normal)
            tokens.update(part for part in normal.split("-") if part)
    return tokens


def retention_category(asset):
    """Return a backward-compatible canonical category for one logical asset."""
    explicit = _normal(asset.get("retention_category")).replace("-", "_")
    if explicit in HIGH_RETENTION_CATEGORIES:
        return explicit
    if explicit in {"generic", "topic_relevant"}:
        return GENERIC_CATEGORY

    tokens = _asset_tokens(asset)
    for category, terms in _CATEGORY_TERMS:
        if tokens & terms:
            return category
    return GENERIC_CATEGORY


def _licensed_gameplay_is_eligible(asset, registry):
    if retention_category(asset) != "licensed_gameplay":
        return True
    source = _normal(asset.get("source"))
    if source in SOCIAL_CREATOR_SOURCES:
        return False
    license_reference = asset.get("license_reference") or registry.get("license_reference")
    return bool(
        asset.get("verified") is True
        and asset.get("commercial_use") is True
        and str(asset.get("license") or "").strip()
        and str(asset.get("source_page") or "").strip()
        and str(license_reference or "").strip()
    )


def semantic_score(asset, requirements):
    """Topic/metadata relevance boost. It is deliberately not the primary score."""
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
        orientation == _normal(asset.get("orientation"))
    )
    return round(
        0.70 * tag_score
        + 0.12 * type_score
        + 0.10 * intensity_score
        + 0.08 * orientation_score,
        4,
    )


def quality_score(asset):
    values = (
        float(asset.get("visual_satisfaction_score") or 0),
        float(asset.get("loopability_score") or 0),
        float(asset.get("caption_readability_score") or 0),
    )
    return round((values[0] * 0.40 + values[1] * 0.25 + values[2] * 0.35) / 100.0, 4)


def retention_score(asset):
    """Score continuous visual interest independently of story-topic matching."""
    quality = quality_score(asset)
    intensity = _normal(asset.get("motion_intensity"))
    motion = {"high": 1.0, "medium": 0.82, "low": 0.45}.get(intensity, 0.62)
    motion_type = _normal(asset.get("motion_type"))
    if any(term in motion_type for term in ("static", "still")):
        motion = min(motion, 0.20)
    elif any(term in motion_type for term in ("continuous", "process", "pov", "time-lapse", "timelapse", "loop")):
        motion = min(1.0, motion + 0.08)

    category = retention_category(asset)
    category_value = 1.0 if category in HIGH_RETENTION_CATEGORIES else 0.35
    orientation = _normal(asset.get("orientation"))
    orientation_value = {"vertical": 1.0, "square": 0.86, "horizontal": 0.72}.get(orientation, 0.78)
    return round(
        0.42 * quality
        + 0.28 * motion
        + 0.18 * category_value
        + 0.12 * orientation_value,
        4,
    )


def _has_production_rendition(asset):
    return any(rendition_is_production_suitable(r) for r in asset.get("renditions", []))


def derive_category_history(registry, receipts, window=RECENT_CATEGORY_WINDOW):
    """Derive private cross-run category history from immutable successful receipts."""
    mapping = asset_map(registry)
    ordered = _ordered_successes(receipts)[: max(0, int(window))]
    categories = []
    for record in ordered:
        asset = mapping.get(record.get("background_asset_id"))
        if asset:
            categories.append(retention_category(asset))
    return {
        "recent_categories": categories,
        "counts": dict(Counter(categories)),
    }


def rank_assets(
    registry,
    requirements,
    receipts,
    planned_asset_ids=(),
    planned_categories=(),
):
    """Rank logical assets retention-first while keeping topic fit as a soft boost.

    ``planned_*`` inputs are ephemeral private batch context. They let the daily
    planner spread choices across a 24-item plan without writing mutable state to
    the public runtime or registry.
    """
    usage = derive_usage_history(receipts)
    category_history = derive_category_history(registry, receipts)
    recent_categories = category_history["recent_categories"]
    category_counts = category_history["counts"]
    planned_asset_counts = Counter(planned_asset_ids or ())
    planned_category_counts = Counter(planned_categories or ())
    ranked = []

    for asset in registry.get("assets", []):
        if asset.get("status") != "active" or asset.get("verified") is not True:
            continue
        if not _licensed_gameplay_is_eligible(asset, registry):
            continue

        semantic = semantic_score(asset, requirements)
        quality = quality_score(asset)
        retention = retention_score(asset)
        category = retention_category(asset)
        recent = usage.get(asset["id"])
        shorts_ago = recent.get("shorts_ago") if recent else None
        use_count = int(recent.get("successful_use_count") or 0) if recent else 0
        never_used = recent is None
        hard_avoided = shorts_ago is not None and shorts_ago < HARD_AVOID_SHORTS

        if hard_avoided:
            recency_penalty = 1000.0
        elif shorts_ago is None:
            recency_penalty = -NEVER_USED_BONUS
        elif shorts_ago < 20:
            recency_penalty = 48.0 - (shorts_ago - 10) * 2.0
        elif shorts_ago < RECENCY_PENALTY_SHORTS:
            recency_penalty = 24.0 - (shorts_ago - 20) * 2.0
        else:
            recency_penalty = 0.0

        # Category rotation is intentionally soft: quality/retention can still win.
        recent_category_penalty = min(10.0, float(category_counts.get(category, 0)) * 1.25)
        if category in recent_categories[:3]:
            recent_category_penalty += 3.0
        planned_category_penalty = min(9.0, float(planned_category_counts.get(category, 0)) * 2.0)
        planned_asset_penalty = min(24.0, float(planned_asset_counts.get(asset["id"], 0)) * 12.0)
        usage_penalty = min(8.0, use_count * 0.5)

        rendition_ready = _has_production_rendition(asset)
        strong_match = bool(
            retention >= MIN_RETENTION_SCORE
            and quality >= MIN_QUALITY_SCORE
            and rendition_ready
        )
        legacy_topic_match = bool(
            semantic >= LEGACY_MIN_SEMANTIC_SCORE
            and quality >= MIN_QUALITY_SCORE
            and rendition_ready
        )

        # Retention dominates. Topic relevance is capped at a 12-point boost;
        # a genuinely engaging unrelated process clip can beat a weak literal clip.
        high_retention_bonus = 8.0 if category in HIGH_RETENTION_CATEGORIES else 0.0
        base = retention * 80.0 + semantic * 12.0 + high_retention_bonus
        total_penalty = (
            recency_penalty
            + recent_category_penalty
            + planned_category_penalty
            + planned_asset_penalty
            + usage_penalty
        )
        ranked.append({
            **asset,
            "retention_category": category,
            "semantic_score": semantic,
            "quality_score": quality,
            "retention_score": retention,
            "base_score": round(base, 3),
            "recency_penalty": round(recency_penalty, 3),
            "category_penalty": round(recent_category_penalty + planned_category_penalty, 3),
            "planned_asset_penalty": round(planned_asset_penalty, 3),
            "usage_penalty": round(usage_penalty, 3),
            "score": round(base - total_penalty, 3),
            "shorts_ago": shorts_ago,
            "successful_use_count": use_count,
            "never_used": never_used,
            "hard_avoided": hard_avoided,
            "rendition_ready": rendition_ready,
            "strong_match": strong_match,
            "legacy_topic_match": legacy_topic_match,
        })
    return sorted(
        ranked,
        key=lambda item: (item["score"], item["retention_score"], item["quality_score"]),
        reverse=True,
    )


def select_logical_backgrounds(
    registry,
    requirements,
    receipts,
    planned_asset_ids=(),
    planned_categories=(),
):
    ranked = rank_assets(
        registry,
        requirements,
        receipts,
        planned_asset_ids=planned_asset_ids,
        planned_categories=planned_categories,
    )
    retention_pool = [
        item for item in ranked if item["strong_match"] and not item["hard_avoided"]
    ]
    pool = list(retention_pool)
    already = {item["id"] for item in pool}
    # Preserve the previous topic-aware selector as a fallback without duplicating
    # orchestration. Legacy candidates are considered only after all eligible
    # retention-first candidates, then licensed sourcing may be requested.
    for item in ranked:
        if item["id"] in already or item["hard_avoided"]:
            continue
        if item["legacy_topic_match"]:
            pool.append(item)
            already.add(item["id"])

    if len(pool) < MIN_FRESH_STRONG_CANDIDATES:
        return {
            "primary": None,
            "backup": None,
            "expansion_required": True,
            "used_legacy_topic_fallback": bool(pool) and len(retention_pool) < 2,
            "reason": "fewer than two acceptable retention-first or legacy topic-aware backgrounds",
            "ranked_candidates": ranked,
        }

    primary = pool[0]
    backup = pool[1]
    # If two retention-qualified choices exist, rotation stays strictly within that
    # tier. A different-category legacy fallback must never displace valid stronger
    # retention footage merely to improve category variety.
    rotation_pool = retention_pool[1:] if len(retention_pool) >= 2 else pool[1:]
    for candidate in rotation_pool:
        if (
            candidate["retention_category"] != primary["retention_category"]
            and candidate["score"] >= backup["score"] - 5.0
        ):
            backup = candidate
            break
    used_legacy = not (primary["strong_match"] and backup["strong_match"])
    return {
        "primary": primary["id"],
        "backup": backup["id"],
        "expansion_required": False,
        "used_legacy_topic_fallback": used_legacy,
        "reason": (
            "retention-first cache supplied two acceptable backgrounds"
            if not used_legacy
            else "retention-first pool supplemented by existing topic-aware fallback"
        ),
        "ranked_candidates": ranked,
    }


def audit_ai_selection(registry, primary_id, backup_id, receipts, requirements=None):
    """Mechanical safety gate for logical IDs chosen by the private planner."""
    requirements = requirements or {}
    assets = asset_map(registry)
    errors = []
    if primary_id == backup_id:
        errors.append("primary and backup background IDs must differ")
    ranked = {item["id"]: item for item in rank_assets(registry, requirements, receipts)}
    selected = []
    for label, asset_id in (("primary", primary_id), ("backup", backup_id)):
        asset = assets.get(asset_id)
        if not asset:
            errors.append(f"{label} background {asset_id} is missing from cache")
            continue
        audit = ranked.get(asset_id)
        if not audit:
            errors.append(f"{label} background {asset_id} is not eligible, active and verified")
            continue
        if audit["quality_score"] < MIN_QUALITY_SCORE:
            errors.append(f"{label} background {asset_id} is below the quality floor")
        if (
            audit["retention_score"] < MIN_RETENTION_SCORE
            and not audit["legacy_topic_match"]
        ):
            errors.append(
                f"{label} background {asset_id} is below the retention floor and does not qualify for topic fallback"
            )
        if audit["hard_avoided"]:
            errors.append(f"{label} background {asset_id} was used within the last 10 Shorts")
        if not audit["rendition_ready"]:
            errors.append(f"{label} background {asset_id} has no qualifying post-crop 1080x1920 rendition")
        selected.append((label, audit))
    return {
        "passed": not errors,
        "errors": errors,
        "primary": next((x for label, x in selected if label == "primary"), None),
        "backup": next((x for label, x in selected if label == "backup"), None),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements")
    parser.add_argument("--primary-id")
    parser.add_argument("--backup-id")
    parser.add_argument("--registry", default=str(REGISTRY_PATH))
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    parser.add_argument("--planned-asset-id", action="append", default=[])
    parser.add_argument("--planned-category", action="append", default=[])
    args = parser.parse_args()
    registry = load_registry(args.registry)
    receipts = load_successful_receipts(args.results_dir)
    requirements = {}
    if args.requirements:
        requirements = json.loads(Path(args.requirements).read_text(encoding="utf-8"))
    if args.primary_id or args.backup_id:
        if not args.primary_id or not args.backup_id:
            raise SystemExit("Both --primary-id and --backup-id are required for AI-selection audit")
        result = audit_ai_selection(registry, args.primary_id, args.backup_id, receipts, requirements)
    else:
        result = select_logical_backgrounds(
            registry,
            requirements,
            receipts,
            planned_asset_ids=args.planned_asset_id,
            planned_categories=args.planned_category,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("expansion_required") or result.get("passed") is False:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
