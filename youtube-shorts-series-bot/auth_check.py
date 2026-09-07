import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

required = ('YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET', 'YOUTUBE_REFRESH_TOKEN')
missing = [name for name in required if not str(os.environ.get(name, '')).strip()]
if missing:
    raise SystemExit('YouTube credential preflight failed: missing ' + ', '.join(missing))

creds = Credentials(
    token=None,
    refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
    token_uri='https://oauth2.googleapis.com/token',
    client_id=os.environ['YOUTUBE_CLIENT_ID'],
    client_secret=os.environ['YOUTUBE_CLIENT_SECRET'],
    scopes=[
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.readonly',
    ],
)

youtube = build('youtube', 'v3', credentials=creds, cache_discovery=False)
response = youtube.channels().list(part='id', mine=True).execute()
if not response.get('items'):
    raise SystemExit('YouTube credential preflight failed: authenticated account has no accessible YouTube channel.')

print('YouTube OAuth preflight OK: credentials are valid and channel access is available.')
