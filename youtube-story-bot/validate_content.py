import json
from pathlib import Path

p = Path(__file__).parent / 'content' / 'latest.json'
data = json.loads(p.read_text(encoding='utf-8'))
required = ['channel_name','handle','story_type','hook','story','title','background_url']
missing = [k for k in required if not str(data.get(k,'')).strip()]
if missing:
    raise SystemExit('Missing required story fields: ' + ', '.join(missing))
if not str(data['handle']).startswith('@'):
    raise SystemExit('handle must start with @')
duration = float(data.get('duration_seconds', 45))
if not 5 <= duration <= 90:
    raise SystemExit('duration_seconds must be between 5 and 90')
if len(data['story'].split()) < 8:
    raise SystemExit('story is too short')
print('Story content valid:', data['hook'])
