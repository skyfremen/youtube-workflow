import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SGT = ZoneInfo('Asia/Singapore')
FIRST_PUBLISH_HOUR = 4
LAST_PUBLISH_HOUR = 23
TOTAL_SLOTS = 20


def scheduled_publish_at(plan_date, slot):
    """Return the UTC ISO-8601 publishAt timestamp for a Singapore queue slot.

    Slot 1 publishes at 04:00 SGT, slot 20 at 23:00 SGT on plan_date.
    """
    try:
        plan_day = date.fromisoformat(str(plan_date))
    except ValueError as exc:
        raise ValueError(f'Invalid plan_date for scheduled publishing: {plan_date!r}') from exc

    if isinstance(slot, bool):
        raise ValueError('Queue slot must be an integer from 1 to 20.')
    try:
        slot_number = int(slot)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'Invalid queue slot for scheduled publishing: {slot!r}') from exc
    if not 1 <= slot_number <= TOTAL_SLOTS:
        raise ValueError(f'Queue slot must be between 1 and {TOTAL_SLOTS}; got {slot_number}.')

    local_hour = FIRST_PUBLISH_HOUR + slot_number - 1
    if local_hour > LAST_PUBLISH_HOUR:
        raise ValueError(f'Calculated Singapore publish hour is out of range: {local_hour}.')

    local_dt = datetime.combine(plan_day, time(hour=local_hour), tzinfo=SGT)
    return local_dt.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def scheduled_publish_at_from_selection(selection_path):
    path = Path(selection_path)
    if not path.exists():
        raise ValueError(f'Queue selection file is missing: {path}')
    selection = json.loads(path.read_text(encoding='utf-8'))
    return scheduled_publish_at(selection.get('plan_date'), selection.get('slot'))
