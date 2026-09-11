FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HOME=/opt/huggingface \
    HF_HUB_CACHE=/opt/huggingface/hub \
    TORCH_HOME=/opt/torch-cache \
    RUNTIME_RESOURCE_HOME=/opt/kokoro-onnx \
    RUNTIME_RESOURCE_A=/opt/kokoro-onnx/kokoro-v1.0.onnx \
    RUNTIME_RESOURCE_B=/opt/kokoro-onnx/voices-v1.0.bin

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       ffmpeg \
       espeak-ng \
       libsndfile1 \
       fonts-dejavu-core \
       fonts-noto-color-emoji \
       git \
    && rm -rf /var/lib/apt/lists/*

# Pin the CPU PyTorch/TorchAudio pair. TorchAudio remains required for the
# Wav2Vec2 forced aligner, and PyTorch Kokoro is retained temporarily as a
# controlled TTS fallback while ONNX FP32 is the production primary.
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
    torch==2.8.0 torchaudio==2.8.0

COPY youtube-shorts-bot/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Kokoro's English frontend otherwise downloads this on a fresh fallback run.
RUN python -m spacy download en_core_web_sm

# Bake the exact FP32 model and voices used by benchmark run 34307845596.
# Production must never download these 350+ MB assets at request time.
RUN mkdir -p "$RUNTIME_RESOURCE_HOME" \
    && python - <<'PY'
import os
import urllib.request
from pathlib import Path

assets = {
    Path(os.environ['RUNTIME_RESOURCE_A']): (
        'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx',
        300_000_000,
    ),
    Path(os.environ['RUNTIME_RESOURCE_B']): (
        'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin',
        20_000_000,
    ),
}
for target, (url, minimum) in assets.items():
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={'User-Agent': 'WackyDramasRunnerBuild/1.0'})
    with urllib.request.urlopen(request, timeout=240) as response, target.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    if target.stat().st_size < minimum:
        raise SystemExit(f'Baked ONNX asset is suspiciously small: {target} ({target.stat().st_size} bytes)')
    print(f'Baked {target.name}: {target.stat().st_size} bytes')
PY

# Prove the baked FP32 model, matching voices and exact default production voice
# can synthesize valid 24 kHz audio without any model download.
RUN python - <<'PY'
import os
import numpy as np
import onnxruntime
from kokoro_onnx import Kokoro

options = onnxruntime.SessionOptions()
options.intra_op_num_threads = max(1, int(os.cpu_count() or 2))
options.inter_op_num_threads = 1
session = onnxruntime.InferenceSession(
    os.environ['RUNTIME_RESOURCE_A'],
    providers=['CPUExecutionProvider'],
    sess_options=options,
)
engine = Kokoro.from_session(session, os.environ['RUNTIME_RESOURCE_B'])
audio, sample_rate = engine.create(
    'Wacky Dramas ONNX runner validation.',
    voice='af_heart', speed=1.75, lang='en-us',
)
audio = np.asarray(audio, dtype=np.float32)
assert int(sample_rate) == 24000, sample_rate
assert audio.size > 0
assert np.all(np.isfinite(audio))
print(f'Kokoro ONNX FP32 offline asset validation passed: {audio.size} samples at {sample_rate} Hz')
PY

# Warm the PyTorch fallback model and default voice into a fixed cache path that
# is independent of HOME. GitHub job containers override HOME=/github/home.
RUN python - <<'PY'
from kokoro import KPipeline
pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
for _gs, _ps, _audio in pipeline('Wacky Dramas fallback warmup.', voice='af_heart', speed=1.75):
    break
print('PyTorch Kokoro fallback model and af_heart voice cache ready in fixed HF_HOME')
PY

# Cache the English Wav2Vec2 acoustic model in TORCH_HOME during the image
# build. Production caption alignment is therefore fully offline.
RUN python - <<'PY'
import torchaudio
bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
model = bundle.get_model()
model.eval()
print('Wav2Vec2 forced-alignment model cache ready')
PY

# From this layer onward production is intentionally Hugging Face offline.
# The build proves the PyTorch fallback cache still works without HTTP.
ENV HF_HUB_OFFLINE=1
RUN python - <<'PY'
from huggingface_hub import is_offline_mode
from kokoro import KPipeline
assert is_offline_mode(), 'HF offline mode must be active in the production image'
pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
for _gs, _ps, _audio in pipeline('Offline fallback validation.', voice='af_heart', speed=1.75):
    assert len(_audio) > 0
    break
else:
    raise SystemExit('PyTorch Kokoro offline validation produced no audio')
print('PyTorch Kokoro offline fallback validation passed')
PY

WORKDIR /__w/youtube-workflow/youtube-workflow
