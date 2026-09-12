# Wacky Dramas System Overview

## Purpose

The canonical Shorts system uses a competitive planning funnel: generate broadly, reject weak/duplicate ideas cheaply, fully author a ranked reserve pool, mechanically validate the frozen AI-authored candidates, promote only the highest-ranked valid winners, then feed comparable public performance back into future planning.

The business objective remains aggressive subscriber and qualified-view growth, including **1,000 subscribers** and **10 million qualified public Shorts views within a rolling 90-day window**.

A normal Daily plan publishes exactly **24 Shorts**, one per hour in **Asia/Singapore**. ChatGPT authors **36** complete ranked candidates so candidate-specific validation failures can be absorbed without weakening the exact-24 production contract. Ad-hoc planning authors **5** complete ranked candidates and promotes the first mechanically valid one.

## Architecture

```text
ChatGPT / Work
  -> inspect current private repo rules/config/analytics/history/background registry
  -> generate broad creative candidates
  -> hard duplicate/quality/safety rejection
  -> editorial scoring + analytics evidence + diversity reasoning
  -> fully author complete production candidates
  -> choose exact primary/backup logical backgrounds
  -> perform planning-time background audit reasoning
  -> choose frozen segment/playback treatments
  -> freeze final AI rank order

Daily:
  -> write one temporary exact-byte 36-candidate draft
  -> execute the live planner contract + daily_precommit (36/36 required)
  -> commit those exact validated bytes as one immutable 36-candidate attempt pool
  -> daily-production.yml
       -> private promotion preflight
       -> mechanically validate candidates in frozen rank order
       -> promote first target_count valid candidates
       -> materialize canonical plan + requests locally
       -> create local [daily production] commit
       -> rebase latest main
       -> recheck catch-up timing + final canonical validation
       -> push only validated immutable production state
       -> dispatch public run.yml

Ad-hoc:
  -> write one temporary exact-byte 5-candidate draft
  -> execute the live planner contract + adhoc_precommit (5/5 required)
  -> commit those exact validated bytes as one immutable 5-candidate pool
  -> adhoc-production.yml
       -> private promotion preflight
       -> mechanically validate candidates in frozen rank order
       -> promote first valid candidate locally
       -> create local [adhoc production] request commit
       -> rebase latest main
       -> final schema/registry/immediate-public validation
       -> scheduled-date uniqueness recheck when planning_mode=scheduled_daily
       -> push only validated immutable request
       -> dispatch public single.yml

Public runtime:
  -> fetch exact promoted private state by opaque batch/source contract
  -> public execution-readiness preflight
  -> resolve/normalize physical background
  -> execute frozen segment/playback treatment
  -> TTS + alignment + captions + render
  -> upload exactly once according to immutable publication mode
  -> verify exact YouTube state
  -> persist private immutable evidence/receipt
  -> public observations feed private analytics learning
```

There is no `planner-execution.yml` bridge. ChatGPT owns planning/background/treatment decisions directly. Private code is an independent validator/promotion gate; public runtime is the heavy stateless executor.

## Schema and compatibility

Schema v5 is current for newly promoted Daily and Ad-hoc requests. It freezes story/narration/publication plus logical primary/backup backgrounds and one immutable treatment for each slot.

Schema v4 remains executable only for historical immutable recovery. Older schema-v3 receipts remain analytics/history compatibility where explicitly supported.

The private/public compatibility fingerprint covers current request/treatment contract semantics. Public execution still validates exact source revision and compatibility before expensive work.

## Planning competition and reserve pools

The planner begins with a broad premise pool (normally at least 120 ideas), then applies semantic hard rejection, duplicate reasoning, analytics/editorial evidence, truthful title competition and diversity judgment before fully authoring the final reserve set.

For new ranked pools, **ChatGPT / Work owns the final editorial decision and rank**. `planning_config.py`, `planning_engine.py`, analytics code, media policy and validators remain rule/specification/regression sources, but deterministic code must not silently replace ChatGPT's final winner order.

The handoff has two distinct immutable layers:

1. **ranked planning attempt** — larger than the production target and AI-authored;
2. **canonical production state** — mechanically materialized from first valid ranked candidates after hard validation.

For normal Daily the pool has 36 and target 24. Ad-hoc has 5 and target 1. Before either pool becomes immutable, ChatGPT must execute the corresponding precommit validator against the exact temporary bytes and current rules HEAD: newly authored Daily pools require 36/36 valid candidates and Ad-hoc pools require 5/5.

Promotion still independently validates every committed candidate as defense in depth. If repository state or time-dependent facts change after precommit, a later-invalid candidate is skipped, never repaired, and later candidates retain original rank. If fewer than the target pass, the attempt fails closed.

## Daily attempt/retry contract

Daily attempts live at:

`content/planning-pools/daily/YYYY-MM-DD/dp-<attempt-id>.json`

Suggested stable sequential IDs are `dp-YYYYMMDD-a01`, `a02`, etc.

A failed attempt remains immutable. Mechanical authoring/contract mistakes should be caught by the mandatory precommit gate before an attempt enters history; a committed attempt can still fail if repository state, timing or other independently validated facts change after precommit. While no canonical `content/planning/YYYY-MM-DD.json` exists, ChatGPT may author a new corrected/replenished attempt under a new ID. Once a canonical plan exists, no further pool attempt is permitted for that date; production problems use recovery of the promoted requests.

Each normal attempt still contains exactly 36 complete production-quality candidates. Reserve candidates are not filler and do not bypass safety, originality, copyright, metadata, background or diversity rules.

## Ad-hoc scheduled/manual contract

Every Ad-hoc pool records:

- `planning_mode`: `scheduled_daily` or `manual_on_demand`;
- `singapore_date`: `YYYY-MM-DD`.

For `scheduled_daily`, all five candidate content IDs use the date-scoped `wd-YYYYMMDDT010000-adhoc-...` namespace. Private promotion is serialized and checks repository state before promotion and again after rebasing. At most one canonical scheduled Ad-hoc request may exist for a Singapore date.

If a scheduled pool fails before promotion, a new immutable pool attempt may be authored because no canonical request exists. Once a canonical scheduled request exists, retries always reuse that content ID through the manual workflow/recovery path.

`manual_on_demand` is explicitly separate and may coexist with the scheduled request while preserving the same immutable/publication rules.

## Timing and publication

Normal Daily planning at/after 20:00 Asia/Singapore targets the next Singapore calendar day with 24 exact top-of-hour slots from 00:00 through 23:00.

Same-day catch-up keeps only exact top-of-hour slots at least 30 minutes in the future. ChatGPT checks this before committing the pool, and private promotion rechecks it mechanically. A delayed stale catch-up pool fails closed instead of creating immutable too-close requests.

Daily pool candidates carry the exact publication template:

```json
{
  "mode": "scheduled",
  "timezone": "Asia/Singapore",
  "publish_at": null
}
```

Promotion validates that template and may set only `publish_at` to the selected pool slot. It does not repair publication mode/timezone or creative fields.

Ad-hoc candidates carry immediate-public publication with `publish_at=null`; final upload resolves to `privacyStatus: public` and no future `publishAt`.

## Validation-before-push transaction boundary

Promotion must not publish invalid immutable production state merely because local materialization succeeded.

Both production workflows therefore use this order:

```text
materialize locally
  -> local production commit
  -> rebase latest main
  -> final validation on rebased state
  -> push validated state
  -> dispatch public runtime
```

If `main` moves after validation, the push fails non-fast-forward. The workflow does not rebase again after validation and does not publish a differently based commit without rerunning validation.

This is intentionally stronger than validating only after a push: validation failure cannot leave a bad immutable production request/plan already committed to `main`.

## Background ownership and hard validation

ChatGPT chooses logical backgrounds, performs planning-time audit reasoning, decides whether the configured emergency pair is necessary, and authors both treatment values.

Private validation independently enforces hard facts including:

- registered IDs and primary/backup distinctness;
- active + verified status;
- commercial-use permission;
- watermark/text absence;
- quality floor;
- production-suitable rendition availability;
- exact treatment shape;
- **finite** numeric values;
- playback-rate and segment-start/duration bounds;
- segment end within known source duration;
- when duration is unknown/untrusted, full-source treatment only (`start=0`, `duration=null`).

The validator is a gate. It never re-ranks, repairs a story, selects another logical asset or calculates another treatment.

`media/background_treatment.py` remains a private policy/history reference and optional planning aid. Its deterministic helpers do not own final treatment selection for new ranked pools.

## Physical rendition execution

The public runtime owns physical execution:

1. validate/fetch promoted immutable request;
2. select the smallest rendition sufficient after real 9:16 crop;
3. reuse normalized physical cache where applicable;
4. download/normalize when needed;
5. apply exact frozen segment/playback treatment to job-local input;
6. perform narration/alignment/caption/render/upload/verification.

Production target is 1080×1920/30fps H.264 High, yuv420p/BT.709 with AAC-LC 48 kHz narration.

The public runtime never keeps a cross-run creative-history ledger and never substitutes an unrelated third logical asset.

## Analytics learning

Raw YouTube observations are collected publicly by `production-runtime/.github/workflows/observe.yml` approximately **01:30, 07:30, 13:30 and 19:30 Asia/Singapore** and written into private state.

Private `analytics-collection.yml` processes/enriches the latest observation snapshot at approximately **19:45 Asia/Singapore**, before the normal 20:00 planner.

Analytics uses comparable age windows (approximately 24h/72h/7d), normalized cohort performance and controlled creative attributes. `analytics_evidence_count` is the confidence input; raw video/published/mature counts are not substitutes.

Missing metrics are renormalized away rather than invented as zero. The targeted API's engaged-view continuation proxy must not be mislabeled as Studio's viewed-vs-swiped control.

Historical learning remains evidence, not an authority that replaces editorial judgment or exploration.

## Upload idempotency and recovery

Before `videos.insert`, production creates durable private upload intent/evidence. Once intent exists, absence of a visible video is never permission for another insert.

Recovery operates only on already-promoted immutable requests. It may redispatch unresolved subsets, reconcile no-start/failed/stale executions, and reuse durable upload/receipt evidence. It never revisits unused 36/5 reserve candidates after production begins.

For schema v5, recovery always reuses the exact background treatments from the immutable request.

## Workflows

Private workflows:

- `daily-production.yml` — Daily pool promotion + dispatch + manual recovery;
- `adhoc-production.yml` — Ad-hoc pool promotion + single dispatch/manual existing-request execution;
- `automatic-recovery.yml` — promoted production reconciliation/recovery;
- `analytics-collection.yml` — private analytics processing;
- `background-management.yml` — registry maintenance;
- `dry-run.yml` — private CI/architecture/contract gate plus linked public Dry Run.

Public runtime workflows:

- `run.yml` — Daily batch execution;
- `single.yml` — one Ad-hoc execution;
- `observe.yml` — public analytics observation;
- `dry-run.yml` — runtime/render regression validation;
- `base.yml` — runtime base image build.

## Repository hygiene

Transient caches/local render outputs are ignored. Ranked pools, promoted requests, planning audits, recovery evidence, verified receipts, analytics state and media registry are durable private state.

Retired `planner-execution.yml`, `execution_bridge.py`, duplicate Ad-hoc router workflows, legacy Wacky Insights architecture and V4 planner base prompts must not be reintroduced.

## Acceptance

Before merging a production/control-plane change:

1. private compile/tests/state guards pass;
2. precommit/ranked-pool tests prove Daily 36/36 and Ad-hoc 5/5 authoring gates plus frozen-rank promotion semantics;
3. Daily retry-attempt paths remain append-only and one canonical plan per date remains enforced;
4. scheduled Ad-hoc uniqueness is repository-enforced;
5. catch-up slots are rechecked at promotion time;
6. hard request validation rejects invalid registry/treatment/non-finite/unknown-duration contracts without mutating AI-authored requests;
7. promoted immutable state is validated after rebase and before push;
8. normal Daily production still contains exactly 24 unique Singapore hourly slots;
9. private/public compatibility fingerprints remain equal;
10. private Dry Run and its correlated public runtime Dry Run both succeed.
