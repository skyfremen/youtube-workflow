# Wacky Dramas upload and recovery

The canonical Shorts architecture is request-driven, immutable, recovery-first, and fail-closed around YouTube insertion.

## Durable private state

- `content/requests/<content_id>.json` — immutable production request.
- `content/recovery/<content_id>/intent.json` — create-only upload intent.
- `content/recovery/<content_id>/upload.json` — create-only durable upload evidence.
- `content/recovery/index/<content_id>.json` — compact content-to-video reconciliation mapping.
- `content/recovery/index/bootstrap.json` — cutover/index bootstrap certificate.
- `content/results/<content_id>.json` — immutable verified-success receipt.

Request bytes are bound to the exact source commit that first added them. Production refuses to publish if the request differs from those immutable bytes.

## Current request/background contract

**Schema v6 is current for new Daily and Ad-hoc production.** Schema v6 freezes the story/narration/publication contract, the logical primary/backup backgrounds, and one long continuous temporal range for each slot. It deliberately does **not** freeze playback rate because exact speed depends on actual post-TTS production timing.

**Schema v5 and schema v4 remain executable only for historical immutable recovery.** Existing v5 requests continue to use their original fixed segment/playback treatment semantics; they are never rewritten into v6.

There is only one background registry: `media-library/backgrounds.json`. The old pre-reset background definitions were destructively removed and are not retained in a legacy recovery snapshot. Historical v4/v5 recovery therefore resolves logical background IDs against the current active registry only. If an old request names a deleted background, recovery fails closed instead of restoring, importing, or silently substituting the old asset.

## Schema-v6 continuous background recovery

For v6, recovery reuses the exact immutable logical slot and continuous source range from the original request. The runtime may resolve the same logical slot to an allowed physical rendition according to the normal rendition policy, but it may not select a different logical asset or temporal range.

Execution order is:

```text
immutable request
  -> resolve requested primary/backup physical rendition
  -> TTS + actual complete visible timeline
  -> required moving-background duration
  -> derived playback rate = selected unique range / required duration
  -> validate configured speed bounds
  -> prepare one continuous background
  -> render once with normal loop count = 0
```

A rerun may derive the playback rate again from the actual deterministic timeline, but the underlying selected range remains immutable. Insufficient source coverage fails closed; recovery must never solve it by looping, freezing a final frame, restarting the source, or substituting an unrelated third asset.

The v6 completion receipt proves the selected logical asset/rendition, immutable range, actual required duration, derived playback rate, treated duration, source/treated evidence where available, and zero normal loops.

## Historical schema-v5/v4 recovery

Historical v5 requests retain their original frozen segment/playback treatment semantics. Historical v4 requests retain their established execution semantics. These compatibility parsers do not provide a separate background library.

If the request's background ID is present in current `backgrounds.json`, normal validation/resolution may proceed. If that ID was part of the deleted pre-reset library and is absent now, recovery is intentionally terminal/fail-closed for that request. No recovery path may recreate the deleted library automatically.

## Publication contract

Daily requests use `publication.mode=scheduled`; upload requires `privacyStatus=private` plus the exact UTC `publishAt` from the immutable request. YouTube owns the later public transition.

Ad-hoc requests use `publication.mode=immediate`, `publish_at=null`, and upload Public immediately.

The private Daily entry point is `daily-production.yml`. Ad-hoc uses its dedicated private workflow and the public single-item execution path. Publication behavior comes from the immutable request, not workflow-side creative repair.

## Retry and idempotency contract

1. Resolve and verify the original immutable request identity/source bytes.
2. Validate request schema, compatibility fingerprint, and background resolution against the current active registry.
3. Before media download, TTS, rendering, or insertion, read any existing receipt, upload evidence, reconciliation mapping, and upload intent for the exact content ID.
4. If a verified receipt already exists, verify identity/evidence and reuse it unchanged.
5. If durable upload evidence exists, require any mapping to agree, restore that exact YouTube video ID, and never create another upload.
6. If a mapping exists but upload evidence is unexpectedly missing, perform only targeted known-video reconciliation; fresh insertion remains forbidden until the anomaly is reconciled.
7. If intent exists without upload evidence/mapping, use the bounded post-intent YouTube reconciliation path. Uncertainty is never permission to insert again.
8. For a genuinely new request, require the private index bootstrap certificate and confirm intent/upload/mapping are absent.
9. After a verified render exists, create upload intent exclusively **before** calling YouTube `videos.insert`.
10. Persist upload evidence and the compact per-content mapping.
11. Verify exact YouTube video, channel, publication state, and schedule/mode.
12. Create the immutable result receipt only after all verification passes.

A lost or ambiguous GitHub write acknowledgement is unsafe. The system never infers permission for another insertion from absence of a later record.

## Critical crash window

The dangerous window remains:

```text
immutable upload intent written
        ↓
YouTube videos.insert succeeds
        ↓
runner dies before upload.json / index mapping is durable
```

The immutable intent becomes an irreversible duplicate-upload fence. Recovery performs bounded exceptional reconciliation against the authenticated channel. Multiple matches, conflicting metadata, or exhaustion of the bounded search fail closed.

## Reconciliation index

`recovery/reconciliation_index.py` reconstructs per-content mappings from trusted upload evidence and verified receipts. It is idempotent:

- identical mappings are reused;
- missing mappings may be created;
- conflicting mappings are never overwritten;
- a valid bootstrap marker is retained;
- new trusted records may be indexed without rewriting the original cutover certificate.

Because mappings are one file per content ID, concurrent different Shorts do not race by rewriting one shared dictionary.

## Reruns

Manual Daily recovery uses `daily-production.yml` `workflow_dispatch` with existing immutable content IDs. Private recovery sends only the opaque batch identity, exact source SHA, and compatibility fingerprint to public runtime.

Per-video failures remain isolated, but an individual failed request never bypasses its durable intent, mapping, upload record, receipt, or immutable background contract.

GitHub partial reruns may reconstruct current-attempt START evidence only when prior attempt evidence and immutable dispatch identity agree exactly. Attempt 1 still requires the explicit workflow Start step; stale evidence is never accepted as current-attempt proof.

## Scheduled-slot guard

Fresh scheduled generation skips expensive work when the immutable publication slot is already past or inside the configured generation buffer. Recovery is attempted before this guard so an already-uploaded scheduled video can still be reconciled and verified.

Planning separately avoids creating same-day catch-up slots that are too close to execution time.

## Verification and receipt requirements

A receipt cannot finalize unless all applicable evidence agrees with the immutable request and durable upload evidence, including:

- YouTube video ID and authenticated channel;
- exact scheduled `publishAt` or immediate-public state;
- verified render identity/evidence;
- **1080×1920**, 30 fps, H.264 High, yuv420p/BT.709, one AAC-LC narration stream at 48 kHz;
- Kokoro narration using the request voice/speed contract;
- primary or backup logical background from the immutable request;
- physical rendition/provenance;
- v6 exact continuous range + derived timing + zero-loop evidence, or historical v5 exact fixed treatment evidence when its background still exists;
- workflow/source-commit provenance.

Receipts are create-only. A rerun may reuse an existing verified receipt but may not mutate it.

## Recovery principle

Recovery resumes **already-promoted immutable production**. It does not revisit unused ranked-pool candidates, rerank creative work, choose new backgrounds, restore deleted old backgrounds, or alter publication contracts after production has begun.
