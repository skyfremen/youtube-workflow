"""Deterministic selection/validation engine for the Wacky Dramas planning funnel.

AI owns semantic creative work; this module owns auditable arithmetic, duplicate
checks, analytics confidence, diversity policy and hourly scheduling. Rejected
candidates never reach media/TTS/render/upload stages.
"""
import argparse
import json
import math
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from planning.planning_config import (
    ANALYTICS_CONFIDENCE_SCALE, CANONICAL_TIMEZONE, DAILY_PUBLISH_COUNT,
    DIVERSITY_LIMITS, EDITORIAL_WEIGHTS, EXPLORATION_FRACTION, HOOK_WEIGHTS,
    MAX_ANALYTICS_WEIGHT, MIN_FINAL_EDITORIAL_SCORE, MIN_HOOK_SCORE,
    MIN_TITLE_SCORE, NEAR_DUPLICATE_THRESHOLD,
    RAW_CANDIDATE_COUNT, SEMIFINALIST_TARGET, TITLE_WEIGHTS,
    TITLES_PER_SEMIFINALIST,
)

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "and", "the", "to", "of", "in", "on", "at", "for", "with",
    "my", "me", "i", "was", "is", "it", "that", "this", "then", "when",
    "had", "has", "have", "but", "after", "before", "from", "our", "their",
}


class PlanningError(ValueError):
    pass


def _bounded(value, name="score"):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise PlanningError(f"{name} must be numeric") from None
    if not 0 <= value <= 100:
        raise PlanningError(f"{name} must be between 0 and 100")
    return value


def weighted_score(components, weights):
    if not isinstance(components, dict):
        raise PlanningError("score components must be an object")
    missing = [key for key in weights if key not in components]
    if missing:
        raise PlanningError("missing score components: " + ", ".join(missing))
    total = sum(weights.values())
    return round(sum(_bounded(components[k], k) * weights[k] for k in weights) / total, 3)


def editorial_score(candidate):
    return weighted_score(candidate.get("editorial_components"), EDITORIAL_WEIGHTS)


def title_score(title):
    if title.get("truthful") is not True:
        return 0.0
    return weighted_score(title.get("score_components"), TITLE_WEIGHTS)


def hook_score(candidate):
    return weighted_score(candidate.get("hook_components"), HOOK_WEIGHTS)


def _tokens(value):
    return {x for x in TOKEN_RE.findall(str(value or "").lower()) if x not in STOPWORDS}


def candidate_fingerprint(candidate):
    fields = (
        candidate.get("premise"), candidate.get("conflict"), candidate.get("relationship_context"),
        candidate.get("likely_payoff"), candidate.get("ending_style"), candidate.get("opening_line"),
    )
    return _tokens(" ".join(str(x or "") for x in fields))


def similarity(a, b):
    """Deterministic similarity over story-bearing language plus controlled structure."""
    left, right = candidate_fingerprint(a), candidate_fingerprint(b)
    if not left or not right:
        return 0.0
    jaccard = len(left & right) / len(left | right)
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
    except PlanningError:
        return "malformed_editorial_score"
    if candidate.get("can_sustain_target_duration") is not True:
        return "cannot_sustain_target_duration"
    if not str(candidate.get("likely_payoff", "")).strip():
        return "missing_payoff"
    for other in [*accepted_today, *recent]:
        sim = similarity(candidate, other)
        if sim >= NEAR_DUPLICATE_THRESHOLD:
            return f"near_duplicate:{other.get('candidate_id') or other.get('content_id') or 'recent'}:{sim:.3f}"
    if score < 45:
        return "editorially_too_weak"
    return None


def filter_candidates(candidates, recent=()):
    accepted, rejected, seen = [], [], set()
    for candidate in candidates:
        cid = candidate.get("candidate_id")
        if cid in seen:
            rejected.append({"candidate": candidate, "reason": "duplicate_candidate_id"})
            continue
        seen.add(cid)
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
    weight = MAX_ANALYTICS_WEIGHT * (1.0 - math.exp(-count / ANALYTICS_CONFIDENCE_SCALE))
    return round(min(MAX_ANALYTICS_WEIGHT, weight), 4)


def normalized_performance_score(metrics):
    """Return the canonical normalized historical-attribute fit score."""
    if not isinstance(metrics, dict):
        return None
    value = metrics.get("historical_attribute_fit")
    return None if value is None else round(_bounded(value, "historical_attribute_fit"), 3)


def blend_scores(editorial, analytics, weight):
    editorial = _bounded(editorial, "editorial")
    weight = max(0.0, min(MAX_ANALYTICS_WEIGHT, float(weight or 0)))
    if analytics is None or weight == 0:
        return round(editorial, 3)
    return round(editorial * (1 - weight) + _bounded(analytics, "analytics") * weight, 3)


def select_best_title(candidate):
    titles = candidate.get("title_candidates") or []
    if len(titles) < TITLES_PER_SEMIFINALIST:
        raise PlanningError(f"{candidate.get('candidate_id')}: requires at least {TITLES_PER_SEMIFINALIST} title candidates")
    scored = [(title_score(title), title) for title in titles]
    score, best = max(scored, key=lambda x: x[0])
    if score < MIN_TITLE_SCORE:
        raise PlanningError(f"{candidate.get('candidate_id')}: no title clears minimum quality")
    return best, score


def score_semifinalist(candidate, analytics_w=0.0):
    editorial = editorial_score(candidate)
    title, title_value = select_best_title(candidate)
    hook_value = hook_score(candidate)
    if editorial < MIN_FINAL_EDITORIAL_SCORE:
        raise PlanningError("editorial_below_final_threshold")
    if hook_value < MIN_HOOK_SCORE:
        raise PlanningError("hook_below_final_threshold")
    analytics_value = normalized_performance_score(candidate.get("analytics_metrics"))
    blended = blend_scores(editorial, analytics_value, analytics_w)
    final = round((blended * 0.70) + (title_value * 0.18) + (hook_value * 0.12), 3)
    output = dict(candidate)
    output.update({
        "editorial_score": editorial, "analytics_score": analytics_value,
        "analytics_weight": analytics_w, "selected_title": title["title"],
        "selected_title_style": title["style"], "selected_title_score": title_value,
        "hook_score": hook_value, "final_score": final,
    })
    return output


def _fits_diversity(candidate, counts):
    values = {
        "category": candidate.get("category"), "conflict": candidate.get("conflict"),
        "title_style": candidate.get("selected_title_style"),
    }
    return all(counts[key][value] < DIVERSITY_LIMITS[key] for key, value in values.items() if value)


def _add(candidate, selected, counts):
    selected.append(candidate)
    counts["category"][candidate.get("category")] += 1
    counts["conflict"][candidate.get("conflict")] += 1
    counts["title_style"][candidate.get("selected_title_style")] += 1


def select_diverse(candidates, limit=DAILY_PUBLISH_COUNT):
    """Reserve exploration first so exploitation cannot consume all diversity capacity."""
    candidates = sorted(candidates, key=lambda x: x["final_score"], reverse=True)
    explore_target = round(limit * EXPLORATION_FRACTION)
    exploit_target = limit - explore_target
    selected, substitutions = [], 0
    counts = {key: Counter() for key in DIVERSITY_LIMITS}
    explore = [x for x in candidates if x.get("selection_class") == "explore"]
    exploit = [x for x in candidates if x.get("selection_class", "exploit") != "explore"]
    explore.sort(key=lambda x: (x.get("editorial_components", {}).get("originality", 0), x["final_score"]), reverse=True)

    def consume(pool, target):
        nonlocal substitutions
        added = 0
        for candidate in pool:
            if candidate in selected:
                continue
            if not _fits_diversity(candidate, counts):
                substitutions += 1
                continue
            if any(similarity(candidate, prior) >= NEAR_DUPLICATE_THRESHOLD for prior in selected):
                substitutions += 1
                continue
            _add(candidate, selected, counts)
            added += 1
            if added >= target:
                break

    consume(explore, explore_target)
    consume(exploit, exploit_target)
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
            "slot": hour, "local": local.isoformat(),
            "publish_at": utc.isoformat().replace("+00:00", "Z"), "timezone": CANONICAL_TIMEZONE,
        })
    return slots


def order_for_schedule(selected):
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
        raise PlanningError(f"raw candidate count {len(raw_candidates)} is below required {RAW_CANDIDATE_COUNT}")
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
        except PlanningError as exc:
            semifinal_rejected.append({"candidate_id": candidate.get("candidate_id"), "reason": str(exc)})
    selected, substitutions = select_diverse(scored)
    ordered = order_for_schedule(selected)
    slots = hourly_slots(plan_date)
    for candidate, slot in zip(ordered, slots):
        candidate["publication"] = slot
        candidate["selection_class"] = candidate.get("selection_class", "exploit")
    return {
        "plan_date": str(plan_date), "raw_premises_generated": len(raw_candidates),
        "hard_rejected": len(rejected), "qualified": len(qualified),
        "semifinalists": len(semifinalists), "semifinal_rejected": semifinal_rejected,
        "final_selected": len(ordered),
        "exploit_selections": sum(x.get("selection_class") != "explore" for x in ordered),
        "explore_selections": sum(x.get("selection_class") == "explore" for x in ordered),
        "analytics_confidence": round(weight / MAX_ANALYTICS_WEIGHT, 4) if MAX_ANALYTICS_WEIGHT else 0,
        "analytics_weight": weight, "editorial_weight": round(1 - weight, 4),
        "duplicate_rejections": sum("duplicate" in x["reason"] for x in rejected),
        "diversity_substitutions": substitutions,
        "rejected": [{"candidate_id": x["candidate"].get("candidate_id"), "reason": x["reason"]} for x in rejected],
        "selected": ordered,
    }


def _components(seed, weights, floor=70):
    return {key: min(100, floor + ((seed * (i + 3) * 7) % 27)) for i, key in enumerate(weights)}


def build_acceptance_fixture(plan_date):
    """Deterministic, non-production acceptance pool with 120 distinct idea spaces."""
    families = [
        "RELATIONSHIP", "DATING", "MARRIAGE", "BETRAYAL", "FAMILY", "INHERITANCE", "MONEY", "WORKPLACE",
        "REVENGE", "FRIENDSHIP", "WEDDING", "ENTITLED_PERSON", "NEIGHBOR", "SECRETS", "DISCOVERY",
        "SOCIAL_CONFLICT", "PROPERTY", "PARENTING", "MORAL_DILEMMA", "KINDNESS", "MISUNDERSTANDING",
        "HIDDEN_IDENTITY", "CONSEQUENCES", "TWIST", "WILDCARD",
    ]
    scenario_sets = [
        ("a cancelled deposit exposed a hidden account", "bank records forced repayment", "SECRET_ACCOUNT"),
        ("a calendar invite contradicted an alibi", "the meeting log revealed who lied", "FALSE_ALIBI"),
        ("a delivery photo showed the package at another door", "camera timestamps reversed the accusation", "DELIVERY_PROOF"),
        ("an unsigned contract appeared after the deadline", "version history proved the clause was added later", "CONTRACT_TAMPERING"),
        ("a child repeated a sentence nobody expected them to know", "the adults finally admitted the hidden arrangement", "ACCIDENTAL_REVEAL"),
        ("a repair invoice listed work that never happened", "the technician confirmed the charge was invented", "FAKE_INVOICE"),
        ("a group-chat screenshot reached the wrong person", "the full thread exposed the manipulation", "CHAT_LEAK"),
        ("an old key still opened a room I was told was empty", "what was stored inside explained months of strange behavior", "HIDDEN_ROOM"),
        ("a loyalty account showed trips I never took", "the booking history identified the secret companion", "TRAVEL_HISTORY"),
        ("a payroll correction removed money instead of adding it", "the audit trail showed who changed the hours", "PAYROLL_EDIT"),
        ("a wedding vendor called about a second ceremony", "the duplicate booking exposed a private plan", "DOUBLE_BOOKING"),
        ("a neighbor's complaint included a photo from inside my yard", "the metadata showed how it was taken", "PRIVACY_INTRUSION"),
        ("an inheritance spreadsheet had one beneficiary quietly removed", "the lawyer's archived copy restored the original intent", "WILL_EDIT"),
        ("a school notice named a parent who had never met the teacher", "the sign-in record uncovered the impersonation", "IMPERSONATION"),
        ("a refund arrived for something I never returned", "the receipt connected it to a larger deception", "REFUND_TRAIL"),
        ("a storage-unit bill arrived in my name", "opening the legitimate records uncovered the hidden debt", "HIDDEN_DEBT"),
        ("a restaurant reservation had a note about an anniversary", "the timestamp contradicted the story I was told", "RESERVATION_REVEAL"),
        ("an access badge logged an entry after someone claimed to be home", "security records settled the argument", "ACCESS_LOG"),
        ("a charity receipt used my address but another person's name", "the organizer explained who had been redirecting donations", "DONATION_MISUSE"),
        ("a landlord sent two tenants different versions of the same rule", "comparing the notices forced a fair reversal", "SELECTIVE_RULE"),
        ("a voice note accidentally captured the conversation after the call", "the unplanned recording exposed the real motive", "VOICE_NOTE"),
        ("a shared photo album uploaded a picture from the wrong location", "the location clue broke the cover story", "LOCATION_CLUE"),
        ("a customer complaint quoted words I never said", "the recorded support transcript cleared my name", "FALSE_COMPLAINT"),
        ("a package contained a handwritten thank-you meant for someone else", "following the order number uncovered an unexpected kindness", "MISDIRECTED_GIFT"),
    ]
    roles = ["EMPLOYEE", "PARTNER", "SIBLING", "TENANT", "FRIEND", "PARENT", "CUSTOMER", "NEIGHBOR"]
    opponents = ["BOSS", "PARTNER", "RELATIVE", "LANDLORD", "COWORKER", "EX_PARTNER", "VENDOR", "GUEST"]
    endings = ["REVERSAL", "BACKFIRE", "REVEAL", "BOUNDARY_SET", "KINDNESS_RETURNED", "JUSTICE", "RECONCILIATION", "CONSEQUENCE"]
    raw = []
    for idx in range(RAW_CANDIDATE_COUNT):
        family = families[idx % len(families)]
        incident, payoff, conflict_root = scenario_sets[idx % len(scenario_sets)]
        variant = idx // len(families) + 1
        raw.append({
            "candidate_id": f"cand-{idx + 1:03d}",
            "premise": f"{family.title().replace('_', ' ')} variant {variant}: {incident}; the narrator must decide whether to confront it before the situation escalates.",
            "relationship_context": f"{family.lower()}-variant-{variant}",
            "category": family, "conflict": f"{conflict_root}_{family}_{variant}",
            "likely_payoff": f"{payoff}; variant {variant} ends with a concrete consequence rather than a cliffhanger.",
            "protagonist_role": roles[idx % len(roles)], "antagonist_role": opponents[(idx * 3) % len(opponents)],
            "ending_style": endings[(idx * 5) % len(endings)],
            "can_sustain_target_duration": idx % 23 != 0,
            "editorial_components": _components(idx + 1, EDITORIAL_WEIGHTS, 72),
        })
    qualified, _ = filter_candidates(raw)
    top = sorted(qualified, key=editorial_score, reverse=True)[:SEMIFINALIST_TARGET]
    styles = [
        "HIDDEN_REVELATION", "DISCOVERY", "NORMAL_TO_ABNORMAL", "DECISION_CONSEQUENCE", "COUNTDOWN",
        "UNDERESTIMATED_NARRATOR", "MORAL_CONFLICT", "DELAYED_REVELATION", "CONTRADICTION", "CONSEQUENCE_FIRST",
    ]
    templates = {
        "HIDDEN_REVELATION": "They Said Nothing Was Hidden… Then I Found {clue} #{n} #Shorts",
        "DISCOVERY": "I Checked {clue} and the Story Stopped Making Sense #{n} #Shorts",
        "NORMAL_TO_ABNORMAL": "It Looked Completely Normal… Until {clue} Proved Otherwise #{n} #Shorts",
        "DECISION_CONSEQUENCE": "I Refused to Ignore {clue}. Then the Truth Came Out #{n} #Shorts",
        "COUNTDOWN": "Hours Before the Decision, {clue} Changed Everything #{n} #Shorts",
        "UNDERESTIMATED_NARRATOR": "They Thought I Had No Proof. They Forgot About {clue} #{n} #Shorts",
        "MORAL_CONFLICT": "Everyone Wanted Me to Stay Quiet. {clue} Made That Impossible #{n} #Shorts",
        "DELAYED_REVELATION": "I Believed the Explanation for Weeks… Then I Saw {clue} #{n} #Shorts",
        "CONTRADICTION": "They Told Me One Story. {clue} Told Me Another #{n} #Shorts",
        "CONSEQUENCE_FIRST": "The Argument Ended the Moment I Showed Them {clue} #{n} #Shorts",
    }
    semifinalists = []
    for idx, candidate in enumerate(top):
        c = dict(candidate)
        clue = candidate["conflict"].split("_")[0].lower().replace("-", " ")
        c["opening_line"] = f"The first thing that didn't fit was {candidate['premise'].split(': ', 1)[1].split(';', 1)[0]}."
        c["hook_components"] = _components(idx + 11, HOOK_WEIGHTS, 76)
        c["selection_class"] = "explore" if idx % 6 == 0 else "exploit"
        c["title_candidates"] = []
        for offset in range(TITLES_PER_SEMIFINALIST):
            style = styles[(idx + offset) % len(styles)]
            score_seed = idx + offset * 7 + 31
            c["title_candidates"].append({
                "title": templates[style].format(clue=clue.title(), n=idx + 1),
                "style": style, "truthful": True,
                "score_components": _components(score_seed, TITLE_WEIGHTS, 75),
            })
        semifinalists.append(c)
    return raw, semifinalists


def print_summary(result):
    for label, key in (
        ("Raw premises generated", "raw_premises_generated"), ("Hard rejected", "hard_rejected"),
        ("Qualified", "qualified"), ("Semifinalists", "semifinalists"), ("Final selected", "final_selected"),
        ("Exploit selections", "exploit_selections"), ("Explore selections", "explore_selections"),
    ):
        print(f"{label}: {result[key]}")
    print(f"Analytics confidence: {result['analytics_confidence']:.2f}")
    print(f"Analytics weight: {result['analytics_weight'] * 100:.1f}%")
    print(f"Editorial weight: {result['editorial_weight'] * 100:.1f}%")
    print(f"Duplicate rejections: {result['duplicate_rejections']}")
    print(f"Diversity substitutions: {result['diversity_substitutions']}")
    for item in result["selected"]:
        print(f"{item['candidate_id']} | {item['category']} | {item['selected_title']} | {item['final_score']:.2f} | {item['publication']['local']} | {item['selection_class']}")
        print(f"  opening: {item.get('opening_line', '')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--acceptance-dry-run", action="store_true")
    parser.add_argument("--date", default=str(date.today()))
    parser.add_argument("--analytics-video-count", type=int, default=0)
    parser.add_argument("--output")
    args = parser.parse_args()
    if not args.acceptance_dry_run:
        raise SystemExit("Only --acceptance-dry-run is a CLI action; production AI planning follows planner/DAILY_PLANNER_PROMPT.md")
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
