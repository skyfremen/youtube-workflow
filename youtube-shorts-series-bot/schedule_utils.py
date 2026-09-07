import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SGT = ZoneInfo('Asia/Singapore')
FIRST_PUBLISH_HOUR = 0
LAST_PUBLISH_HOUR = 23
TOTAL_SLOTS = 24
MIN_SCHEDULE_LEAD = timedelta(minutes=10)


def scheduled_publish_at(plan_date, slot):
    """Return the UTC ISO-8601 publishAt timestamp for a Singapore queue slot.

    Slot 1 publishes at 00:00 SGT, slot 24 at 23:00 SGT on plan_date.
    """
    try:
        plan_day = date.fromisoformat(str(plan_date))
    except ValueError as exc:
        raise ValueError(f'Invalid plan_date for scheduled publishing: {plan_date!r}') from exc

    if isinstance(slot, bool):
        raise ValueError('Queue slot must be an integer from 1 to 24.')
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


def parse_publish_at(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)


def ensure_publish_at_is_safe(publish_at, now=None, min_lead=MIN_SCHEDULE_LEAD):
    """Fail closed when a scheduled YouTube release is too close or in the past.

    YouTube can immediately publish a private video when publishAt is in the past.
    Keeping a lead-time buffer also prevents a long render/upload from crossing the
    requested release time before the API call completes.
    """
    scheduled = parse_publish_at(publish_at)
    current = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)
    earliest_safe = current + min_lead
    if scheduled <= earliest_safe:
        raise ValueError(
            'MISSED_SCHEDULE_WINDOW: requested YouTube publishAt '
            f'{scheduled.isoformat()} must be more than {int(min_lead.total_seconds() // 60)} '
            f'minutes after current time {current.isoformat()}.'
        )
    return scheduled.isoformat(timespec='seconds').replace('+00:00', 'Z')


def scheduled_publish_at_from_selection(selection_path, require_safe=False, now=None):
    path = Path(selection_path)
    if not path.exists():
        raise ValueError(f'Queue selection file is missing: {path}')
    selection = json.loads(path.read_text(encoding='utf-8'))
    publish_at = scheduled_publish_at(selection.get('plan_date'), selection.get('slot'))
    if require_safe:
        return ensure_publish_at_is_safe(publish_at, now=now)
    return publish_at
