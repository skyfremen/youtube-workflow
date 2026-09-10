# Wacky Dramas upload and recovery

The canonical Shorts architecture is request-driven, immutable, and fail-closed around YouTube insertion.

## Durable state

- `content/requests/<content_id>.json` is the immutable production request.
- `content/recovery/<content_id>/intent.json` is the create-only upload intent.
- `content/recovery/<content_id>/upload.json` is create-only durable upload evidence.
- `content/results/<content_id>.json` is the immutable verified-success receipt.

The request bytes are bound to the exact commit that first added them. Production refuses to publish if the current request differs from those source bytes.

## Publication modes

Two current publication modes share the same recovery guarantees:

- **Ad-hoc request:** no `publication` object. The uploader requires an immediate `privacyStatus=public` body and no `publishAt`.
- **Daily-growth schema-v3 request:** immutable `publication.mode=scheduled`. The uploader requires `privacyStatus=private` plus the exact UTC `publishAt` from the request. YouTube owns the later public transition.

The workflow file `single-production.yml` retains a historical filename, but its current workflow name and production behavior are **Wacky Dramas Ad-hoc Public Publish**. The filename is not a publication contract.

## Retry and idempotency contract

1. Resolve the original request-addition commit and verify the current request bytes against that Git blob.
2. Validate the request and shared media registry.
3. Before media download, TTS, rendering, or insertion, read any existing immutable receipt and durable upload evidence.
4. If durable upload evidence exists, restore that exact YouTube video ID and do not create another upload.
5. If an intent exists without a durable upload record, search the authenticated channel for the deterministic recovery marker. If the upload cannot be reconciled unambiguously, fail closed; absence is never permission to insert again.
6. For a genuinely new request only, validate the exact upload contract and confirm no matching upload exists.
7. After a verified render exists, create the upload intent exclusively before calling YouTube `videos.insert`.
8. Persist durable upload evidence from the insert response or reconciled recovery result.
9. Verify the exact YouTube video, channel, publication state, and schedule where applicable.
10. Create the immutable result receipt only after verification passes. If the receipt already exists, verify its identity/evidence and reuse it unchanged.

A lost or ambiguous GitHub write acknowledgement is treated as unsafe. The code does not infer ownership of an upload intent from a later matching read and does not retry insertion optimistically.

## Reruns

Ad-hoc GitHub Actions reruns are recovery-only. Manual recovery also uses `recovery_only=true`; this forbids a new upload when no durable record can be reconciled.

The daily batch processes each immutable content ID through the same recovery-first publisher. Per-video failures are isolated so the rest of a valid batch can continue, but an individual failed request never bypasses its durable intent or receipt rules.

## Scheduled-slot guard

For fresh scheduled generation, `publish.py` skips new expensive work when the immutable slot is already past or is within the configured 10-minute generation buffer. Recovery is attempted before this guard, so an already-uploaded scheduled video can still be reconciled and verified.

The planner additionally avoids creating same-day catch-up slots that are too close to the current time. These are separate protections: planning chooses viable slots; publication guards prevent stale immutable slots from causing late generation.

## Duplicate recovery marker

`workflow_common.marker_tag(content_id)` derives a deterministic non-viewer-facing YouTube tag. `upload.py` searches the authenticated channel uploads for that marker when durable intent recovery requires YouTube reconciliation.

The recovery marker must not be placed in the public description. Semantic YouTube tags and visible hashtags remain distinct from the hidden recovery marker.

## Verification and receipt requirements

A receipt cannot be finalized unless all of the following agree with the immutable request and durable upload evidence:

- YouTube video ID and authenticated channel.
- Immediate-public or scheduled publication state, including exact `publishAt` for scheduled requests.
- Verified render identity and SHA.
- 720×1280 resolution, 30 fps, H.264 video, one AAC narration stream.
- Kokoro narration using the request voice/speed contract.
- Primary or backup background selected from the request and recorded with its rendition/provenance.
- Workflow/source-commit provenance.

The receipt itself is create-only. A rerun may reuse an existing verified receipt but may not mutate it.

## Operator recovery

For an existing ad-hoc content ID, manually run **Wacky Dramas Ad-hoc Public Publish** with:

- `content_id=<existing immutable content_id>`
- `recovery_only=true`
- `render_preview=false` unless a separate debug preview is explicitly needed

For a daily-growth content ID, use `daily-production.yml` `workflow_dispatch` with the existing content ID(s). Do not create replacement requests merely to retry a failed workflow.

If recovery reports conflicting videos, mismatched evidence, an intent with no observable video, or any other ambiguous state, stop automated insertion and reconcile the durable GitHub/YouTube evidence. Never delete an intent, edit an immutable request/receipt, or add a force-reupload path to clear ambiguity.

## Safe verification

Repository cleanup and code changes should use `dry-run.yml` and its unit/contract checks. A public YouTube upload is not part of cleanup verification. Debug rendering may be used only through the explicit test/preview path that does not upload.
