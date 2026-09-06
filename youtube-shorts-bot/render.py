import json, os, subprocess, textwrap
from pathlib import Path

BASE = Path(__file__).parent
CONTENT = BASE / 'content' / 'latest.json'
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)

with CONTENT.open(encoding='utf-8') as f:
    data = json.load(f)

script = data['script'].strip()
title = data.get('title','YouTube Short')

# Generate narration using the free local espeak-ng package on the GitHub runner.
voice_wav = OUT / 'voice.wav'
subprocess.run(['espeak-ng','-s','165','-w',str(voice_wav),script], check=True)

# Build simple timed SRT captions from the script.
words = script.split()
chunks = [' '.join(words[i:i+7]) for i in range(0, len(words), 7)]

def ts(seconds):
    ms = int((seconds - int(seconds))*1000)
    s = int(seconds)
    h, s = divmod(s,3600); m, s = divmod(s,60)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

# Probe narration duration.
probe = subprocess.check_output([
    'ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(voice_wav)
], text=True).strip()
duration = max(float(probe), 1.0)
step = duration / max(len(chunks),1)

srt = OUT / 'captions.srt'
with srt.open('w', encoding='utf-8') as f:
    for i, chunk in enumerate(chunks,1):
        start=(i-1)*step; end=min(i*step,duration)
        f.write(f'{i}\n{ts(start)} --> {ts(end)}\n{chunk}\n\n')

video = OUT / 'short.mp4'
# Clean kinetic-caption style. No paid assets or APIs required.
filter_complex = (
    "drawbox=x=0:y=0:w=iw:h=ih:color=0x111111:t=fill," 
    "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
    "text='@skyfremen':x=(w-text_w)/2:y=120:fontsize=42:fontcolor=white@0.55," 
    "subtitles='" + str(srt).replace("'", "\\'") + "':force_style='Alignment=2,FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,MarginV=220'"
)

subprocess.run([
    'ffmpeg','-y','-f','lavfi','-i',f'color=c=0x111111:s=1080x1920:r=30:d={duration}',
    '-i',str(voice_wav),'-vf',filter_complex,
    '-c:v','libx264','-preset','medium','-pix_fmt','yuv420p',
    '-c:a','aac','-b:a','192k','-shortest',str(video)
], check=True)

print(video)
