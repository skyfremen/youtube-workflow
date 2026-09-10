# Wacky Dramas YouTube Workflow

This repository contains the canonical **Wacky Dramas** Shorts production system. The active implementation lives under `youtube-shorts-bot/`; GitHub Actions orchestration lives under `.github/workflows/`.

## Canonical architecture

Application modules under `youtube-shorts-bot/` are grouped by responsibility into `planning/`, `media/`, `rendering/`, `publishing/`, `validation/`, `common/`, and `analytics/`; durable runtime data remains in its existing top-level locations.

The production path is request-driven and append-only:

1. The daily planner generates a large premise pool, applies deterministic scoring/diversity policy, selects up to 24 winners, and creates immutable schema-v3 requests with hourly `Asia/Singapore` publication slots.
2. Requests are validated before expensive work.
3. Primary/backup logical background IDs are resolved through the verified media registry, with rendition preflight and controlled fallback.
4. Kokoro generates narration using the approved voice/speed contract; captions are aligned and the video is rendered at 720×1280 / 30 fps / H.264 + AAC.
5. Upload recovery is checked before generation or insertion. A durable upload intent is an irreversible retry fence.
6. Scheduled daily requests upload private with the immutable YouTube `publishAt` value.
7. YouTube state is verified through the authenticated owner API.
8. A success receipt is written only after verification succeeds and is immutable thereafter.
9. Scheduled daily receipts feed age-matched analytics and future candidate scoring.

Canonical durable paths:

- `youtube-shorts-bot/content/requests/<content_id>.json` — immutable production request.
- `youtube-shorts-bot/content/recovery/<content_id>/intent.json` — create-only upload intent.
- `youtube-shorts-bot/content/recovery/<content_id>/upload.json` — create-only durable upload evidence.
- `youtube-shorts-bot/content/results/<content_id>.json` — immutable verified success receipt.
- `youtube-shorts-bot/content/planning/YYYY-MM-DD.json` — immutable daily planning audit when a daily plan is created.
- `youtube-shorts-bot/content/background-sourcing/YYYY-MM-DD.json` — optional immutable sourcing manifest for newly selected Pexels backgrounds.

Never edit or delete an existing production JSON in those immutable paths during ordinary operation.

## Active workflows

The supported workflow set is deliberately small:

| Workflow | Purpose |
| --- | --- |
| `daily-production.yml` | Processes a daily selected batch, isolates per-video failures, preserves shared-state safety, and delegates hourly release timing to YouTube scheduling. |
| `analytics-collection.yml` | Collects age-matched Shorts analytics and updates the learning snapshot/model. |
| `background-management.yml` | Maintains official Pexels rendition metadata in the verified background registry. |
| `build-image.yml` | Builds the canonical production GHCR runner image from `youtube-shorts-bot/Dockerfile`. |
| `dry-run.yml` | Static, unit, contract, planning-funnel, media-registry, workflow-safety, and zero-production-side-effect checks. |

The dry-run workflow also asserts the exact supported workflow and planner surface and prevents retired project roots or removed production entry points from reappearing.

## Publication and recovery invariants

- One story maps to one immutable `content_id`.
- The current channel identity is **Wacky Dramas / @WACKYDRAMAS** and production ownership is additionally pinned to the expected YouTube channel ID in code.
- Schema-v3 scheduled uploads must enter YouTube as private and carry the exact immutable `publishAt`.
- The deterministic recovery marker is stored in non-viewer-facing YouTube tags, not in the description.
- If a durable intent exists, a missing/temporarily unobservable video is never permission to upload again.
- Result receipts are created only after exact YouTube state, request identity, render, background, and provenance verification.

See `youtube-shorts-bot/docs/RECOVERY.md` for operator recovery details and `youtube-shorts-bot/docs/SYSTEM_OVERVIEW.md` for the planning/analytics design.

## Development and verification

The canonical lightweight validation baseline is encoded in `.github/workflows/dry-run.yml`. It compiles production Python, runs `unittest` discovery, validates the media registry, exercises the scheduled request and 120-premise planning acceptance paths, checks renderer constants, enforces workflow safety and naming contracts, and proves the dry run creates no TTS/render/upload side effects.

A production upload is **not** required to validate repository cleanup or ordinary code changes. Do not use public YouTube publishing as a cleanup test.

## Repository scope

Retired Wacky Insights planner/queue/series/music/publishing architecture, the former `youtube-story-bot` prototype, and the former single-story production entry point are not part of the supported tree. Do not restore them. Historical or experimental branches with unique unmerged work must be reviewed before deletion rather than treated as disposable solely because of age or naming.
