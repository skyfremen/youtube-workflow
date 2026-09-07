import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
PLANS = BASE / 'content' / 'plans'
sys.path.insert(0, str(BASE))

from queue_manager import validate_plan

MIN_SERIES_PARTS_TOTAL = 12
MAX_SERIES_PARTS_TOTAL = 16
MIN_DISTINCT_SERIES = 3
MIN_PARTS_PER_SERIES = 3


def fail(errors):
    raise SystemExit('Series plan validation failed:\n- ' + '\n- '.join(errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True)
    args = parser.parse_args()

    path = PLANS / f'{args.date}.json'
    validate_plan(path)
    plan = json.loads(path.read_text(encoding='utf-8'))
    items = plan.get('items', [])
    errors = []

    by_slot = {item.get('slot'): item for item in items if isinstance(item, dict)}
    series = {}
    series_parts_total = 0

    for idx, item in enumerate(items, 1):
        content = item.get('content', {}) if isinstance(item, dict) else {}
        required_fields = (
            'series_role', 'series_id', 'series_title', 'part_number',
            'part_total', 'next_part_slot', 'series_potential'
        )
        missing = [field for field in required_fields if field not in content]
        if missing:
            errors.append(f'item {idx}: missing series metadata: {", ".join(missing)}')
            continue

        role = content.get('series_role')
        cta = str(content.get('cta', '')).strip()

        try:
            potential = float(content.get('series_potential'))
        except (TypeError, ValueError):
            errors.append(f'item {idx}: series_potential must be numeric')
            potential = -1
        if not 0 <= potential <= 100:
            errors.append(f'item {idx}: series_potential must be between 0 and 100')

        if role == 'standalone':
            for field in ('series_id', 'series_title', 'part_number', 'part_total', 'next_part_slot'):
                if content.get(field) is not None:
                    errors.append(f'item {idx}: standalone {field} must be null')
            if cta != 'DOUBLE TAP TO AGREE':
                errors.append(f'item {idx}: standalone CTA must be DOUBLE TAP TO AGREE')
            continue

        if role != 'series':
            errors.append(f'item {idx}: series_role must be series or standalone')
            continue

        series_parts_total += 1
        sid = str(content.get('series_id') or '').strip()
        title = str(content.get('series_title') or '').strip()
        if not sid:
            errors.append(f'item {idx}: series_id is required for series content')
            continue
        if not title:
            errors.append(f'item {idx}: series_title is required for series content')

        try:
            part_number = int(content.get('part_number'))
            part_total = int(content.get('part_total'))
        except (TypeError, ValueError):
            errors.append(f'item {idx}: part_number and part_total must be integers')
            continue

        if part_total < MIN_PARTS_PER_SERIES:
            errors.append(f'item {idx}: part_total must be >= {MIN_PARTS_PER_SERIES}')
        if not 1 <= part_number <= part_total:
            errors.append(f'item {idx}: part_number must be between 1 and part_total')

        series.setdefault(sid, []).append((part_number, item.get('slot'), content))

        if part_number < part_total:
            expected_cta = f'FOLLOW FOR PART {part_number + 1}'
            if cta != expected_cta:
                errors.append(f'item {idx}: CTA must be {expected_cta}')
            next_slot = content.get('next_part_slot')
            current_slot = item.get('slot')
            if not isinstance(next_slot, int) or next_slot not in by_slot:
                errors.append(f'item {idx}: next_part_slot must point to an existing slot')
            elif not isinstance(current_slot, int) or next_slot <= current_slot:
                errors.append(f'item {idx}: next_part_slot must be later than the current slot')
            elif next_slot - current_slot < 4:
                errors.append(f'item {idx}: next series part must be at least 4 slots later')
            elif next_slot - current_slot > 8:
                errors.append(f'item {idx}: next series part must be no more than 8 slots later')
        else:
            if content.get('next_part_slot') is not None:
                errors.append(f'item {idx}: final series part next_part_slot must be null')
            if cta not in {'FOLLOW FOR MORE', 'DOUBLE TAP TO AGREE'}:
                errors.append(f'item {idx}: final series CTA must be FOLLOW FOR MORE or DOUBLE TAP TO AGREE')

    if not MIN_SERIES_PARTS_TOTAL <= series_parts_total <= MAX_SERIES_PARTS_TOTAL:
        errors.append(f'series parts total must be {MIN_SERIES_PARTS_TOTAL}-{MAX_SERIES_PARTS_TOTAL}; found {series_parts_total}')
    if len(series) < MIN_DISTINCT_SERIES:
        errors.append(f'plan must contain at least {MIN_DISTINCT_SERIES} distinct series; found {len(series)}')

    for sid, parts in series.items():
        parts.sort()
        numbers = [p[0] for p in parts]
        declared_totals = {int(p[2].get('part_total')) for p in parts}
        titles = {str(p[2].get('series_title')) for p in parts}
        if len(declared_totals) != 1:
            errors.append(f'series {sid}: inconsistent part_total values')
            continue
        total = next(iter(declared_totals))
        if numbers != list(range(1, total + 1)):
            errors.append(f'series {sid}: parts must cover 1 through {total}; found {numbers}')
        if len(titles) != 1:
            errors.append(f'series {sid}: series_title must be consistent across parts')
        for i in range(len(parts) - 1):
            _, _, content = parts[i]
            expected_next_slot = parts[i + 1][1]
            if content.get('next_part_slot') != expected_next_slot:
                errors.append(f'series {sid} part {parts[i][0]}: next_part_slot must be {expected_next_slot}')

    if errors:
        fail(errors)

    print(
        f'Series plan valid: {path.name}; {series_parts_total} series parts across '
        f'{len(series)} series plus {24 - series_parts_total} standalone controls.'
    )


if __name__ == '__main__':
    main()
