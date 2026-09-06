import json, os
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = Path(__file__).parent
with (BASE/'content'/'latest.json').open(encoding='utf-8') as f:
    data = json.load(f)

creds = Credentials(
    token=None,
    refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
    token_uri='https://oauth2.googleapis.com/token',
    client_id=os.environ['YOUTUBE_CLIENT_ID'],
    client_secret=os.environ['YOUTUBE_CLIENT_SECRET'],
    scopes=['https://www.googleapis.com/auth/youtube.upload'],
)

youtube = build('youtube','v3',credentials=creds)
body = {
  'snippet': {
    'title': data['title'][:100],
    'description': (data.get('description','') + '\n\n' + ' '.join(data.get('hashtags',[])))[:5000],
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
