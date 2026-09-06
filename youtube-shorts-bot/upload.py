import json, os
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = Path(__file__).parent
with (BASE/'content'/'latest.json').open(encoding='utf-8') as f:
    data = json.load(f)
with (BASE/'music_catalog.json').open(encoding='utf-8') as f:
    music_catalog = json.load(f)

music_key = data.get('music', 'monkeys_spinning_monkeys')
music_info = music_catalog.get(music_key, music_catalog['monkeys_spinning_monkeys'])

creds = Credentials(
    token=None,
    refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
    token_uri='https://oauth2.googleapis.com/token',
    client_id=os.environ['YOUTUBE_CLIENT_ID'],
    client_secret=os.environ['YOUTUBE_CLIENT_SECRET'],
    scopes=['https://www.googleapis.com/auth/youtube.upload'],
)

youtube = build('youtube','v3',credentials=creds)

parts = [data.get('description','').strip()]
credit = music_info.get('credit','').strip()
if credit:
    parts.append(credit)
hashtags = ' '.join(data.get('hashtags',[])).strip()
if hashtags:
    parts.append(hashtags)
description = '\n\n'.join(p for p in parts if p)[:5000]

body = {
  'snippet': {
    'title': data['title'][:100],
    'description': description,
    'categoryId': '28'
  },
  'status': {
    'privacyStatus': os.getenv('YOUTUBE_PRIVACY','private'),
    'selfDeclaredMadeForKids': False
  }
}

media = MediaFileUpload(str(BASE/'output'/'short.mp4'), mimetype='video/mp4', resumable=True)
request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
response = None
while response is None:
    _, response = request.next_chunk()
print('Uploaded video ID:', response['id'])
print('Music:', music_info['title'], '-', music_info['artist'])
