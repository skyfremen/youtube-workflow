# Wacky Dramas upload and recovery

The canonical Shorts architecture is request-driven, immutable, and fail-closed around YouTube insertion.

## Durable state

- `content/requests/<content_id>.json` is the immutable production request.
- `content/recovery/<content_id>/intent.json` is the create-only upload intent.
- `content/recovery/<content_id>/upload.json` is create-only durable upload evidence.
- `content/recovery/index/<content_id>.json` is the compact create-only content-to-video reconciliation mapping.
- `content/recovery/index/bootstrap.json` certifies that trusted pre-cutover private evidence was indexed before the indexed runtime is allowed to authorize fresh uploads.
- `content/results/<content_id>.json` is the immutable verified-success receipt.

The request bytes are bound to the exact commit that first added them. Production refuses to publish if the current request differs from those source bytes.

The per-content reconciliation mapping is deliberately small and private. It contains immutable request identity, the YouTube video ID, and expected channel ID. It is an additional reconciliation source, not a replacement for the upload-intent fence or full durable upload evidence.

## Publication contract

The current production path is the scheduled schema-v4 daily path. Schema v3 remains supported only for immutable historical/recovery compatibility. Each immutable request carries `publication.mode=scheduled`; the uploader requires `privacyStatus=private` plus the exact UTC `publishAt` from the request. YouTube owns the later public transition.

The canonical private entry point is `daily-production.yml` (**Daily Production**). It creates one opaque public-runtime dispatch; publication behavior is determined by the immutable request contract.

## Retry and idempotency contract

1. Resolve the original request-addition commit and verify the current request bytes against that Git blob.
2. Validate the request and shared media registry.
3. Before media download, TTS, rendering, or insertion, read any existing receipt, upload evidence, reconciliation mapping, and intent for the exact content ID.
4. If durable upload evidence exists, require any mapping to agree with it, repair a missing mapping idempotently, restore that exact YouTube video ID, and do not create another upload.
5. If a mapping exists but durable upload evidence is unexpectedly missing, perform a targeted lookup of that one mapped video ID. Whether it verifies or is unavailable, fresh insertion remains forbidden until the private evidence anomaly is reconciled.
6. If an intent exists without upload evidence or a mapping, use only the bounded post-intent YouTube reconciliation path described below. Failure to establish certainty is never permission to insert again.
7. For a genuinely new request, require the private index bootstrap certificate and confirm that intent, upload evidence, and the exact mapping are all absent. No channel-history scan is required on this normal path.
8. After a verified render exists, create the upload intent exclusively **before** calling YouTube `videos.insert`.
9. Persist durable upload evidence from the insert response or a reconciled recovery result.
10. Create the compact per-content mapping from the durable upload record. If this write fails, the already-durable upload record remains authoritative and a later recovery repairs the mapping without another insertion.
11. Verify the exact YouTube video, channel, publication state, and schedule by the known video ID.
12. Create the immutable result receipt only after verification passes. If the receipt already exists, verify its identity/evidence and reuse it unchanged.

A lost or ambiguous GitHub write acknowledgement is treated as unsafe. The code does not infer ownership of an upload intent from a later matching read and does not retry insertion optimistically.

## Critical crash window

The dangerous window remains:

```text
immutable upload intent written
        ↓
YouTube videos.insert succeeds
        ↓
runner dies before upload.json / index mapping is durable
```

The index cannot close this window because it may not have been written yet. Recovery therefore keeps the immutable intent as an irreversible fence and performs a bounded exceptional reconciliation against the authenticated channel.

The exceptional lookup starts at the newest uploads and is bounded by the intent creation time (with a small clock-skew allowance) and a fixed maximum of 250 observed uploads. Matching requires the deterministic marker plus the immutable title, description, category, and authenticated channel. Multiple matches or conflicting metadata fail closed. If the fixed bound is exhausted before certainty is reached, recovery fails closed and the intent continues to prohibit `videos.insert`.

This exceptional bounded lookup is not used for ordinary new uploads or ordinary recovery when private upload evidence/mapping already exists.

## Reconciliation index and bootstrap

`recovery/reconciliation_index.py` reconstructs the private index from existing trusted `content/recovery/*/upload.json` records and verified `content/results/*.json` receipts. It cross-checks duplicate evidence for the same content ID and refuses conflicts.

The migration is safe to rerun:

- existing identical per-content mappings are reused;
- missing mappings can be created;
- conflicting mappings are never overwritten;
- an existing valid bootstrap marker is retained;
- newly accumulated trusted records can be indexed without rewriting the original cutover certificate.

The initial bootstrap does not query YouTube when the trusted private evidence already contains the needed content/video relationships. The public runtime refuses fresh insertion if the bootstrap certificate is missing or invalid.

Because mappings are one file per content ID rather than one shared JSON dictionary, concurrent different Shorts do not race by rewriting the same index object. GitHub create-only semantics continue to protect same-content conflicts.

## Reruns

Manual recovery uses `daily-production.yml` `workflow_dispatch` with one or more existing immutable content IDs. The private workflow writes an immutable recovery manifest and sends only its opaque batch ID, exact source SHA and compatibility fingerprint to the public runtime. The batch processes each content ID through the same recovery-first publisher. Per-video failures are isolated so the rest of a valid batch can continue, but an individual failed request never bypasses its durable intent, mapping, upload record, or receipt rules.

## Scheduled-slot guard

For fresh scheduled generation, the public runtime's publication pipeline skips new expensive work when the immutable slot is already past or is within the configured generation buffer. Recovery is attempted before this guard, so an already-uploaded scheduled video can still be reconciled and verified.

The planner additionally avoids creating same-day catch-up slots that are too close to the current time. These are separate protections: planning chooses viable slots; publication guards prevent stale immutable slots from causing late generation.

## Duplicate recovery marker

`workflow_common.marker_tag(content_id)` derives a deterministic non-viewer-facing YouTube tag. The shared upload contract creates it. Normal duplicate resolution now uses the private per-content mapping and targeted known-video verification instead of enumerating channel history.

The marker remains essential for the exceptional post-intent crash-window lookup. It must not be placed in the public description. Semantic YouTube tags and visible hashtags remain distinct from the hidden recovery marker.

## Verification and receipt requirements

A receipt cannot be finalized unless all of the following agree with the immutable request and durable upload evidence:

- YouTube video ID and authenticated channel.
- Scheduled publication state, including exact `publishAt`.
- Verified render identity and SHA.
- **1080×1920** resolution, 30 fps, H.264 High video, yuv420p/BT.709, one AAC-LC narration stream at 48 kHz.
- Kokoro narration using the request's frozen voice/speed contract.
- Primary or backup background selected from the request and recorded with its rendition/provenance.
- Workflow/source-commit provenance.

The receipt carries the same supported schema version as its immutable request. The receipt itself is create-only. A rerun may reuse an existing verified receipt but may not mutate it.

## Operator recovery

For a scheduled daily content ID, manually run `daily-production.yml` using `workflow_dispatch` with the existing content ID or comma-separated content IDs. Do not create replacement requests merely to retry a failed workflow.

If recovery reports conflicting videos, mismatched evidence, an indexed video that is unavailable, an intent whose bounded recovery window cannot establish certainty, or any other ambiguous state, stop automated insertion and reconcile the durable GitHub/YouTube evidence. Never delete an intent, edit an immutable request/receipt/mapping, or add a force-reupload path to clear ambiguity.

## Complexity

Previous normal behavior enumerated the uploads playlist and then fetched video metadata in batches until channel history ended or the 5,000-video safety ceiling was hit. That made fresh authorization O(channel history) and eventually made absence impossible to establish beyond the bound.

After cutover, the normal recovery and duplicate-prevention path is O(1) private state lookup plus targeted verification of a known video ID when needed. Channel growth to 5,000, 10,000, 50,000 or more uploads does not increase normal lookup work. Only the exceptional unresolved-intent crash window can enumerate uploads, and that path has the fixed 250-video bound described above.

## Safe verification

Private planning/state changes should use private `dry-run.yml`; runtime changes should use the public repository's `dry-run.yml`. Scheduled observation is isolated in public `observe.yml`. A production YouTube upload is not part of cleanup verification.
