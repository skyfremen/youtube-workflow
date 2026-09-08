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

# GitHub-hosted production is CPU-only. Install CPU PyTorch first so Kokoro
# cannot pull the multi-gigabyte CUDA dependency stack.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

COPY youtube-shorts-bot/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Kokoro's English frontend otherwise downloads this on a fresh production job.
RUN python -m spacy download en_core_web_sm

# Warm the model and default voice during image build; ordinary content changes
# never rebuild this image.
RUN python - <<'PY'
from kokoro import KPipeline
pipeline = KPipeline(lang_code='a')
for _gs, _ps, _audio in pipeline('Wacky Dramas runner warmup.', voice='af_heart', speed=1.0):
    break
print('Kokoro model and af_heart voice cache ready')
PY

WORKDIR /__w/youtube-workflow/youtube-workflow
