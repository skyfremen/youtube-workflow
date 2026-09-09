"""Build a deterministic Wacky Dramas analytics learning model.

Raw YouTube metrics are first converted to within-cohort percentiles. The model
then attributes smoothed performance to controlled creative dimensions. Planning
uses the resulting 0-100 historical_attribute_fit; it never feeds raw subscriber,
share, retention, or view counts directly into growth_planner's 0-100 scorer.
"""
from __future__ import annotations

from collections import defaultdict
from math import isfinite

from growth_config import (
    ANALYTICS_ATTRIBUTE_PRIOR_STRENGTH,
    ANALYTICS_MIN_MATURE_VIDEOS,
    RAW_ANALYTICS_WEIGHTS,
    TITLE_WEIGHTS,
)

COHORT_ORDER = ("7d", "72h", "24h")
DIMENSION_WEIGHTS = {
    "category": 15,
    "conflict": 10,
    "primary_emotion": 10,
    "protagonist_role": 5,
    "antagonist_role": 5,
    "opening_style": 20,
    "title_style": 20,
    "ending_style": 10,
    "duration_bucket": 5,
}


def _number(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def _percentile_scores(values):
    """Return percentile scores with average ranks for ties."""
    numeric = [(idx, _number(value)) for idx, value in enumerate(values)]
    present = [(idx, value) for idx, value in numeric if value is not None]
    out = [None] * len(values)
    if not present:
        return out
    if len(present) == 1:
        out[present[0][0]] = 50.0
        return out
    ordered = sorted(present, key=lambda item: item[1])
    pos = 0
    while pos < len(ordered):
        end = pos + 1
        while end < len(ordered) and ordered[end][1] == ordered[pos][1]:
            end += 1
        average_rank = (pos + (end - 1)) / 2.0
        score = round(100.0 * average_rank / (len(ordered) - 1), 3)
        for idx, _ in ordered[pos:end]:
            out[idx] = score
        pos = end
    return out


def performance_scores(entries):
    """Normalize raw metrics within one age-matched cohort and return 0-100 row scores."""
    if not entries:
        return []
    normalized = {
        key: _percentile_scores([e.get("metrics", {}).get(key) for e in entries])
        for key in RAW_ANALYTICS_WEIGHTS
    }
    scores = []
    for index, _entry in enumerate(entries):
        usable = []
        for key, weight in RAW_ANALYTICS_WEIGHTS.items():
            value = normalized[key][index]
            if value is not None:
                usable.append((value, float(weight)))
        if not usable:
            scores.append(None)
            continue
        denominator = sum(weight for _, weight in usable)
        scores.append(round(sum(value * weight for value, weight in usable) / denominator, 3))
    return scores


def duration_bucket(seconds):
    value = _number(seconds)
    if value is None:
        return None
    if value < 120:
        return "<120"
    if value < 135:
        return "120-134"
    if value < 150:
        return "135-149"
    if value < 165:
        return "150-164"
    return "165-178"


def _weighted_title_score(item):
    if not isinstance(item, dict) or item.get("truthful") is not True:
        return -1.0
    components = item.get("score_components")
    if not isinstance(components, dict):
        return _number(item.get("score")) or -1.0
    usable = []
    for key, weight in TITLE_WEIGHTS.items():
        value = _number(components.get(key))
        if value is None:
            return -1.0
        usable.append((value, weight))
    return sum(value * weight for value, weight in usable) / sum(TITLE_WEIGHTS.values())


def candidate_dimensions(candidate):
    attrs = candidate.get("attributes") if isinstance(candidate.get("attributes"), dict) else {}
    planning = candidate.get("planning") if isinstance(candidate.get("planning"), dict) else {}
    planning_attrs = planning.get("attributes") if isinstance(planning.get("attributes"), dict) else {}
    merged = {**planning_attrs, **attrs}
    for key in (
        "conflict", "primary_emotion", "protagonist_role", "antagonist_role",
        "opening_style", "title_style", "ending_style",
    ):
        if candidate.get(key) is not None:
            merged[key] = candidate.get(key)

    title_style = candidate.get("selected_title_style") or merged.get("title_style")
    if not title_style:
        titles = candidate.get("title_candidates") or []
        if titles:
            best = max(titles, key=_weighted_title_score)
            title_style = best.get("style")

    duration = (
        candidate.get("target_duration_seconds")
        or planning.get("target_duration_seconds")
        or candidate.get("video_duration_seconds")
    )
    return {
        "category": candidate.get("category") or merged.get("category"),
        "conflict": merged.get("conflict"),
        "primary_emotion": merged.get("primary_emotion"),
        "protagonist_role": merged.get("protagonist_role"),
        "antagonist_role": merged.get("antagonist_role"),
        "opening_style": merged.get("opening_style"),
        "title_style": title_style,
        "ending_style": merged.get("ending_style"),
        "duration_bucket": duration_bucket(duration),
    }


def _cohort_entries(snapshot, milestones, label):
    rows = {
        str(row.get("video")): row for row in snapshot.get("videos", [])
        if row.get("growth_eligible")
    }
    entries = []
    for video_id, snapshots in milestones.get("videos", {}).items():
        point = snapshots.get(label)
        row = rows.get(str(video_id))
        if not point or not row:
            continue
        metrics = point.get("metrics")
        dimensions = row.get("growth_dimensions")
        if not isinstance(metrics, dict) or not isinstance(dimensions, dict):
            continue
        entries.append({
            "video": str(video_id),
            "metrics": metrics,
            "dimensions": dimensions,
            "age_hours": point.get("age_hours"),
        })
    return entries


def _dimension_model(entries, scores):
    usable_scores = [score for score in scores if score is not None]
    overall = round(sum(usable_scores) / len(usable_scores), 3) if usable_scores else None
    groups = {key: defaultdict(list) for key in DIMENSION_WEIGHTS}
    for entry, score in zip(entries, scores):
        if score is None:
            continue
        dims = entry["dimensions"]
        for key in DIMENSION_WEIGHTS:
            value = dims.get(key)
            if value:
                groups[key][str(value)].append(score)

    dimensions = {}
    prior = float(ANALYTICS_ATTRIBUTE_PRIOR_STRENGTH)
    for key, values in groups.items():
        dimensions[key] = {}
        for value, group_scores in values.items():
            raw_mean = sum(group_scores) / len(group_scores)
            shrunk = raw_mean if overall is None else (
                (sum(group_scores) + prior * overall) / (len(group_scores) + prior)
            )
            dimensions[key][value] = {
                "score": round(shrunk, 3),
                "sample_size": len(group_scores),
                "raw_mean": round(raw_mean, 3),
            }
    return overall, dimensions


def build_model(snapshot, milestones):
    """Build 24h/72h/7d models and choose the strongest adequately sized cohort."""
    cohorts = {}
    for label in ("24h", "72h", "7d"):
        entries = _cohort_entries(snapshot, milestones, label)
        scores = performance_scores(entries)
        overall, dimensions = _dimension_model(entries, scores)
        cohorts[label] = {
            "video_count": len([x for x in scores if x is not None]),
            "overall_score": overall,
            "dimension_weights": DIMENSION_WEIGHTS,
            "dimensions": dimensions,
        }

    active = next(
        (
            label for label in COHORT_ORDER
            if cohorts[label]["video_count"] >= ANALYTICS_MIN_MATURE_VIDEOS
        ),
        None,
    )
    evidence_count = int(snapshot.get("growth_video_count") or 0)
    return {
        "schema_version": 2,
        "epoch": snapshot.get("analytics_epoch"),
        "active_cohort": active,
        "analytics_evidence_count": evidence_count,
        "analytics_enabled": bool(active and evidence_count > 0),
        "cohorts": cohorts,
    }


def score_candidate(candidate, model):
    """Return a smoothed historical fit for one future candidate."""
    if not isinstance(model, dict) or not model.get("analytics_enabled"):
        return None
    label = model.get("active_cohort")
    cohort = model.get("cohorts", {}).get(label, {})
    overall = _number(cohort.get("overall_score"))
    if overall is None:
        return None

    dims = candidate_dimensions(candidate)
    matches = []
    for key, weight in DIMENSION_WEIGHTS.items():
        value = dims.get(key)
        record = cohort.get("dimensions", {}).get(key, {}).get(str(value)) if value else None
        if not record:
            continue
        score = _number(record.get("score"))
        if score is not None:
            matches.append((score, float(weight), key, str(value), int(record.get("sample_size") or 0)))

    if not matches:
        return {
            "historical_attribute_fit": round(overall, 3),
            "matched_dimensions": [],
            "matched_weight": 0,
            "active_cohort": label,
            "fallback_to_cohort_mean": True,
        }

    matched_weight = sum(weight for _, weight, *_ in matches)
    weighted = sum(score * weight for score, weight, *_ in matches)
    weighted += overall * (sum(DIMENSION_WEIGHTS.values()) - matched_weight)
    score = weighted / sum(DIMENSION_WEIGHTS.values())
    return {
        "historical_attribute_fit": round(score, 3),
        "matched_dimensions": [
            {
                "dimension": key,
                "value": value,
                "sample_size": n,
                "score": round(score_value, 3),
            }
            for score_value, _, key, value, n in matches
        ],
        "matched_weight": round(matched_weight, 3),
        "active_cohort": label,
        "fallback_to_cohort_mean": False,
    }
