import argparse
import json
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from zoneinfo import ZoneInfo

from workflow_common import archive_records

BASE = Path(__file__).parent
CONTENT_DIR = BASE / 'content'
PLANS_DIR = CONTENT_DIR / 'plans'
ARCHIVE_DIR = CONTENT_DIR / 'archive'
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)

CONTENT_FIELDS = (
    'topic', 'category', 'setup', 'payoff', 'cta', 'handle', 'title', 'description',
    'hashtags', 'background_url', 'background_source_url', 'background_creator',
    'background_license', 'background_credit', 'music_url', 'music_source_url',
    'music_title', 'music_artist', 'music_license', 'music_credit'
)
SCORE_FIELDS = ('relatability', 'funny', 'hook', 'originality', 'clarity', 'visual_potential', 'total')
SCORE_WEIGHTS = {
    'relatability': 0.30,
    'funny': 0.25,
    'hook': 0.15,
    'originality': 0.15,
    'clarity': 0.10,
    'visual_potential': 0.05,
}
VALID_STATUSES = {'pending', 'published'}


def sg_date():
    return datetime.now(ZoneInfo('Asia/Singapore')).date().isoformat()


def normalize(text):
    text = re.sub(r'[^a-z0-9 ]+', ' ', str(text).lower())
    return ' '.join(text.split())


def concept_text(content):
    return normalize(' '.join(str(content.get(k, '')) for k in ('topic', 'setup', 'payoff')))


def similarity(a, b):
    return SequenceMatcher(None, concept_text(a), concept_text(b)).ratio()


def load_plan(path):
    return json.loads(path.read_text(encoding='utf-8'))


def plan_path(date=None):
    return PLANS_DIR / f'{date or sg_date()}.json'


def _numeric_score(value, label, errors):
    if isinstance(value, bool):
        errors.append(f'{label}: score must be numeric, not boolean')
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f'{label}: score must be numeric')
        return None
    if not 0 <= number <= 100:
        errors.append(f'{label}: score {number:g} must be between 0 and 100')
        return None
    return number


def validate_plan(path):
    plan = load_plan(path)
    errors = []
    items = plan.get('items')

    expected_date = path.stem
    if plan.get('plan_date') != expected_date:
        errors.append(f'plan_date must match filename date {expected_date}')
    if plan.get('target_count') != 20:
        errors.append('target_count must be 20')

    candidates_generated = plan.get('candidates_generated')
    if isinstance(candidates_generated, bool) or not isinstance(candidates_generated, int) or candidates_generated < 50:
        errors.append('candidates_generated must be an integer >= 50')

    if not isinstance(items, list) or len(items) != 20:
        errors.append('items must contain exactly 20 Shorts')
        items = items if isinstance(items, list) else []

    seen_slots, seen_backgrounds, seen_music = set(), set(), set()
    for idx, item in enumerate(items, 1):
        if not isinstance(item, dict):
            errors.append(f'item {idx}: must be an object')
            continue

        slot = item.get('slot')
        if isinstance(slot, bool) or not isinstance(slot, int) or not 1 <= slot <= 20:
            errors.append(f'item {idx}: slot must be an integer from 1 to 20')
        elif slot in seen_slots:
            errors.append(f'item {idx}: duplicate slot {slot}')
        else:
            seen_slots.add(slot)

        status = item.get('status')
        if status not in VALID_STATUSES:
            errors.append(f'item {idx}: status must be pending or published')

        content = item.get('content', {})
        missing = [k for k in CONTENT_FIELDS if k not in content or content.get(k) is None]
        if missing:
            errors.append(f'item {idx}: missing content fields: {", ".join(missing)}')
            continue
        if content.get('handle') != '@WACKYINSIGHTS':
            errors.append(f'item {idx}: handle must be @WACKYINSIGHTS')
        if '#Shorts' not in str(content.get('title', '')) or len(str(content.get('title', ''))) > 100:
            errors.append(f'item {idx}: title must include #Shorts and be <=100 chars')

        scores = item.get('quality', {})
        missing_scores = [k for k in SCORE_FIELDS if k not in scores]
        if missing_scores:
            errors.append(f'item {idx}: missing quality scores: {", ".join(missing_scores)}')
        else:
            parsed = {key: _numeric_score(scores.get(key), f'item {idx} {key}', errors) for key in SCORE_FIELDS}
            if all(parsed.get(key) is not None for key in SCORE_WEIGHTS) and parsed.get('total') is not None:
                calculated = sum(parsed[key] * weight for key, weight in SCORE_WEIGHTS.items())
                if abs(parsed['total'] - calculated) > 0.5:
                    errors.append(
                        f'item {idx}: quality total {parsed["total"]:.2f} does not match weighted score {calculated:.2f}'
                    )
                if calculated < 75:
                    errors.append(f'item {idx}: weighted quality score {calculated:.2f} is below 75')

        if not str(item.get('comedy_mechanism', '')).strip():
            errors.append(f'item {idx}: comedy_mechanism is required')
        bg = str(content.get('background_url', '')).strip()
        music = str(content.get('music_url', '')).strip()
        if bg in seen_backgrounds:
            errors.append(f'item {idx}: duplicate background_url in batch')
        if music in seen_music:
            errors.append(f'item {idx}: duplicate music_url in batch')
        seen_backgrounds.add(bg)
        seen_music.add(music)

    if len(seen_slots) != 20 and len(items) == 20:
        errors.append('slots must be unique and cover 1 through 20 exactly once')

    for i in range(len(items)):
        ci = items[i].get('content', {}) if isinstance(items[i], dict) else {}
        for j in range(i + 1, len(items)):
            cj = items[j].get('content', {}) if isinstance(items[j], dict) else {}
            sim = similarity(ci, cj)
            if sim >= 0.78:
                errors.append(f'items {i+1} and {j+1}: concepts too similar ({sim:.2f})')

    recent = [record for _, record in archive_records(ARCHIVE_DIR)]
    for idx, item in enumerate(items, 1):
        if not isinstance(item, dict) or item.get('status') == 'published':
            continue
        content = item.get('content', {})
        for old in recent[-100:]:
            sim = similarity(content, old)
            if sim >= 0.82:
                errors.append(f'item {idx}: too similar to archived concept ({sim:.2f})')
                break

    if errors:
        raise SystemExit('Daily plan validation failed:\n- ' + '\n- '.join(errors))
    print(f'Daily plan valid: {path.name}, 20 quality-gated Shorts.')


def select_next(path):
    validate_plan(path)
    plan = load_plan(path)
    selection_path = OUT / 'queue_selection.json'
    selection_path.unlink(missing_ok=True)
    for idx, item in enumerate(plan['items']):
        if item.get('status', 'pending') == 'pending':
            content = item['content']
            (CONTENT_DIR / 'latest.json').write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            selection = {'plan_path': str(path), 'item_index': idx, 'slot': item.get('slot', idx + 1)}
            selection_path.write_text(json.dumps(selection, indent=2) + '\n', encoding='utf-8')
            print(f'Selected queue slot {selection["slot"]}.')
            return True
    print('NO_PENDING_SHORTS: daily queue is complete; nothing to publish.')
    return False


def mark_published(path):
    plan = load_plan(path)
    selection = json.loads((OUT / 'queue_selection.json').read_text(encoding='utf-8'))
    upload = json.loads((OUT / 'upload_result.json').read_text(encoding='utf-8'))
    idx = int(selection['item_index'])
    item = plan['items'][idx]
    item['status'] = 'published'
    item['youtube_video_id'] = upload['youtube_video_id']
    item['youtube_url'] = upload['youtube_url']
    item['uploaded_at'] = upload.get('uploaded_at', '')
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Marked queue slot {item.get("slot", idx + 1)} published.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('validate', 'select', 'mark'))
    parser.add_argument('--date')
    args = parser.parse_args()
    path = plan_path(args.date)
    if not path.exists():
        if args.command == 'select':
            (OUT / 'queue_selection.json').unlink(missing_ok=True)
            print(f'NO_PLAN_FOR_TODAY: {path.name} does not exist; nothing to publish.')
            raise SystemExit(0)
        raise SystemExit(f'Plan not found: {path}')
    {'validate': validate_plan, 'select': select_next, 'mark': mark_published}[args.command](path)
