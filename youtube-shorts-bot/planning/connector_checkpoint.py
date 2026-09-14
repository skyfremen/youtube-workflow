"""Standalone connector-native deterministic planner checkpoint.

ChatGPT/Work fetches this exact file at ``rules_source_sha`` and supplies only the
frozen authored pool plus small connector evidence. The checkpoint intentionally
has no dependency on a Git checkout, the repository tree, the full media registry,
global media-readiness state, or replenishment state.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

CHECKPOINT_SCHEMA_VERSION = 2
POOL_SCHEMA_VERSION = 2
REQUEST_SCHEMA_VERSION = 7
EVIDENCE_SCHEMA_VERSION = 2
REPOSITORY = "skyfremen/youtube-workflow"
CANONICAL_TIMEZONE = "Asia/Singapore"
SGT = timezone(timedelta(hours=8))
CATCH_UP_MIN_LEAD_MINUTES = 30
CANONICAL_BACKGROUND_FALLBACK_CATEGORY = "satisfying_process"

CONTENT_ID_RE = re.compile(r"^wd-[A-Za-z0-9-]+$")
CANDIDATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
DAILY_POOL_ID_RE = re.compile(r"^dp-[A-Za-z0-9-]{8,96}$")
ADHOC_POOL_ID_RE = re.compile(r"^ap-[A-Za-z0-9-]{8,96}$")

TOP_LEVEL_KEYS = {
    "schema_version", "content_id", "channel", "story", "narration", "visual",
    "youtube", "publication", "planning",
}
CHANNEL_KEYS = {"name", "handle"}
STORY_KEYS = {
    "category", "story_type", "hook", "script", "card_emojis", "lead_gender",
    "story_tone", "punchline",
}
NARRATION_KEYS = {"engine", "voice", "speed"}
V7_VISUAL_KEYS = {
    "background_mode", "background_primary_sequence", "background_backup_sequence",
}
SEQUENCE_SEGMENT_KEYS = {
    "background_id", "segment_start_seconds", "segment_duration_seconds",
}
YOUTUBE_KEYS = {
    "title", "description", "hashtags", "tags", "category_id", "made_for_kids",
}
PUBLICATION_KEYS = {"mode", "timezone", "publish_at"}
PLANNING_KEYS = {
    "plan_date", "editorial_score", "editorial_components", "analytics_score",
    "analytics_weight", "final_score", "title_candidates", "selected_title_score",
    "hook_score", "selection_class", "selection_reason", "similarity", "attributes",
    "target_duration_seconds",
}
ATTRIBUTE_KEYS = {
    "subtype", "conflict", "primary_emotion", "protagonist_role", "antagonist_role",
    "opening_style", "title_style", "ending_style",
}
TITLE_CANDIDATE_KEYS = {"title", "style", "truthful", "score", "score_components"}
PLANNING_EXECUTION_KEYS = {
    "editorial_selection_owner", "planning_method", "rules_source_sha",
    "ranked_candidate_ids",
}
CANDIDATE_KEYS = {"rank", "candidate_id", "background_category", "request"}

EDITORIAL_WEIGHTS = {
    "opening_hook_potential": 20,
    "curiosity_gap": 20,
    "emotional_stakes": 15,
    "escalation_potential": 10,
    "payoff_quality": 10,
    "title_potential": 10,
    "broad_relatability": 5,
    "originality": 5,
    "narration_suitability": 5,
}
TITLE_WEIGHTS = {
    "curiosity_gap": 30,
    "emotional_impact": 20,
    "unanswered_question": 15,
    "immediate_comprehension": 10,
    "specificity": 10,
    "natural_phrasing": 5,
    "conciseness": 5,
    "truthful_reflection": 5,
}

CATEGORIES = {
    "RELATIONSHIP", "DATING", "MARRIAGE", "BETRAYAL", "FAMILY", "INHERITANCE",
    "MONEY", "WORKPLACE", "REVENGE", "FRIENDSHIP", "WEDDING", "ENTITLED_PERSON",
    "NEIGHBOR", "SECRETS", "DISCOVERY", "SOCIAL_CONFLICT", "PROPERTY", "PARENTING",
    "MORAL_DILEMMA", "KINDNESS", "MISUNDERSTANDING", "HIDDEN_IDENTITY", "CONSEQUENCES",
    "TWIST", "WILDCARD",
}
EMOTIONS = {
    "ANGER", "BETRAYAL", "INJUSTICE", "EMBARRASSMENT", "FEAR", "DISBELIEF", "REVENGE",
    "LOVE", "GUILT", "REGRET", "SURPRISE", "RELIEF", "HOPE", "SADNESS", "JOY",
}
OPENING_STYLES = {
    "IMMEDIATE_REVELATION", "CONTRADICTION", "DISCOVERY", "CONSEQUENCE_FIRST",
    "URGENT_CONFLICT", "SHOCKING_STATEMENT", "UNANSWERED_EVENT", "DECISION_FIRST",
}
TITLE_STYLES = {
    "HIDDEN_REVELATION", "DISCOVERY", "NORMAL_TO_ABNORMAL", "DECISION_CONSEQUENCE",
    "COUNTDOWN", "UNDERESTIMATED_NARRATOR", "MORAL_CONFLICT", "DELAYED_REVELATION",
    "CONTRADICTION", "CONSEQUENCE_FIRST",
}
ENDING_STYLES = {
    "REVERSAL", "BACKFIRE", "REVEAL", "CONSEQUENCE", "RECONCILIATION", "BOUNDARY_SET",
    "JUSTICE", "SACRIFICE", "KINDNESS_RETURNED", "BITTERSWEET", "OPEN_RESOLUTION",
}
PROTAGONIST_ROLES = {
    "PARTNER", "SPOUSE", "EMPLOYEE", "MANAGER", "SIBLING", "PARENT", "ADULT_CHILD",
    "FRIEND", "ROOMMATE", "NEIGHBOR", "TENANT", "LANDLORD", "CUSTOMER", "OWNER",
    "BRIDE", "GROOM", "STUDENT", "TEACHER", "TRAVELER", "STRANGER", "RELATIVE",
}
ANTAGONIST_ROLES = PROTAGONIST_ROLES | {"COWORKER", "BOSS", "EX_PARTNER", "VENDOR", "GUEST"}
LEAD_GENDERS = {"female", "male"}
NATURAL_TONES = {"natural", "general", "conversational", "warm", "calm"}
EXPRESSIVE_TONES = {"comedy", "dramatic", "sarcastic", "dramatic_comedy", "absurd", "expressive"}
STORY_TONES = NATURAL_TONES | EXPRESSIVE_TONES
APPROVED_VOICES = {"af_heart", "af_bella", "am_echo", "am_fenrir"}

PUNCHLINE_TYPES = {
    "REVEAL", "REVERSAL", "BACKFIRE", "COMEBACK", "CONSEQUENCE", "CONTRADICTION", "ABSURDITY",
}
PUNCHLINE_REQUIRED_KEYS = {"text", "emphasis_text"}
PUNCHLINE_OPTIONAL_KEYS = {"type"}
MAX_EMPHASIS_WORDS = 5
_APOSTROPHES = str.maketrans({
    "’": "'", "‘": "'", "`": "'", "´": "'", "“": '"', "”": '"',
})
_TOKEN_RE = re.compile(r"[0-9A-Za-z]+(?:'[0-9A-Za-z]+)*")

BACKGROUND_MODE = "concatenated_fit_to_short"
BACKGROUND_CATEGORIES = {
    "cooking", "baking", "food_prep", "satisfying_process", "crafting", "cleaning",
    "assembly", "pov_movement", "city_motion", "licensed_gameplay",
}
MIN_SEQUENCE_CLIP_SECONDS = 60.0
MIN_SEQUENCE_CLIPS = 2
MAX_SEQUENCE_CLIPS = 3
PREFERRED_SEQUENCE_CLIPS = 3
MIN_SEQUENCE_SOURCE_SECONDS = 210.0
PREFERRED_SEQUENCE_SOURCE_SECONDS = 240.0
MAX_SEQUENCE_SOURCE_SECONDS = 300.0
DURATION_EPSILON_SECONDS = 0.05

PROFILE = {
    "adhoc": {
        "pool_type": "adhoc",
        "planning_modes": {"manual_on_demand"},
        "date_field": "singapore_date",
        "fixed_target_count": 1,
        "normal_target_count": None,
        "candidate_count_policy": "fixed_one",
        "has_publication_slots": False,
        "publication": {"mode": "immediate", "timezone": CANONICAL_TIMEZONE, "publish_at": None},
    },
    "daily": {
        "pool_type": "daily",
        "planning_modes": {"normal_next_day", "same_day_catch_up"},
        "date_field": "plan_date",
        "fixed_target_count": None,
        "normal_target_count": 24,
        "candidate_count_policy": "target_count",
        "has_publication_slots": True,
        "publication": {"mode": "scheduled", "timezone": CANONICAL_TIMEZONE, "publish_at": None},
    },
}


def _nonempty(value):
    return bool(str(value or "").strip())


def _number(value, label, errors, *, minimum=None, maximum=None, nullable=False):
    if value is None and nullable:
        return None
    if isinstance(value, bool):
        errors.append(f"{label} must be numeric" + (" or null" if nullable else ""))
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be numeric" + (" or null" if nullable else ""))
        return None
    if not math.isfinite(number):
        errors.append(f"{label} must be finite")
        return None
    if minimum is not None and number < minimum:
        errors.append(f"{label} must be >= {minimum:g}")
    if maximum is not None and number > maximum:
        errors.append(f"{label} must be <= {maximum:g}")
    return number


def _score(value, label, errors, *, allow_none=False):
    if value is None and allow_none:
        return
    _number(value, label, errors, minimum=0, maximum=100)


def _component_scores(value, expected, label, errors):
    if not isinstance(value, dict) or set(value) != set(expected):
        errors.append(f"{label} must contain exactly the configured score components")
        return
    for key in expected:
        _score(value.get(key), f"{label}.{key}", errors)


def _semantic_tokens(value):
    text = unicodedata.normalize("NFKC", str(value or "")).translate(_APOSTROPHES)
    return [match.group(0).casefold() for match in _TOKEN_RE.finditer(text)]


def _matches(haystack, needle):
    if not needle or len(needle) > len(haystack):
        return []
    width = len(needle)
    return [i for i in range(len(haystack) - width + 1) if haystack[i:i + width] == needle]


def _validate_punchline(script, punchline):
    errors = []
    if not isinstance(punchline, dict):
        return ["story.punchline must be an object"]
    allowed = PUNCHLINE_REQUIRED_KEYS | PUNCHLINE_OPTIONAL_KEYS
    missing = PUNCHLINE_REQUIRED_KEYS - set(punchline)
    extra = set(punchline) - allowed
    if missing:
        errors.append("story.punchline missing fields: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("story.punchline unexpected fields: " + ", ".join(sorted(extra)))
    text = str(punchline.get("text") or "").strip()
    emphasis = str(punchline.get("emphasis_text") or "").strip()
    if not text:
        errors.append("story.punchline.text must be non-empty")
    if not emphasis:
        errors.append("story.punchline.emphasis_text must be non-empty")
    kind = punchline.get("type")
    if kind is not None and kind not in PUNCHLINE_TYPES:
        errors.append("story.punchline.type is not a controlled semantic type")
    script_words = _semantic_tokens(script)
    punch_words = _semantic_tokens(text)
    emphasis_words = _semantic_tokens(emphasis)
    if emphasis_words and len(emphasis_words) > MAX_EMPHASIS_WORDS:
        errors.append(f"story.punchline.emphasis_text must be at most {MAX_EMPHASIS_WORDS} words")
    if script_words and punch_words:
        locs = _matches(script_words, punch_words)
        if punch_words == script_words:
            errors.append("story.punchline.text must not be the entire story script")
        if not locs:
            errors.append("story.punchline.text must occur in story.script after normalization")
        elif len(locs) > 1:
            errors.append("story.punchline.text must identify one unambiguous span in story.script")
    if punch_words and emphasis_words:
        locs = _matches(punch_words, emphasis_words)
        if not locs:
            errors.append("story.punchline.emphasis_text must occur inside story.punchline.text")
        elif len(locs) > 1:
            errors.append("story.punchline.emphasis_text must identify one unambiguous span inside story.punchline.text")
    return errors


def _expected_voice(gender, tone):
    if gender not in LEAD_GENDERS or tone not in STORY_TONES:
        return None
    expressive = tone in EXPRESSIVE_TONES
    if gender == "female":
        return "af_bella" if expressive else "af_heart"
    return "am_fenrir" if expressive else "am_echo"


def _parse_date(raw, label, errors):
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        errors.append(f"{label} must be YYYY-MM-DD")
        return None


def _validate_publication(publication, expected, errors):
    if publication != expected:
        errors.append("publication must exactly equal the profile's canonical template")


def _validate_planning(planning, youtube_title, errors):
    if not isinstance(planning, dict):
        errors.append("planning must be an object")
        return
    missing = PLANNING_KEYS - set(planning)
    extra = set(planning) - PLANNING_KEYS
    if missing:
        errors.append("planning missing fields: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("planning unexpected fields: " + ", ".join(sorted(extra)))
    for key in ("editorial_score", "final_score", "selected_title_score", "hook_score"):
        _score(planning.get(key), f"planning.{key}", errors)
    _score(planning.get("analytics_score"), "planning.analytics_score", errors, allow_none=True)
    _component_scores(planning.get("editorial_components"), EDITORIAL_WEIGHTS, "planning.editorial_components", errors)
    _number(planning.get("analytics_weight"), "planning.analytics_weight", errors, minimum=0, maximum=0.75)
    if planning.get("selection_class") not in {"exploit", "explore"}:
        errors.append("planning.selection_class must be exploit or explore")
    if not _nonempty(planning.get("selection_reason")):
        errors.append("planning.selection_reason must be non-empty")
    similarity = planning.get("similarity")
    if not isinstance(similarity, dict) or "max_recent_similarity" not in similarity:
        errors.append("planning.similarity must record max_recent_similarity")
    else:
        _number(similarity.get("max_recent_similarity"), "planning.similarity.max_recent_similarity", errors, minimum=0, maximum=1)
    _number(planning.get("target_duration_seconds"), "planning.target_duration_seconds", errors, minimum=120, maximum=175)

    attrs = planning.get("attributes")
    if not isinstance(attrs, dict) or set(attrs) != ATTRIBUTE_KEYS:
        errors.append("planning.attributes must contain the controlled attribute fields")
    else:
        if not _nonempty(attrs.get("subtype")) or not _nonempty(attrs.get("conflict")):
            errors.append("planning subtype/conflict must be non-empty")
        checks = (
            ("primary_emotion", EMOTIONS),
            ("protagonist_role", PROTAGONIST_ROLES),
            ("antagonist_role", ANTAGONIST_ROLES),
            ("opening_style", OPENING_STYLES),
            ("title_style", TITLE_STYLES),
            ("ending_style", ENDING_STYLES),
        )
        for field, allowed in checks:
            if attrs.get(field) not in allowed:
                errors.append(f"planning.attributes.{field} is not a controlled value")

    titles = planning.get("title_candidates")
    if not isinstance(titles, list) or len(titles) != 5:
        errors.append("planning.title_candidates must contain exactly 5 candidates")
    else:
        selected_seen = False
        styles = set()
        for index, item in enumerate(titles):
            label = f"planning.title_candidates[{index}]"
            if not isinstance(item, dict) or set(item) != TITLE_CANDIDATE_KEYS:
                errors.append(f"{label} has invalid fields")
                continue
            if item.get("truthful") is not True:
                errors.append(f"{label} must be truthful")
            style = item.get("style")
            if style not in TITLE_STYLES:
                errors.append(f"{label}.style is not controlled")
            else:
                styles.add(style)
            _score(item.get("score"), f"{label}.score", errors)
            _component_scores(item.get("score_components"), TITLE_WEIGHTS, f"{label}.score_components", errors)
            if item.get("title") == youtube_title:
                selected_seen = True
        if len(styles) < 3:
            errors.append("planning.title_candidates must use at least 3 title styles")
        if not selected_seen:
            errors.append("youtube.title must exactly match one planning.title_candidates entry")


def _background_evidence(evidence):
    value = evidence.get("selected_backgrounds") if isinstance(evidence, dict) else None
    return value if isinstance(value, dict) else {}


def _validate_evidence_asset(asset_id, asset, errors):
    label = f"evidence.selected_backgrounds.{asset_id}"
    if not isinstance(asset, dict):
        errors.append(f"{label} must be an object")
        return
    required_true = (
        "eligible", "registered", "selectable", "verified", "commercial_use",
        "visual_review_verified", "production_rendition",
    )
    for field in required_true:
        if asset.get(field) is not True:
            errors.append(f"{label}.{field} must be true")
    if asset.get("status") != "active":
        errors.append(f"{label}.status must be active")
    if asset.get("has_watermark") is not False:
        errors.append(f"{label}.has_watermark must be false")
    if asset.get("has_embedded_text") is not False:
        errors.append(f"{label}.has_embedded_text must be false")
    if asset.get("category") not in BACKGROUND_CATEGORIES:
        errors.append(f"{label}.category must be a controlled background category")
    if not _nonempty(asset.get("source_blob_sha")):
        errors.append(f"{label}.source_blob_sha is required")
    _number(asset.get("duration_seconds"), f"{label}.duration_seconds", errors, minimum=MIN_SEQUENCE_CLIP_SECONDS)


def _validate_sequence(sequence, label, evidence, expected_category, errors):
    if not isinstance(sequence, list):
        errors.append(f"{label} must be a list")
        return []
    if not MIN_SEQUENCE_CLIPS <= len(sequence) <= MAX_SEQUENCE_CLIPS:
        errors.append(f"{label} must contain {MIN_SEQUENCE_CLIPS}-{MAX_SEQUENCE_CLIPS} segments")
    ids = []
    total = 0.0
    bg = _background_evidence(evidence)
    for index, item in enumerate(sequence):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict) or set(item) != SEQUENCE_SEGMENT_KEYS:
            errors.append(f"{item_label} must contain exactly background_id, segment_start_seconds, segment_duration_seconds")
            continue
        asset_id = item.get("background_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            errors.append(f"{item_label}.background_id must be non-empty")
            continue
        ids.append(asset_id)
        start = _number(item.get("segment_start_seconds"), f"{item_label}.segment_start_seconds", errors, minimum=0, maximum=86400)
        duration = _number(item.get("segment_duration_seconds"), f"{item_label}.segment_duration_seconds", errors, minimum=MIN_SEQUENCE_CLIP_SECONDS)
        if duration is not None:
            total += duration
        asset = bg.get(asset_id)
        if not isinstance(asset, dict):
            errors.append(f"{item_label} lacks connector evidence for background {asset_id}")
            continue
        if asset.get("category") != expected_category:
            errors.append(
                f"{item_label} background category {asset.get('category')!r} must equal "
                f"candidate.background_category {expected_category!r}"
            )
        source_duration = _number(asset.get("duration_seconds"), f"evidence.selected_backgrounds.{asset_id}.duration_seconds", errors, minimum=MIN_SEQUENCE_CLIP_SECONDS)
        if start is not None and duration is not None and source_duration is not None:
            if start + duration > source_duration + DURATION_EPSILON_SECONDS:
                errors.append(f"{item_label} selected range exceeds background {asset_id} source duration")
    if len(ids) != len(set(ids)):
        errors.append(f"{label} must not repeat a background_id")
    if sequence and not (MIN_SEQUENCE_SOURCE_SECONDS - DURATION_EPSILON_SECONDS <= total <= MAX_SEQUENCE_SOURCE_SECONDS + DURATION_EPSILON_SECONDS):
        errors.append(f"{label} total source duration must be {MIN_SEQUENCE_SOURCE_SECONDS:g}-{MAX_SEQUENCE_SOURCE_SECONDS:g}s")
    return ids


def _validate_request(request, profile_name, background_category, evidence):
    errors = []
    if not isinstance(request, dict):
        return ["request root must be an object"]
    if set(request) != TOP_LEVEL_KEYS:
        missing = TOP_LEVEL_KEYS - set(request)
        extra = set(request) - TOP_LEVEL_KEYS
        if missing:
            errors.append("request missing fields: " + ", ".join(sorted(missing)))
        if extra:
            errors.append("request unexpected fields: " + ", ".join(sorted(extra)))
    if request.get("schema_version") != REQUEST_SCHEMA_VERSION:
        errors.append(f"new production request must use schema-v{REQUEST_SCHEMA_VERSION}")
    content_id = request.get("content_id")
    if not isinstance(content_id, str) or not CONTENT_ID_RE.fullmatch(content_id):
        errors.append(f"content_id must match {CONTENT_ID_RE.pattern}")
    if profile_name == "adhoc" and isinstance(content_id, str) and "-adhoc-" not in content_id.lower():
        errors.append("Ad-hoc content_id must contain -adhoc-")

    channel = request.get("channel")
    if not isinstance(channel, dict) or set(channel) != CHANNEL_KEYS:
        errors.append("channel must contain exactly name and handle")
    else:
        if channel.get("name") != "Wacky Dramas":
            errors.append("channel.name must be Wacky Dramas")
        if channel.get("handle") != "@WACKYDRAMAS":
            errors.append("channel.handle must be @WACKYDRAMAS")

    story = request.get("story")
    if not isinstance(story, dict):
        errors.append("story must be an object")
    else:
        missing = STORY_KEYS - set(story)
        extra = set(story) - STORY_KEYS
        if missing:
            errors.append("story missing fields: " + ", ".join(sorted(missing)))
        if extra:
            errors.append("story unexpected fields: " + ", ".join(sorted(extra)))
        for key in ("category", "story_type", "hook", "script"):
            if not _nonempty(story.get(key)):
                errors.append(f"story.{key} must be non-empty")
        if story.get("category") not in CATEGORIES:
            errors.append("story.category is not controlled")
        hook = str(story.get("hook") or "").strip()
        script = str(story.get("script") or "").strip()
        if hook and script.startswith(hook):
            errors.append("story.script must not repeat story.hook at the beginning")
        emojis = story.get("card_emojis")
        if not isinstance(emojis, list) or not 4 <= len(emojis) <= 6 or any(not _nonempty(x) for x in (emojis or [])):
            errors.append("story.card_emojis must contain 4-6 non-empty emojis")
        if story.get("lead_gender") not in LEAD_GENDERS:
            errors.append("story.lead_gender must be female or male")
        if story.get("story_tone") not in STORY_TONES:
            errors.append("story.story_tone is not controlled")
        errors.extend(_validate_punchline(script, story.get("punchline")))

    narration = request.get("narration")
    if not isinstance(narration, dict) or set(narration) != NARRATION_KEYS:
        errors.append("narration must contain exactly engine, voice, speed")
    else:
        if narration.get("engine") != "kokoro":
            errors.append("narration.engine must be kokoro")
        voice = narration.get("voice")
        if voice not in APPROVED_VOICES:
            errors.append("narration.voice is not approved")
        elif isinstance(story, dict):
            expected = _expected_voice(story.get("lead_gender"), story.get("story_tone"))
            if expected and voice != expected:
                errors.append(f"narration.voice must be {expected} for lead gender/tone")
        speed = _number(narration.get("speed"), "narration.speed", errors)
        if speed is not None and abs(speed - 1.75) > 0.001:
            errors.append("narration.speed must be 1.75")

    visual = request.get("visual")
    if background_category not in BACKGROUND_CATEGORIES:
        errors.append("candidate.background_category must be a controlled background category")
    if not isinstance(visual, dict) or set(visual) != V7_VISUAL_KEYS:
        errors.append("visual must contain exactly background_mode, background_primary_sequence, background_backup_sequence")
    else:
        if visual.get("background_mode") != BACKGROUND_MODE:
            errors.append(f"visual.background_mode must be {BACKGROUND_MODE}")
        pids = _validate_sequence(
            visual.get("background_primary_sequence"),
            "visual.background_primary_sequence",
            evidence,
            background_category,
            errors,
        )
        bids = _validate_sequence(
            visual.get("background_backup_sequence"),
            "visual.background_backup_sequence",
            evidence,
            background_category,
            errors,
        )
        overlap = sorted(set(pids) & set(bids))
        if overlap:
            errors.append("primary and backup background sequences must be disjoint; overlap=" + ", ".join(overlap))

    youtube = request.get("youtube")
    youtube_title = ""
    if not isinstance(youtube, dict) or set(youtube) != YOUTUBE_KEYS:
        errors.append("youtube must contain the canonical fields")
    else:
        youtube_title = str(youtube.get("title") or "").strip()
        if not youtube_title or len(youtube_title) > 100 or "#Shorts" not in youtube_title:
            errors.append("youtube.title must be non-empty, <=100 chars, and contain #Shorts")
        if not _nonempty(youtube.get("description")):
            errors.append("youtube.description must be non-empty")
        hashtags = youtube.get("hashtags")
        if not isinstance(hashtags, list) or not 3 <= len(hashtags) <= 8 or any(not str(x).strip().startswith("#") for x in (hashtags or [])):
            errors.append("youtube.hashtags must contain 3-8 # entries")
        tags = youtube.get("tags")
        if not isinstance(tags, list) or not 4 <= len(tags) <= 12:
            errors.append("youtube.tags must contain 4-12 semantic tags")
        elif any(not _nonempty(x) or str(x).strip().startswith("#") for x in tags):
            errors.append("youtube.tags must be non-empty backend keywords without #")
        elif len({str(x).strip().lower() for x in tags}) != len(tags):
            errors.append("youtube.tags must not contain case-insensitive duplicates")
        if not _nonempty(youtube.get("category_id")):
            errors.append("youtube.category_id must be non-empty")
        if youtube.get("made_for_kids") is not False:
            errors.append("youtube.made_for_kids must be false")

    _validate_publication(request.get("publication"), PROFILE[profile_name]["publication"], errors)
    _validate_planning(request.get("planning"), youtube_title, errors)
    return list(dict.fromkeys(errors))


def _validate_evidence(evidence, rules_source_sha):
    errors = []
    if not isinstance(evidence, dict):
        return ["connector evidence must be an object"]
    if evidence.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        errors.append(f"evidence.schema_version must be {EVIDENCE_SCHEMA_VERSION}")
    if evidence.get("repository") != REPOSITORY:
        errors.append(f"evidence.repository must be {REPOSITORY}")
    if evidence.get("rules_source_sha") != rules_source_sha:
        errors.append("evidence.rules_source_sha must equal validator rules_source_sha")
    if not _nonempty(evidence.get("checkpoint_blob_sha")):
        errors.append("evidence.checkpoint_blob_sha must contain connector-returned blob identity")
    drift = evidence.get("drift")
    if not isinstance(drift, dict) or drift.get("status") != "PASS" or drift.get("current_main_sha") != rules_source_sha:
        errors.append("evidence.drift must PASS and current_main_sha must equal rules_source_sha at checkpoint time")
    uniqueness = evidence.get("uniqueness")
    if not isinstance(uniqueness, dict) or uniqueness.get("status") != "PASS":
        errors.append("evidence.uniqueness.status must be PASS")
    selected = evidence.get("selected_backgrounds")
    if not isinstance(selected, dict):
        errors.append("evidence.selected_backgrounds must be an object")
    else:
        for asset_id, item in selected.items():
            if not isinstance(asset_id, str) or not asset_id:
                errors.append("evidence.selected_backgrounds keys must be non-empty strings")
                continue
            _validate_evidence_asset(asset_id, item, errors)
    if "media_readiness" in evidence:
        errors.append("evidence.media_readiness is obsolete for current planning; provide selected-background evidence only")
    if "replenishment" in evidence:
        errors.append("evidence.replenishment is obsolete for current planning")
    return errors


def _parse_slot(raw, plan_date, errors):
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"invalid publication slot {raw!r}")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        errors.append("daily publication slots must be UTC timestamps")
        return None
    local = parsed.astimezone(SGT)
    if local.date().isoformat() != plan_date:
        errors.append("daily publication slot must fall on plan_date in Asia/Singapore")
    if any((local.minute, local.second, local.microsecond)):
        errors.append("daily publication slots must be exact top-of-hour timestamps")
    return parsed


def _normal_slots(plan_date):
    local_midnight = datetime.fromisoformat(plan_date).replace(tzinfo=SGT)
    return [
        local_midnight.replace(hour=hour).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        for hour in range(24)
    ]


def _expected_count(profile_name, target):
    return 1 if profile_name == "adhoc" else target if isinstance(target, int) and not isinstance(target, bool) else 0


def validate_pool(profile_name, pool, rules_source_sha, evidence, raw_bytes=b"", now_utc=None):
    profile = PROFILE[profile_name]
    pool_errors = []
    pool_errors.extend(_validate_evidence(evidence, rules_source_sha))
    if not isinstance(pool, dict):
        pool_errors.append("planning pool root must be an object")
        return _result(profile_name, pool, rules_source_sha, raw_bytes, pool_errors, [], 0)

    expected_keys = {
        "schema_version", "pool_type", "pool_id", "planning_mode", "target_count",
        "planning_execution", "ranked_candidates", profile["date_field"],
    }
    if profile["has_publication_slots"]:
        expected_keys.add("publication_slots")
    missing = expected_keys - set(pool)
    extra = set(pool) - expected_keys
    if missing:
        pool_errors.append("planning pool missing fields: " + ", ".join(sorted(missing)))
    if extra:
        pool_errors.append("planning pool unexpected fields: " + ", ".join(sorted(extra)))
    if pool.get("schema_version") != POOL_SCHEMA_VERSION:
        pool_errors.append(f"planning pool schema_version must be {POOL_SCHEMA_VERSION}")
    if pool.get("pool_type") != profile["pool_type"]:
        pool_errors.append(f"pool_type must be {profile['pool_type']}")
    date_value = str(pool.get(profile["date_field"], ""))
    _parse_date(date_value, profile["date_field"], pool_errors)
    pool_id = pool.get("pool_id")
    pool_re = ADHOC_POOL_ID_RE if profile_name == "adhoc" else DAILY_POOL_ID_RE
    if not isinstance(pool_id, str) or not pool_re.fullmatch(pool_id):
        pool_errors.append(f"pool_id must match {pool_re.pattern}")
    mode = pool.get("planning_mode")
    if mode not in profile["planning_modes"]:
        pool_errors.append(f"planning_mode must be one of {sorted(profile['planning_modes'])}")
    target = pool.get("target_count")
    if profile["fixed_target_count"] is not None:
        if target != profile["fixed_target_count"]:
            pool_errors.append(f"target_count must be {profile['fixed_target_count']}")
    else:
        if isinstance(target, bool) or not isinstance(target, int) or not 1 <= target <= 24:
            pool_errors.append("Daily target_count must be 1-24")
        elif mode == "normal_next_day" and target != profile["normal_target_count"]:
            pool_errors.append(f"normal_next_day target_count must be {profile['normal_target_count']}")

    if profile_name == "daily":
        slots = pool.get("publication_slots")
        if not isinstance(slots, list) or not isinstance(target, int) or isinstance(target, bool) or len(slots) != target or len(slots) != len(set(slots)):
            pool_errors.append("publication_slots must contain exactly target_count unique slots")
        else:
            parsed = [_parse_slot(raw, date_value, pool_errors) for raw in slots]
            if all(item is not None for item in parsed):
                if parsed != sorted(parsed):
                    pool_errors.append("publication_slots must be chronological")
                if mode == "normal_next_day" and slots != _normal_slots(date_value):
                    pool_errors.append("normal_next_day publication_slots must be canonical 24 hourly slots")
                if mode == "same_day_catch_up":
                    current = now_utc or datetime.now(timezone.utc)
                    if current.tzinfo is None:
                        current = current.replace(tzinfo=timezone.utc)
                    threshold = current.astimezone(timezone.utc) + timedelta(minutes=CATCH_UP_MIN_LEAD_MINUTES)
                    if any(item < threshold for item in parsed):
                        pool_errors.append(f"same_day_catch_up slots must be >= {CATCH_UP_MIN_LEAD_MINUTES} minutes in future")

    expected = _expected_count(profile_name, target)
    candidates = pool.get("ranked_candidates")
    candidate_results = []
    candidate_ids = []
    content_ids = []
    if not isinstance(candidates, list) or len(candidates) != expected:
        pool_errors.append(f"ranked_candidates must contain exactly {expected} candidates")
        candidates = []
    for index, item in enumerate(candidates, start=1):
        item_errors = []
        if not isinstance(item, dict) or set(item) != CANDIDATE_KEYS:
            item_errors.append("candidate must contain exactly rank, candidate_id, background_category, request")
            candidate_id = None
            request = None
            background_category = None
        else:
            candidate_id = item.get("candidate_id")
            request = item.get("request")
            background_category = item.get("background_category")
            if item.get("rank") != index:
                item_errors.append("candidate rank must equal frozen list position")
            if not isinstance(candidate_id, str) or not CANDIDATE_ID_RE.fullmatch(candidate_id):
                item_errors.append("invalid candidate_id")
            else:
                candidate_ids.append(candidate_id)
            if background_category not in BACKGROUND_CATEGORIES:
                item_errors.append("invalid background_category")
            if not isinstance(request, dict):
                item_errors.append("request must be an object")
            else:
                cid = request.get("content_id")
                if isinstance(cid, str):
                    content_ids.append(cid)
                item_errors.extend(_validate_request(request, profile_name, background_category, evidence))
        candidate_results.append({
            "rank": index,
            "candidate_id": candidate_id,
            "content_id": request.get("content_id") if isinstance(request, dict) else None,
            "status": "PASS" if not item_errors else "FAIL",
            "errors": list(dict.fromkeys(item_errors)),
        })
    if len(candidate_ids) != len(set(candidate_ids)):
        pool_errors.append("candidate IDs must be unique")
    if len(content_ids) != len(set(content_ids)):
        pool_errors.append("candidate request content IDs must be unique")

    execution = pool.get("planning_execution")
    if not isinstance(execution, dict) or set(execution) != PLANNING_EXECUTION_KEYS:
        pool_errors.append("planning_execution must contain canonical ChatGPT provenance")
    else:
        if execution.get("editorial_selection_owner") != "chatgpt":
            pool_errors.append("planning_execution.editorial_selection_owner must be chatgpt")
        if execution.get("planning_method") != "chatgpt_ranked_pool":
            pool_errors.append("planning_execution.planning_method must be chatgpt_ranked_pool")
        if execution.get("rules_source_sha") != rules_source_sha:
            pool_errors.append("planning_execution.rules_source_sha must equal rules_source_sha")
        if execution.get("ranked_candidate_ids") != candidate_ids:
            pool_errors.append("planning_execution.ranked_candidate_ids must exactly match frozen candidate order")
    if not HEX40_RE.fullmatch(str(rules_source_sha or "")):
        pool_errors.append("rules_source_sha must be lowercase 40-character SHA")

    return _result(profile_name, pool, rules_source_sha, raw_bytes, pool_errors, candidate_results, expected)


def _result(profile_name, pool, rules_source_sha, raw_bytes, pool_errors, candidate_results, expected):
    valid = sum(item.get("status") == "PASS" for item in candidate_results)
    status = "PASS" if not pool_errors and len(candidate_results) == expected and valid == expected else "FAIL"
    date_field = PROFILE[profile_name]["date_field"]
    return {
        "status": status,
        "commit_allowed": status == "PASS",
        "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
        "profile": profile_name,
        "pool_id": pool.get("pool_id") if isinstance(pool, dict) else None,
        date_field: pool.get(date_field) if isinstance(pool, dict) else None,
        "planning_mode": pool.get("planning_mode") if isinstance(pool, dict) else None,
        "target_count": pool.get("target_count") if isinstance(pool, dict) else None,
        "request_schema_version": REQUEST_SCHEMA_VERSION,
        "rules_source_sha": rules_source_sha,
        "draft_sha256": hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None,
        "expected_candidates": expected,
        "valid_candidates": valid,
        "failed_candidates": max(0, expected - valid),
        "pool_errors": list(dict.fromkeys(pool_errors)),
        "candidate_results": candidate_results,
    }


def contract_payload():
    return {
        "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
        "pool_schema_version": POOL_SCHEMA_VERSION,
        "request_schema_version": REQUEST_SCHEMA_VERSION,
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "repository": REPOSITORY,
        "execution_environment": {
            "canonical_mode": "connector_native_checkpoint",
            "shell_git_required": False,
            "git_checkout_required": False,
            "repository_tree_materialization_required": False,
            "full_background_registry_local_copy_required": False,
            "github_actions_planning": False,
            "planning_passes": 4,
            "post_commit_planner_monitoring": False,
            "local_files_required": [
                "connector_checkpoint.py",
                "authored pool JSON",
                "small selected-evidence JSON",
            ],
        },
        "profiles": {
            "adhoc": {
                "allowed_planning_modes": ["manual_on_demand"],
                "target_count": 1,
                "expected_candidates": 1,
                "publication": PROFILE["adhoc"]["publication"],
                "global_media_readiness_required": False,
                "automatic_replenishment_enabled": False,
                "selected_background_validation_required": True,
                "background_same_category_required": True,
                "reserve_candidate_count": 0,
                "post_commit_planner_monitoring": False,
            },
            "daily": {
                "allowed_planning_modes": ["normal_next_day", "same_day_catch_up"],
                "normal_next_day": {"target_count": 24, "expected_candidates": 24},
                "same_day_catch_up": {"expected_candidates": "target_count"},
                "publication": PROFILE["daily"]["publication"],
                "global_media_readiness_required": False,
                "automatic_replenishment_enabled": False,
                "selected_background_validation_required": True,
                "background_same_category_required": True,
                "reserve_candidate_count": 0,
                "post_commit_planner_monitoring": False,
            },
        },
        "background": {
            "mode": BACKGROUND_MODE,
            "categories": sorted(BACKGROUND_CATEGORIES),
            "canonical_fallback_category": CANONICAL_BACKGROUND_FALLBACK_CATEGORY,
            "clip_count_min": MIN_SEQUENCE_CLIPS,
            "clip_count_preferred": PREFERRED_SEQUENCE_CLIPS,
            "clip_count_max": MAX_SEQUENCE_CLIPS,
            "clip_min_seconds": MIN_SEQUENCE_CLIP_SECONDS,
            "sequence_min_seconds": MIN_SEQUENCE_SOURCE_SECONDS,
            "sequence_preferred_seconds": PREFERRED_SEQUENCE_SOURCE_SECONDS,
            "sequence_max_seconds": MAX_SEQUENCE_SOURCE_SECONDS,
            "primary_backup_disjoint": True,
            "same_category_primary_backup": True,
            "planner_freezes_playback_rate": False,
            "runtime_derives_playback_rate_after_tts": True,
        },
        "evidence": {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "required_top_level": [
                "schema_version", "repository", "rules_source_sha", "checkpoint_blob_sha",
                "drift", "uniqueness", "selected_backgrounds",
            ],
            "global_media_readiness_forbidden": True,
            "replenishment_state_forbidden": True,
        },
        "recovery": {
            "checkpoint_failure": "repair affected authored input and rerun same checkpoint",
            "preferred_background_unavailable": "try alternate eligible category then canonical fallback",
            "replenishment": "not part of normal planning",
            "terminal_only_after_recoverable_options_exhausted": True,
        },
    }


def _load_json(path, label):
    try:
        raw = Path(path).read_bytes()
        return raw, json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read {label} {path}: {exc}") from exc


def main():
    parser = argparse.ArgumentParser(description="Connector-native Wacky Dramas planner checkpoint")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("contract")
    validate = sub.add_parser("validate")
    validate.add_argument("--profile", choices=("daily", "adhoc"), required=True)
    validate.add_argument("--pool", required=True)
    validate.add_argument("--rules-source-sha", required=True)
    validate.add_argument("--evidence", required=True)
    args = parser.parse_args()

    if args.command == "contract":
        print(json.dumps(contract_payload(), indent=2, sort_keys=True))
        return

    pool_raw, pool = _load_json(args.pool, "pool")
    _, evidence = _load_json(args.evidence, "connector evidence")
    original = copy.deepcopy(pool)
    result = validate_pool(args.profile, pool, args.rules_source_sha, evidence, raw_bytes=pool_raw)
    if pool != original:
        raise AssertionError("connector checkpoint mutated the authored pool")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
