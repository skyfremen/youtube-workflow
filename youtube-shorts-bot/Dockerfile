FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TORCH_HOME=/opt/torch-cache

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

# Pin the CPU PyTorch/TorchAudio pair. TorchAudio 2.8 provides the optimized
# CTC forced-align primitive used by the Wav2Vec2 caption aligner; pinning the
# pair keeps the prebuilt runner deterministic and prevents CUDA downloads.
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
    torch==2.8.0 torchaudio==2.8.0

COPY youtube-shorts-bot/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Kokoro's English frontend otherwise downloads this on a fresh production job.
RUN python -m spacy download en_core_web_sm

# Warm the Kokoro model and default voice during image build; ordinary content
# changes never rebuild this image.
RUN python - <<'PY'
from kokoro import KPipeline
pipeline = KPipeline(lang_code='a')
for _gs, _ps, _audio in pipeline('Wacky Dramas runner warmup.', voice='af_heart', speed=1.0):
    break
print('Kokoro model and af_heart voice cache ready')
PY

# Cache the English Wav2Vec2 acoustic model in TORCH_HOME during the image
# build. Production caption alignment is therefore fully offline and performs
# no apt/pip/model download in an ordinary publishing run.
RUN python - <<'PY'
import torchaudio
bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
model = bundle.get_model()
model.eval()
print('Wav2Vec2 forced-alignment model cache ready')
PY

WORKDIR /__w/youtube-workflow/youtube-workflow
