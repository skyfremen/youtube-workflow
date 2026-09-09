# Wacky Dramas private upload and recovery

The canonical Shorts architecture is request-driven and immutable:

- `content/requests/<content_id>.json` is the immutable request.
- `content/results/<content_id>.json` is the immutable verified-success receipt.
- `content/recovery/<content_id>/intent.json` and `upload.json` are durable append-only upload evidence.

There is no queue, series, music, daily-plan, `latest.json`, or scheduled-publish path in the canonical Wacky Dramas publisher.

## Retry contract

1. Resolve the original request-addition commit and verify that the current request bytes still match that Git blob.
2. Before downloading media or rendering, read any canonical receipt and durable upload record from GitHub.
3. If a durable video ID already exists, recover that exact video and set `upload_required=false`.
4. For a genuinely new request only, create exclusive durable upload intent before calling YouTube `videos.insert`.
5. Persist the returned YouTube video ID to durable recovery evidence before final verification.
6. Verify through the authenticated owner API that the exact video is PRIVATE, processed, associated with the immutable request, and has no `publishAt`.
7. Create the immutable result receipt only after verification passes. If the receipt already exists, verify it and reuse its bytes unchanged.
8. GitHub Actions reruns (`GITHUB_RUN_ATTEMPT > 1`) are forced into `--recovery-only` mode. A rerun is therefore never permission for a fresh upload.

Never delete an intent to clear ambiguity, never add a force-reupload flag, and never infer that a failed workflow means no YouTube upload occurred. Durable evidence must be reconciled instead.

## Accepted visual and recovery proof

The current card-first visual sequence was accepted using content ID `wd-20260908T180410-card-first-10s-b72d4e`.

- Canonical private video: `CdpjHVq7sj8`
- Acceptance run: `34260939023`, attempt 1
- Actual video duration: `10.066667` seconds
- Render: 720x1280, 30 fps, H.264 + one AAC narration stream
- Card title narration: `1.925` seconds
- Card transition: `0.300` seconds
- Story/subtitles start: `2.225` seconds
- Privacy: PRIVATE
- `publishAt`: absent
- Receipt blob: `f9b850eb8135b3863fcb0e20cad94e347a35e79b`

The same run was rerun as attempt 2. Recovery resolved `CdpjHVq7sj8`, reported `upload_required=false`, skipped background resolution, TTS/render and upload, reverified the existing private video, and reused the exact receipt blob unchanged. This proves same-content idempotency without another upload.

## Accepted full-length production proof

The production-duration path was accepted using content ID `wd-20260908T190630-roommate-rent-p4n8vx` after correcting the long-word caption-fit issue discovered by the preceding failed request.

- Canonical private video: `ntjLVNyPyus`
- Acceptance run: `34267054783`, attempt 1
- Actual video duration: `142.333333` seconds
- Total narration: `141.975` seconds
- Card title narration: `1.675` seconds
- Card transition: `0.300` seconds
- Story narration start: `1.975` seconds
- Story narration: `140.000` seconds
- Render: 720x1280, 30 fps, H.264 + one AAC narration stream
- Audio source: narration only
- Background: `satisfying-001` primary, `satisfying-002` backup
- Kokoro: `af_heart` at `1.75x`
- Test mode: false
- Privacy: PRIVATE
- YouTube processing: processed
- `publishAt`: absent
- Recovery marker and immutable description marker: verified

This proves the normal production path can render, upload, verify, and receipt a story inside the 120–175 second target while staying below the 178-second ceiling.

## Native 720p layout contract

The Shorts renderer now uses native fixed 720x1280 UI coordinates rather than scaling a 1080x1920 design space. Caption geometry is explicit: 85px left margin, 85px right margin, and 550px usable text width, with equal ASS margins so the subtitle block remains horizontally centered. Other card, branding, icon, pill, and motion coordinates are also stored directly in native 720p pixels.

The live YouTube channel rename is user-managed and may be completed later. Recovery and upload ownership are pinned to the authenticated channel ID, not the display name.

## Historical incomplete acceptance requests

`wd-20260909T010256-overtime-email-e4b91c` is an immutable historical acceptance request with no verified success receipt. Its earlier private upload was not accepted because recovery-marker verification failed. Keep the request unchanged as audit evidence; current recovery guards do not permit it to authorize a fresh upload.

`wd-20260908T185000-roommate-rent-k7m4qz` is an immutable full-length acceptance request that failed during caption layout before upload intent or YouTube insert. The failure exposed a long-word caption-fit bug, which was corrected in the renderer with adaptive per-caption font sizing and regression coverage. Keep the failed request unchanged; use a new content ID for the replacement production proof.

## Operational entry point

For a new story, add exactly one new immutable request file under `content/requests/` in its own commit. The push-triggered **Wacky Dramas Ad-hoc Private Publish** workflow is the only Shorts publishing path and uploads PRIVATE only.

## Background rendition migration

The schema-v3 Pexels migration populated official `video_files` metadata for 17 of the 30 existing logical backgrounds. The remaining 13 stay registered for historical generic-fallback compatibility because Pexels exposes no rendition large enough to crop-fill 720×1280 without upscaling. Planning excludes those generic-only assets from new requests; it does not change their stable logical IDs or provenance.

For recovery of an existing content ID, manually run **Wacky Dramas Ad-hoc Private Publish** with that `content_id` and `recovery_only=true`.
