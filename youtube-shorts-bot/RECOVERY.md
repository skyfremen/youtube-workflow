# Wacky Dramas private upload recovery

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

## Accepted migration proof

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

The live YouTube channel rename is user-managed and may be completed later. Recovery and upload ownership are pinned to the authenticated channel ID, not the display name.

## Operational entry point

For a new story, add exactly one new immutable request file under `content/requests/` in its own commit. The push-triggered **Wacky Dramas Ad-hoc Private Publish** workflow is the only Shorts publishing path and uploads PRIVATE only.

For recovery of an existing content ID, manually run **Wacky Dramas Ad-hoc Private Publish** with that `content_id` and `recovery_only=true`.
