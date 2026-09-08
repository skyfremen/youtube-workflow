import argparse
from datetime import datetime, timezone

from schedule_utils import MIN_SCHEDULE_LEAD, ensure_publish_at_is_safe, scheduled_publish_at


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True)
    parser.add_argument('--slot', required=True, type=int)
    args = parser.parse_args()

    publish_at = scheduled_publish_at(args.date, args.slot)
    now = datetime.now(timezone.utc)
    try:
        ensure_publish_at_is_safe(publish_at, now=now)
    except ValueError as exc:
        print(
            'MISSED_SCHEDULE_WINDOW: '
            f'slot {args.slot} for {args.date} is no longer safely schedulable; '
            f'publishAt={publish_at}, now={now.isoformat()}, '
            f'minLeadMinutes={int(MIN_SCHEDULE_LEAD.total_seconds() // 60)}. '
            'Skipping before media download/render.'
        )
        raise SystemExit(20)

    print(
        f'SCHEDULE_WINDOW_SAFE: slot {args.slot}, publishAt={publish_at}, '
        f'now={now.isoformat()}.'
    )
