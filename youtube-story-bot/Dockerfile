FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_TELEMETRY=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       ffmpeg \
       espeak-ng \
       libsndfile1 \
       fonts-dejavu-core \
       fonts-noto-color-emoji \
       git \
    && rm -rf /var/lib/apt/lists/*

# GitHub-hosted Actions runners for this job are CPU-only. Install CPU PyTorch
# first so Kokoro does not pull the multi-gigabyte CUDA dependency stack.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

COPY youtube-story-bot/requirements.txt /tmp/story-requirements.txt
RUN pip install -r /tmp/story-requirements.txt

# Kokoro's English frontend otherwise downloads this on a fresh runner.
RUN python -m spacy download en_core_web_sm

# Warm Kokoro during the image build so its model and af_heart voice are cached
# in the image instead of being downloaded for every render job.
RUN python - <<'PY'
from kokoro import KPipeline
pipeline = KPipeline(lang_code='a')
for _gs, _ps, _audio in pipeline('Wacky Dramas runner warmup.', voice='af_heart', speed=1.0):
    break
print('Kokoro model cache ready')
PY

WORKDIR /__w/youtube-workflow/youtube-workflow
