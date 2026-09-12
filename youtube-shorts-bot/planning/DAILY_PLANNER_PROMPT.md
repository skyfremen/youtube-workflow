# Wacky Dramas — Daily Planner (schema v5 overlay)

This is the canonical Daily planner entry point.

Read `planning/DAILY_PLANNER_V4_BASE.md` **in full** first and preserve all of its business, creative, analytics, metadata, scheduling, safety, deterministic-runner, publication, provenance, recovery, and background-selection rules except where this overlay explicitly supersedes schema-v4/background-treatment statements.

Repository code remains the source of truth. Before planning, inspect the current checked-out implementations of `validation/validate_content.py`, `common/runtime_contract.py`, `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, `media-library/backgrounds.json`, and the current production/dry-run workflows. Do not blindly trust either prompt when executable code has moved forward.

## Schema-v5 override

New immutable production requests must use **schema v5**. Schema v4 remains readable only for migration/recovery of requests that already exist; do not author a new v4 request.

The v5 `visual` object contains exactly:

- `background_primary_id`
- `background_backup_id`
- `background_primary_treatment`
- `background_backup_treatment`

Each treatment contains exactly:

- `segment_start_seconds`
- `segment_duration_seconds` — number or `null` for full-source treatment
- `playback_rate`

The validator and compatibility fingerprint define the authoritative numeric bounds. At the time of this overlay, playback is bounded to 1.0×–2.0×. Never manually broaden those bounds.

## Mandatory treatment allocation

Logical asset selection and physical rendition resolution remain separate.

For each final winner:

1. Select the primary and backup logical asset using the retention-first private selector and its existing topic-aware fallback chain.
2. Read private immutable successful receipts, including scheduled and immediate-public Ad-hoc successes.
3. Run the canonical private treatment allocator for the selected pair. Do not manually approximate its choice:

```bash
PYTHONPATH=youtube-shorts-bot python youtube-shorts-bot/media/background_treatment.py \
  --primary-id <PRIMARY_ID> \
  --backup-id <BACKUP_ID> \
  --planned-json /tmp/wacky-dramas-planned-background-treatments.json
```

`--planned-json` is optional for the first item. For later items in the same Daily plan, it must contain the treatments already reserved earlier in this planning run, represented with their associated logical asset IDs as accepted by the current allocator.

4. Consume the allocator's **actual returned** `background_primary_treatment` and `background_backup_treatment` and freeze them into the immutable request.
5. Append both reservations to the in-progress private `planned_treatments` scratch list before allocating the next winner.
6. Validate the complete request through `validation/validate_content.py` and the existing exact upload-payload validation before commit.

If the allocator cannot run successfully or returns an invalid treatment, fail closed. Do not invent segment boundaries or speed values to continue planning.

## Segment reuse policy

Persistent segment/playback history comes only from private immutable successful receipts. Do not add mutable usage fields to the logical registry. Do not create a public history ledger.

For sufficiently long clips, prefer materially different temporal ranges and avoid recent/planned overlap according to `media/background_treatment.py`. Short clips and older assets without trustworthy duration metadata may use the allocator's backward-compatible full-source treatment.

Playback speed is a treatment, not a uniqueness loophole. A different rate does not make an otherwise repeated segment meaningfully new. Segment diversity and logical-asset diversity remain primary.

Use category/asset-aware speed bounds from the allocator. Do not universally accelerate every clip, and do not choose a faster rate merely for randomness.

## Daily coordination

Continue carrying the retention selector's ephemeral `planned_asset_ids` / `planned_categories` (or their current equivalents) across the day's winners.

Additionally carry ephemeral `planned_treatments` across the same planning run. These are private planning scratch inputs only; they are not a persistent public state store.

The intended private allocation sequence is therefore:

```text
winner
  -> retention-first logical primary/backup selection
  -> asset/category anti-repetition
  -> canonical segment/playback allocation
  -> append planned asset/category/treatment scratch state
  -> immutable schema-v5 request
```

## Public runtime boundary

Do not move media probing, downloading, physical rendition selection, normalization, cropping, transcoding, FFmpeg treatment, rendering, or upload work into the private planner.

The public runtime receives the frozen logical IDs and treatment pair. It remains responsible for:

```text
logical asset validation
  -> smallest post-crop-sufficient physical rendition
  -> normalized-cache lookup
  -> download only if required
  -> normalize once to production size/FPS if required
  -> apply the frozen segment/playback treatment to the normalized job-local input
  -> render
```

The normalized physical cache remains treatment-agnostic. Different segment/speed treatments must not force repeated provider downloads or contaminate persistent creative history.

## Staged compatibility

The private/public compatibility hash fingerprints schema v5 treatment keys and bounds. Existing v4 requests may continue through the public runtime only through the explicitly tested staged compatibility path. New Daily requests use the current v5 hash.

Do not weaken exact source-SHA validation, dispatch/start evidence, upload intent, duplicate-upload protection, recovery, idempotency, completion receipts, public/private state ownership, dry-run boundaries, or least-privilege behavior.

## Final Daily request check

Before committing any Daily request, confirm:

- schema version is 5;
- primary and backup IDs are distinct registered logical assets;
- both treatment objects came from the canonical allocator;
- long-source segments do not knowingly repeat recent/planned ranges when alternatives exist;
- playback rates are within canonical asset/category/global bounds;
- same-day scratch history was supplied for later winners;
- no mutable usage/segment/playback ledger was added to `production-runtime`;
- physical rendition selection is still smallest-sufficient **after crop**;
- no provider original/UHD shortcut was introduced;
- normalized-cache reuse remains possible across different treatments;
- all remaining rules from `DAILY_PLANNER_V4_BASE.md` continue to apply unless explicitly superseded above.
