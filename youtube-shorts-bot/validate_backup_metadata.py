import argparse
import json
from pathlib import Path

BASE = Path(__file__).parent
PLANS = BASE / 'content' / 'plans'

BACKGROUND_BACKUP_FIELDS = (
    'background_backup_url', 'background_backup_source_url',
    'background_backup_creator', 'background_backup_license',
    'background_backup_credit',
)
MUSIC_BACKUP_FIELDS = (
    'music_backup_url', 'music_backup_source_url', 'music_backup_title',
    'music_backup_artist', 'music_backup_license', 'music_backup_credit',
)
MATCH_FIELDS = (
    'background_scene', 'background_match_reason', 'background_match_score',
    'background_backup_scene', 'background_backup_match_reason', 'background_backup_match_score',
    'music_mood', 'music_match_reason', 'music_match_score',
    'music_backup_mood', 'music_backup_match_reason', 'music_backup_match_score',
)

MIN_MATCH_SCORE = 85.0
MIN_REASON_LENGTH = 24
MIN_SCENE_LENGTH = 8


def validate_group(content, fields, label, item_no, errors):
    missing = [field for field in fields if not str(content.get(field, '')).strip()]
    if missing:
        errors.append(
            f'item {item_no}: incomplete {label} backup metadata; missing: {", ".join(missing)}'
        )


def validate_score(content, field, item_no, errors):
    value = content.get(field)
    if isinstance(value, bool):
        errors.append(f'item {item_no}: {field} must be numeric')
        return
    try:
        score = float(value)
    except (TypeError, ValueError):
        errors.append(f'item {item_no}: {field} must be numeric')
        return
    if not 0 <= score <= 100:
        errors.append(f'item {item_no}: {field} must be between 0 and 100')
    elif score < MIN_MATCH_SCORE:
        errors.append(
            f'item {item_no}: {field} is {score:g}; media-content match must be >= {MIN_MATCH_SCORE:g}'
        )


def validate_match_metadata(content, item_no, errors):
    missing = [field for field in MATCH_FIELDS if field not in content or content.get(field) is None]
    if missing:
        errors.append(
            f'item {item_no}: missing semantic media-match fields: {", ".join(missing)}'
        )
        return

    for field in ('background_scene', 'background_backup_scene', 'music_mood', 'music_backup_mood'):
        if len(str(content.get(field, '')).strip()) < MIN_SCENE_LENGTH:
            errors.append(f'item {item_no}: {field} is too vague; describe the actual scene/mood')

    for field in (
        'background_match_reason', 'background_backup_match_reason',
        'music_match_reason', 'music_backup_match_reason',
    ):
        if len(str(content.get(field, '')).strip()) < MIN_REASON_LENGTH:
            errors.append(
                f'item {item_no}: {field} is too vague; explain specifically why the asset fits this joke'
            )

    for field in (
        'background_match_score', 'background_backup_match_score',
        'music_match_score', 'music_backup_match_score',
    ):
        validate_score(content, field, item_no, errors)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True)
    args = parser.parse_args()

    path = PLANS / f'{args.date}.json'
    plan = json.loads(path.read_text(encoding='utf-8'))
    errors = []

    for idx, item in enumerate(plan.get('items', []), 1):
        content = item.get('content', {}) if isinstance(item, dict) else {}
        validate_group(content, BACKGROUND_BACKUP_FIELDS, 'background', idx, errors)
        validate_group(content, MUSIC_BACKUP_FIELDS, 'music', idx, errors)
        validate_match_metadata(content, idx, errors)

        bg_primary = str(content.get('background_url', '')).strip()
        bg_backup = str(content.get('background_backup_url', '')).strip()
        if bg_backup and bg_backup == bg_primary:
            errors.append(f'item {idx}: background backup must differ from primary')

        music_primary = str(content.get('music_url', '')).strip()
        music_backup = str(content.get('music_backup_url', '')).strip()
        if music_backup and music_backup == music_primary:
            errors.append(f'item {idx}: music backup must differ from primary')

    if errors:
        raise SystemExit('Media metadata validation failed:\n- ' + '\n- '.join(errors))

    print(
        'Media metadata valid: primary/backup assets include explicit scene/mood matching '
        f'with scores >= {MIN_MATCH_SCORE:g}; backup media was not downloaded.'
    )


if __name__ == '__main__':
    main()
