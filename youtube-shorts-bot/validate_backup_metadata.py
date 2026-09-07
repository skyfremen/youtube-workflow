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


def validate_group(content, fields, label, item_no, errors):
    missing = [field for field in fields if not str(content.get(field, '')).strip()]
    if missing:
        errors.append(
            f'item {item_no}: incomplete {label} backup metadata; missing: {", ".join(missing)}'
        )


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

        bg_primary = str(content.get('background_url', '')).strip()
        bg_backup = str(content.get('background_backup_url', '')).strip()
        if bg_backup and bg_backup == bg_primary:
            errors.append(f'item {idx}: background backup must differ from primary')

        music_primary = str(content.get('music_url', '')).strip()
        music_backup = str(content.get('music_backup_url', '')).strip()
        if music_backup and music_backup == music_primary:
            errors.append(f'item {idx}: music backup must differ from primary')

    if errors:
        raise SystemExit('Backup media metadata validation failed:\n- ' + '\n- '.join(errors))

    print('Backup media metadata valid; no backup media was downloaded.')


if __name__ == '__main__':
    main()
