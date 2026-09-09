"""Deterministic selection/validation engine for the Wacky Dramas growth funnel.

AI is used for semantic creative work (premises, outlines, titles and scripts),
while this module owns the auditable arithmetic, duplicate checks, analytics
confidence, diversity policy and hourly schedule. Rejected candidates never
reach media/TTS/render/upload stages.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from growth_config import (
    ANALYTICS_CONFIDENCE_SCALE,
    CANONICAL_TIMEZONE,
    DAILY_PUBLISH_COUNT,
    DIVERSITY_LIMITS,
    EDITORIAL_WEIGHTS,
    EXPLORATION_FRACTION,
    HOOK_WEIGHTS,
    MAX_ANALYTICS_WEIGHT,
    MIN_FINAL_EDITORIAL_SCORE,
    MIN_HOOK_SCORE,
    MIN_TITLE_SCORE,
    NEAR_DUPLICATE_THRESHOLD,
    PERFORMANCE_WEIGHTS,
    RAW_CANDIDATE_COUNT,
    SEMIFINALIST_TARGET,
    SOFT_SIMILARITY_THRESHOLD,
    TITLE_WEIGHTS,
    TITLES_PER_SEMIFINALIST,
)

TOKEN_RE = re.compile(r"[a-z0-9]+")


class GrowthPlanError(ValueError):
    pass


def _bounded(value, name="score"):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise GrowthPlanError(f"{name} must be numeric") from None
    if not 0 <= value <= 100:
        raise GrowthPlanError(f"{name} must be between 0 and 100")
    return value


def weighted_score(components, weights):
    """Return a 0-100 weighted score; missing components are not fabricated."""
    if not isinstance(components, dict):
        raise GrowthPlanError("score components must be an object")
    missing = [key for key in weights if key not in components]
    if missing:
        raise GrowthPlanError("missing score components: " + ", ".join(missing))
    total_weight = sum(weights.values())
    return round(sum(_bounded(components[k], k) * weights[k] for k in weights) / total_weight, 3)


def editorial_score(candidate):
    return weighted_score(candidate.get("editorial_components"), EDITORIAL_WEIGHTS)


def title_score(title):
    if title.get("truthful") is not True:
        return 0.0
    return weighted_score(title.get("score_components"), TITLE_WEIGHTS)


def hook_score(candidate):
    return weighted_score(candidate.get("hook_components"), HOOK_WEIGHTS)


def _tokens(value):
    return set(TOKEN_RE.findall(str(value or "").lower()))


def candidate_fingerprint(candidate):
    fields = [
        candidate.get("premise"), candidate.get("conflict"), candidate.get("relationship_context"),
        candidate.get("likely_payoff"), candidate.get("ending_style"), candidate.get("opening_line"),
    ]
    return _tokens(" ".join(str(x or "") for x in fields))


def similarity(a, b):
    """Deterministic semantic-ish similarity using story-bearing fields, not title equality."""
    left, right = candidate_fingerprint(a), candidate_fingerprint(b)
    if not left or not right:
        return 0.0
    jaccard = len(left & right) / len(left | right)
    # Structural overlap matters even when wording changes.
    structural = sum(
        1 for key in ("category", "conflict", "protagonist_role", "antagonist_role", "ending_style")
        if a.get(key) and a.get(key) == b.get(key)
    ) / 5.0
    return round((0.72 * jaccard) + (0.28 * structural), 4)


def hard_reject(candidate, accepted_today=(), recent=()):
    required = ("candidate_id", "premise", "category", "conflict", "likely_payoff", "editorial_components")
    if any(not candidate.get(k) for k in required):
        return "malformed_candidate"
    if candidate.get("hard_reject_reason"):
        return str(candidate["hard_reject_reason"])
    try:
        score = editorial_score(candidate)
    except GrowthPlanError:
        return "malformed_editorial_score"
    if candidate.get("can_sustain_target_duration") is not True:
        return "cannot_sustain_target_duration"
    if not str(candidate.get("likely_payoff", "")).strip():
        return "missing_payoff"
    for other in [*accepted_today, *recent]:
        sim = similarity(candidate, other)
        if sim >= NEAR_DUPLICATE_THRESHOLD:
            return f"near_duplicate:{other.get('candidate_id') or other.get('content_id') or 'recent'}:{sim:.3f}"
    if score < 45:  # very weak ideas die before normal ranking; finals have a stricter gate.
        return "editorially_too_weak"
    return None


def filter_candidates(candidates, recent=()):
    accepted, rejected = [], []
    seen_ids = set()
    for candidate in candidates:
        if candidate.get("candidate_id") in seen_ids:
            rejected.append({"candidate": candidate, "reason": "duplicate_candidate_id"})
            continue
        seen_ids.add(candidate.get("candidate_id"))
        reason = hard_reject(candidate, accepted_today=accepted, recent=recent)
        if reason:
            rejected.append({"candidate": candidate, "reason": reason})
        else:
            accepted.append(candidate)
    return accepted, rejected


def analytics_weight(video_count):
    try:
        count = max(0, int(video_count or 0))
    except (TypeError, ValueError):
        return 0.0
    if count == 0:
        return 0.0
    # Smooth confidence transition; never reaches 100% analytics.
    weight = MAX_ANALYTICS_WEIGHT * (1.0 - math.exp(-count / ANALYTICS_CONFIDENCE_SCALE))
    return round(min(MAX_ANALYTICS_WEIGHT, weight), 4)


def normalized_performance_score(metrics):
    """Weighted 0-100 score using only actually available normalized metrics."""
    if not isinstance(metrics, dict):
        return None
    usable = []
    for key, weight in PERFORMANCE_WEIGHTS.items():
        value = metrics.get(key)
        if value is None:
            continue
        usable.append((_bounded(value, key), weight))
    if not usable:
        return None
    denominator = sum(weight for _, weight in usable)
    return round(sum(value * weight for value, weight in usable) / denominator, 3)


def blend_scores(editorial, analytics, weight):
    editorial = _bounded(editorial, "editorial")
    weight = max(0.0, min(MAX_ANALYTICS_WEIGHT, float(weight or 0)))
    if analytics is None or weight == 0:
        return round(editorial, 3)
    analytics = _bounded(analytics, "analytics")
    return round(editorial * (1 - weight) + analytics * weight, 3)


def select_best_title(candidate):
    titles = candidate.get("title_candidates") or []
    if len(titles) < TITLES_PER_SEMIFINALIST:
        raise GrowthPlanError(f"{candidate.get('candidate_id')}: requires at least {TITLES_PER_SEMIFINALIST} title candidates")
    scored = []
    for title in titles:
        score = title_score(title)
        scored.append((score, title))
    score, best = max(scored, key=lambda x: x[0])
    if score < MIN_TITLE_SCORE:
        raise GrowthPlanError(f"{candidate.get('candidate_id')}: no title clears minimum quality")
    return best, score


def score_semifinalist(candidate, analytics_w=0.0):
    editorial = editorial_score(candidate)
    title, title_value = select_best_title(candidate)
    hook_value = hook_score(candidate)
    if editorial < MIN_FINAL_EDITORIAL_SCORE:
        raise GrowthPlanError("editorial_below_final_threshold")
    if hook_value < MIN_HOOK_SCORE:
        raise GrowthPlanError("hook_below_final_threshold")
    analytics_value = normalized_performance_score(candidate.get("analytics_metrics"))
    blended = blend_scores(editorial, analytics_value, analytics_w)
    # Title/hook remain explicit final-selection signals after editorial/analytics blend.
    final = round((blended * 0.70) + (title_value * 0.18) + (hook_value * 0.12), 3)
    output = dict(candidate)
    output.update({
        "editorial_score": editorial,
        "analytics_score": analytics_value,
        "analytics_weight": analytics_w,
        "selected_title": title["title"],
        "selected_title_style": title["style"],
        "selected_title_score": title_value,
        "hook_score": hook_value,
        "final_score": final,
    })
    return output


def _fits_diversity(candidate, counts):
    values = {
        "category": candidate.get("category"),
        "conflict": candidate.get("conflict"),
        "title_style": candidate.get("selected_title_style"),
    }
    return all(counts[key][value] < DIVERSITY_LIMITS[key] for key, value in values.items() if value)


def _add(candidate, selected, counts):
    selected.append(candidate)
    counts["category"][candidate.get("category")] += 1
    counts["conflict"][candidate.get("conflict")] += 1
    counts["title_style"][candidate.get("selected_title_style")] += 1


def select_diverse(candidates, limit=DAILY_PUBLISH_COUNT):
    """Choose winners with deliberate 80/20 exploration and hard diversity caps."""
    candidates = sorted(candidates, key=lambda x: x["final_score"], reverse=True)
    explore_target = round(limit * EXPLORATION_FRACTION)
    exploit_target = limit - explore_target
    selected, substitutions = [], 0
    counts = {key: Counter() for key in DIVERSITY_LIMITS}

    exploit = [x for x in candidates if x.get("selection_class", "exploit") != "explore"]
    explore = [x for x in candidates if x.get("selection_class") == "explore"]
    # Exploratory candidates are still strong; originality breaks ties.
    explore.sort(key=lambda x: (x.get("editorial_components", {}).get("originality", 0), x["final_score"]), reverse=True)

    for pool, target in ((exploit, exploit_target), (explore, explore_target)):
        added = 0
        for candidate in pool:
            if candidate in selected:
                continue
            if not _fits_diversity(candidate, counts):
                substitutions += 1
                continue
            # Do not allow another obvious near duplicate through just because it fits category caps.
            if any(similarity(candidate, prior) >= NEAR_DUPLICATE_THRESHOLD for prior in selected):
                substitutions += 1
                continue
            _add(candidate, selected, counts)
            added += 1
            if added >= target:
                break

    # Fill safely from any remaining strong candidate, never relaxing hard diversity caps.
    for candidate in candidates:
        if len(selected) >= limit:
            break
        if candidate in selected or not _fits_diversity(candidate, counts):
            continue
        if any(similarity(candidate, prior) >= NEAR_DUPLICATE_THRESHOLD for prior in selected):
            continue
        _add(candidate, selected, counts)

    return selected[:limit], substitutions


def hourly_slots(plan_date):
    if isinstance(plan_date, str):
        plan_date = date.fromisoformat(plan_date)
    tz = ZoneInfo(CANONICAL_TIMEZONE)
    slots = []
    for hour in range(24):
        local = datetime(plan_date.year, plan_date.month, plan_date.day, hour, 0, tzinfo=tz)
        utc = local.astimezone(timezone.utc)
        slots.append({
            "slot": hour,
            "local": local.isoformat(),
            "publish_at": utc.isoformat().replace("+00:00", "Z"),
            "timezone": CANONICAL_TIMEZONE,
        })
    return slots


def order_for_schedule(selected):
    """Avoid identical ending/title patterns in adjacent hours where practical."""
    remaining = sorted(selected, key=lambda x: x["final_score"], reverse=True)
    ordered = []
    while remaining:
        previous = ordered[-1] if ordered else None
        pick = next((x for x in remaining if not previous or (
            x.get("ending_style") != previous.get("ending_style") and
            x.get("selected_title_style") != previous.get("selected_title_style")
        )), remaining[0])
        ordered.append(pick)
        remaining.remove(pick)
    return ordered


def evaluate(raw_candidates, semifinalists, plan_date, analytics_video_count=0, recent=()):
    if len(raw_candidates) < RAW_CANDIDATE_COUNT:
        raise GrowthPlanError(f"raw candidate count {len(raw_candidates)} is below required {RAW_CANDIDATE_COUNT}")
    qualified, rejected = filter_candidates(raw_candidates, recent=recent)
    qualified_ids = {x["candidate_id"] for x in qualified}
    semifinalists = [x for x in semifinalists if x.get("candidate_id") in qualified_ids]
    if len(semifinalists) > SEMIFINALIST_TARGET:
        semifinalists = sorted(semifinalists, key=editorial_score, reverse=True)[:SEMIFINALIST_TARGET]
    weight = analytics_weight(analytics_video_count)
    scored, semifinal_rejected = [], []
    for candidate in semifinalists:
        try:
            scored.append(score_semifinalist(candidate, weight))
        except GrowthPlanError as exc:
            semifinal_rejected.append({"candidate_id": candidate.get("candidate_id"), "reason": str(exc)})
    selected, substitutions = select_diverse(scored)
    ordered = order_for_schedule(selected)
    slots = hourly_slots(plan_date)
    for candidate, slot in zip(ordered, slots):
        candidate["publication"] = slot
        candidate["selection_class"] = candidate.get("selection_class", "exploit")
    duplicate_rejections = sum("duplicate" in x["reason"] for x in rejected)
    return {
        "plan_date": str(plan_date),
        "raw_premises_generated": len(raw_candidates),
        "hard_rejected": len(rejected),
        "qualified": len(qualified),
        "semifinalists": len(semifinalists),
        "semifinal_rejected": semifinal_rejected,
        "final_selected": len(ordered),
        "exploit_selections": sum(x.get("selection_class") != "explore" for x in ordered),
        "explore_selections": sum(x.get("selection_class") == "explore" for x in ordered),
        "analytics_confidence": round(weight / MAX_ANALYTICS_WEIGHT, 4) if MAX_ANALYTICS_WEIGHT else 0,
        "analytics_weight": weight,
        "editorial_weight": round(1 - weight, 4),
        "duplicate_rejections": duplicate_rejections,
        "diversity_substitutions": substitutions,
        "rejected": [{"candidate_id": x["candidate"].get("candidate_id"), "reason": x["reason"]} for x in rejected],
        "selected": ordered,
    }


def _components(seed, weights, floor=70):
    return {key: min(100, floor + ((seed * (i + 3) * 7) % 27)) for i, key in enumerate(weights)}


def build_acceptance_fixture(plan_date):
    """Cheap deterministic acceptance data: 120 distinct premises, zero production side effects."""
    families = [
        "RELATIONSHIP", "DATING", "MARRIAGE", "BETRAYAL", "FAMILY", "INHERITANCE", "MONEY", "WORKPLACE",
        "REVENGE", "FRIENDSHIP", "WEDDING", "ENTITLED_PERSON", "NEIGHBOR", "SECRETS", "DISCOVERY",
        "SOCIAL_CONFLICT", "PROPERTY", "PARENTING", "MORAL_DILEMMA", "KINDNESS", "MISUNDERSTANDING",
        "HIDDEN_IDENTITY", "CONSEQUENCES", "TWIST", "WILDCARD",
    ]
    settings = ["at a family dinner", "during a deadline", "before a major purchase", "on a group trip", "at a celebration"]
    incidents = ["a receipt exposed a secret", "a message contradicted the story", "a contract changed overnight", "a camera revealed the truth", "a stranger returned something important"]
    payoffs = ["the evidence reversed the accusation", "the lie unraveled in front of everyone", "a boundary forced a fair outcome", "the person underestimated me and lost leverage", "an unexpected act of kindness changed the decision"]
    raw = []
    for idx in range(RAW_CANDIDATE_COUNT):
        family = families[idx % len(families)]
        variant = idx // len(families)
        conflict = f"{family}_CONFLICT_{variant + 1}"
        raw.append({
            "candidate_id": f"cand-{idx + 1:03d}",
            "premise": f"{family.title().replace('_', ' ')} drama {settings[variant]}: {incidents[(idx + variant) % len(incidents)]}, forcing a choice with real consequences.",
            "relationship_context": f"{family.lower()}-context-{variant + 1}",
            "category": family,
            "conflict": conflict,
            "likely_payoff": payoffs[(idx * 2 + variant) % len(payoffs)],
            "protagonist_role": ["EMPLOYEE", "PARTNER", "SIBLING", "TENANT", "FRIEND"][idx % 5],
            "antagonist_role": ["BOSS", "PARTNER", "RELATIVE", "LANDLORD", "COWORKER"][idx % 5],
            "ending_style": ["REVERSAL", "BACKFIRE", "REVEAL", "BOUNDARY_SET", "KINDNESS_RETURNED"][idx % 5],
            "can_sustain_target_duration": idx % 19 != 0,
            "editorial_components": _components(idx + 1, EDITORIAL_WEIGHTS, 62 if idx % 17 == 0 else 72),
        })
    qualified, _ = filter_candidates(raw)
    top = sorted(qualified, key=editorial_score, reverse=True)[:SEMIFINALIST_TARGET]
    styles = ["HIDDEN_REVELATION", "DISCOVERY", "NORMAL_TO_ABNORMAL", "DECISION_CONSEQUENCE", "COUNTDOWN"]
    semifinalists = []
    for idx, candidate in enumerate(top):
        c = dict(candidate)
        c["opening_line"] = f"I knew something was wrong when {incidents[(idx + 1) % len(incidents)]}, and nobody expected me to have proof."
        c["hook_components"] = _components(idx + 11, HOOK_WEIGHTS, 74)
        c["selection_class"] = "explore" if idx % 6 == 0 else "exploit"
        c["title_candidates"] = []
        for t, style in enumerate(styles):
            title = [
                f"I Thought Everything Was Fine… Then the Evidence Appeared #{idx + 1} #Shorts",
                f"I Checked One Detail and the Whole Story Fell Apart #{idx + 1} #Shorts",
                f"It Started Like a Normal Day… Until I Saw the Proof #{idx + 1} #Shorts",
                f"I Refused to Ignore the Evidence. Then Everything Changed #{idx + 1} #Shorts",
                f"Hours Before the Decision, I Learned the Truth #{idx + 1} #Shorts",
            ][t]
            c["title_candidates"].append({
                "title": title,
                "style": style,
                "truthful": True,
                "score_components": _components(idx + t + 31, TITLE_WEIGHTS, 74),
            })
        semifinalists.append(c)
    return raw, semifinalists


def print_summary(result):
    print(f"Raw premises generated: {result['raw_premises_generated']}")
    print(f"Hard rejected: {result['hard_rejected']}")
    print(f"Qualified: {result['qualified']}")
    print(f"Semifinalists: {result['semifinalists']}")
    print(f"Final selected: {result['final_selected']}")
    print(f"Exploit selections: {result['exploit_selections']}")
    print(f"Explore selections: {result['explore_selections']}")
    print(f"Analytics confidence: {result['analytics_confidence']:.2f}")
    print(f"Analytics weight: {result['analytics_weight'] * 100:.1f}%")
    print(f"Editorial weight: {result['editorial_weight'] * 100:.1f}%")
    print(f"Duplicate rejections: {result['duplicate_rejections']}")
    print(f"Diversity substitutions: {result['diversity_substitutions']}")
    for item in result["selected"]:
        pub = item["publication"]["local"]
        print(f"{item['candidate_id']} | {item['category']} | {item['selected_title']} | {item['final_score']:.2f} | {pub} | {item['selection_class']}")
        print(f"  opening: {item.get('opening_line', '')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--acceptance-dry-run", action="store_true")
    parser.add_argument("--date", default=str(date.today()))
    parser.add_argument("--analytics-video-count", type=int, default=0)
    parser.add_argument("--output")
    args = parser.parse_args()
    if not args.acceptance_dry_run:
        raise SystemExit("Only --acceptance-dry-run is a CLI action; production AI planning follows planner/DAILY_GROWTH_PROMPT.md")
    raw, semifinalists = build_acceptance_fixture(args.date)
    result = evaluate(raw, semifinalists, args.date, analytics_video_count=args.analytics_video_count)
    print_summary(result)
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["final_selected"] > DAILY_PUBLISH_COUNT:
        raise SystemExit("selected more than daily production limit")
    if len({x["publication"]["publish_at"] for x in result["selected"]}) != result["final_selected"]:
        raise SystemExit("duplicate publication slots")


if __name__ == "__main__":
    main()
