# Wacky Dramas upload and recovery

The canonical Shorts architecture is request-driven, immutable, recovery-first, and fail-closed around YouTube insertion.

## Durable private state

- `content/requests/<content_id>.json` — immutable production request.
- `content/recovery/<content_id>/intent.json` — create-only upload intent.
- `content/recovery/<content_id>/upload.json` — create-only durable upload evidence.
- `content/recovery/index/<content_id>.json` — content-to-video reconciliation mapping.
- `content/results/<content_id>.json` — immutable verified-success receipt.

Request bytes are bound to the exact source commit that first added them. Production refuses to publish if the request differs from those immutable bytes.

## Current request/background contract

**Schema v7 is current for new Daily and Ad-hoc production.** It freezes two ordered, disjoint 2-3 clip background sequences using `concatenated_fit_to_short`. Each segment freezes logical background ID, start and duration. Playback rate is not frozen because exact speed depends on actual post-TTS production timing.

**Schema v6 remains executable for historical immutable recovery** using its original one-long-source `fit_to_short` semantics. **Schema v5 and schema v4 remain executable for historical immutable recovery** under their original contracts. Existing requests are never rewritten into v7.

There is only one background registry: `media-library/backgrounds.json`. Old pre-reset background definitions were destructively removed rather than retained in a hidden legacy registry. If a historical request references a deleted logical ID, recovery fails closed.

## Schema-v7 sequence recovery

Recovery reuses the exact immutable sequence and ranges from the request. It may resolve each logical asset to an allowed physical rendition according to the normal rendition policy, but may not choose different logical assets, reorder clips, modify ranges, or mix primary and backup.

```text
immutable request
  -> resolve frozen primary sequence
  -> TTS + exact complete visible timeline
  -> trim frozen ranges and concatenate once
  -> derived playback rate = total unique source duration / required duration
  -> validate 1.0x-2.5x bounds
  -> render with loop_mode=none / loop_count=0
  -> if primary execution fails, retry entire frozen backup sequence only
```

Insufficient unique source coverage fails closed. Recovery never loops, restarts, freezes the last frame or invents a third asset.

The verified receipt proves selected slot, ordered segment IDs/ranges, physical rendition evidence, per-clip hashes, total unique source duration, derived playback rate, treated duration and explicit zero-loop execution.

## Historical recovery

Schema v6 preserves its historical single long source range and runtime-derived rate. Schema v5 preserves its fixed segment/playback treatment. Schema v4 preserves its established execution behavior. All resolve against the current active registry; no compatibility parser restores deleted media definitions.

## Publication contract

Daily uses `publication.mode=scheduled`; upload remains private with the exact UTC `publishAt` until YouTube performs the scheduled public transition. Ad-hoc uses `publication.mode=immediate`, `publish_at=null`, and uploads Public immediately.

## Retry and idempotency contract

1. Resolve and verify original immutable request identity/source bytes.
2. Validate request schema, compatibility fingerprint and media contract.
3. Before expensive work or insertion, read existing receipt, upload evidence, reconciliation mapping and upload intent.
4. Reuse a verified existing receipt unchanged.
5. If durable upload evidence exists, restore that exact YouTube ID and never insert again.
6. If evidence is incomplete or ambiguous, reconcile boundedly and fail closed rather than authorizing a duplicate upload.
7. For a genuinely new request, create upload intent exclusively before YouTube `videos.insert`.
8. Persist upload evidence/mapping, verify exact channel/publication state, then create immutable result receipt.

The recovery watchdog reuses the exact content ID and immutable request. It never replans a replacement Short to recover execution failure.

## Analytics continuity

Verified schema-v7 receipts participate in the same private analytics enrichment and learning pipeline as supported historical receipts. Background sequence evidence is provenance; creative-performance learning still uses the planned story/title/attribute dimensions and measured YouTube performance.
