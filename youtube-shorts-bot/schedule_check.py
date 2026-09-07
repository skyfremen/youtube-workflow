from pathlib import Path

from schedule_utils import scheduled_publish_at_from_selection

BASE = Path(__file__).parent
selection = BASE / 'output' / 'queue_selection.json'
try:
    publish_at = scheduled_publish_at_from_selection(selection, require_safe=True)
except ValueError as exc:
    raise SystemExit(str(exc))

print('Schedule window safe:', publish_at)
