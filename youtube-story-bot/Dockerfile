FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl ffmpeg fonts-dejavu-core git espeak-ng libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY youtube-story-bot/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /__w/youtube-workflow/youtube-workflow
