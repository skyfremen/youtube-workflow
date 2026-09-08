import argparse
import json
from pathlib import Path

from workflow_common import ensure_request_path_matches, load_json

FORBIDDEN_KEYS = {
    "setup", "payoff", "cta", "comedy_mechanism", "series_role", "series_id",
    "series_title", "part_number", "part_total", "next_part_slot",
    "duration_seconds", "background_url", "background_source_url",
    "background_license", "background_creator", "privacy_status", "publishAt",
    "publish_at", "music_url", "music_source_url", "music_title", "music_artist",
    "music_license",
}
TOP_LEVEL_KEYS = {
    "schema_version", "content_id", "channel", "story", "narration", "visual", "youtube"
}
STORY_KEYS = {"category", "story_type", "hook", "script", "card_emojis"}
NARRATION_KEYS = {"engine", "voice", "speed"}
VISUAL_KEYS = {"background_primary_id", "background_backup_id"}
YOUTUBE_KEYS = {"title", "description", "hashtags", "category_id", "made_for_kids"}


def _nonempty(value):
    return bool(str(value or "").strip())


def validate_request_data(data, request_path=None):
    errors = []
    if not isinstance(data, dict):
        return ["request root must be an object"]
    if data.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    unknown = set(data) - TOP_LEVEL_KEYS
    if unknown:
        errors.append("unexpected top-level fields: " + ", ".join(sorted(unknown)))
    forbidden = set(data) & FORBIDDEN_KEYS
    if forbidden:
        errors.append("obsolete/forbidden fields present: " + ", ".join(sorted(forbidden)))

    channel = data.get("channel")
    if not isinstance(channel, dict):
        errors.append("channel must be an object")
    else:
        if set(channel) != {"name", "handle"}:
            errors.append("channel must contain exactly name and handle")
        if channel.get("name") != "Wacky Dramas":
            errors.append("channel.name must be Wacky Dramas")
        if channel.get("handle") != "@WACKYDRAMAS":
            errors.append("channel.handle must be @WACKYDRAMAS")

    story = data.get("story")
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
        emojis = story.get("card_emojis")
        if not isinstance(emojis, list) or not 4 <= len(emojis) <= 6:
            errors.append("story.card_emojis must contain 4-6 emojis")
        elif any(not _nonempty(x) for x in emojis):
            errors.append("story.card_emojis entries must be non-empty")
        script = str(story.get("script", ""))
        if "Wacky Insights" in script or "@WACKYINSIGHTS" in script or "#wackyinsights" in script.lower():
            errors.append("story script contains obsolete Wacky Insights branding")

    narration = data.get("narration")
    if not isinstance(narration, dict):
        errors.append("narration must be an object")
    else:
        if set(narration) != NARRATION_KEYS:
            errors.append("narration must contain exactly engine, voice, speed")
        if narration.get("engine") != "kokoro":
            errors.append("narration.engine must be kokoro")
        if not _nonempty(narration.get("voice")):
            errors.append("narration.voice must be non-empty")
        try:
            speed = float(narration.get("speed"))
            if not 0.5 <= speed <= 2.5:
                errors.append("narration.speed must be between 0.5 and 2.5")
        except (TypeError, ValueError):
            errors.append("narration.speed must be numeric")

    visual = data.get("visual")
    if not isinstance(visual, dict):
        errors.append("visual must be an object")
    else:
        if set(visual) != VISUAL_KEYS:
            errors.append("visual must contain exactly background_primary_id and background_backup_id")
        primary = str(visual.get("background_primary_id", "")).strip()
        backup = str(visual.get("background_backup_id", "")).strip()
        if not primary or not backup:
            errors.append("visual primary and backup background IDs are required")
        elif primary == backup:
            errors.append("visual primary and backup background IDs must differ")

    yt = data.get("youtube")
    if not isinstance(yt, dict):
        errors.append("youtube must be an object")
    else:
        missing = YOUTUBE_KEYS - set(yt)
        extra = set(yt) - YOUTUBE_KEYS
        if missing:
            errors.append("youtube missing fields: " + ", ".join(sorted(missing)))
        if extra:
            errors.append("youtube unexpected fields: " + ", ".join(sorted(extra)))
        title = str(yt.get("title", "")).strip()
        if not title or len(title) > 100 or "#Shorts" not in title:
            errors.append("youtube.title must be non-empty, <=100 chars, and contain #Shorts")
        if not _nonempty(yt.get("description")):
            errors.append("youtube.description must be non-empty")
        tags = yt.get("hashtags")
        if not isinstance(tags, list) or not 3 <= len(tags) <= 8:
            errors.append("youtube.hashtags must contain 3-8 entries")
        elif any(not str(x).strip().startswith("#") for x in tags):
            errors.append("youtube.hashtags entries must start with #")
        if not _nonempty(yt.get("category_id")):
            errors.append("youtube.category_id must be non-empty")
        if yt.get("made_for_kids") is not False:
            errors.append("youtube.made_for_kids must be false for this workflow")

    serialized = json.dumps(data, ensure_ascii=False)
    for term in ("@WACKYINSIGHTS", "#wackyinsights", "Wacky Insights"):
        if term.lower() in serialized.lower():
            errors.append(f"request contains obsolete branding: {term}")
    if request_path and not errors:
        try:
            ensure_request_path_matches(request_path, data)
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def validate_request(path):
    path = Path(path)
    data = load_json(path)
    errors = validate_request_data(data, request_path=path)
    if errors:
        raise SystemExit("Wacky Dramas request validation failed:\n- " + "\n- ".join(errors))
    print(f"Request valid: {path.name}")
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    validate_request(args.request)


if __name__ == "__main__":
    main()
