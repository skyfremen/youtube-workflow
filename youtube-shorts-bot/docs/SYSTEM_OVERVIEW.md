# Wacky Dramas System Overview

## Purpose

The canonical Shorts system uses a competitive planning funnel: generate broadly, reject cheaply, develop selectively, freeze a ranked reserve pool, mechanically validate/promote only strong candidates, then feed comparable public performance back into future planning.

The business objective remains aggressive subscriber and qualified-view growth, including **1,000 subscribers** and **10 million qualified public Shorts views within a rolling 90-day window**. In this repository, growth is business-purpose language only; technical architecture uses functional names such as planning, validation, promotion, production, publication, verification, analytics, and learning.

Normal Daily production remains exactly **24 Shorts per day**, one scheduled publication per hour in **Asia/Singapore**. Ad-hoc production remains exactly one immediately Public Short per promoted run.

## Architecture

```text
Daily ChatGPT planner
  -> >=120 raw premises
  -> hard duplicate/quality/safety rejection
  -> editorial + analytics evidence
  -> semifinalist development and title competition
  -> exactly 36 complete ranked production candidates
  -> ChatGPT freezes story/title/voice/punchline/backgrounds/treatments
  -> one immutable candidate-pool commit
  -> private daily-production.yml
       -> global compatibility + registry preflight
       -> strict validation of all 36
       -> first 24 valid by frozen rank for normal next-day
       -> mechanically assign exact 24 hourly slots
       -> materialize exactly 24 immutable schema-v5 requests + final plan
       -> final strict validation
       -> one opaque public dispatch
  -> public run.yml
  -> TTS / alignment / render / upload / verify
  -> immutable result receipts
  -> age-matched analytics learning
```

```text
Ad-hoc ChatGPT planner
  -> exactly 5 complete ranked production candidates
  -> one immutable Ad-hoc candidate-pool commit
  -> private adhoc-production.yml
       -> global compatibility + registry preflight
       -> strict validation of all 5
       -> first valid by frozen rank
       -> materialize exactly one immutable schema-v5 request
       -> final strict validation
       -> one-item private execution state
       -> opaque public single.yml dispatch
  -> immediate Public upload and verification
```

Reserve candidates never cross the public boundary. The public runtime sees only the final promoted immutable requests at an exact private source revision.

## Planning ownership

ChatGPT / Work owns creative and semantic judgment: premise generation, rejection reasoning, duplicate/near-duplicate reasoning, scoring interpretation, analytics interpretation, diversity, full stories, titles, voices, punchline semantics, logical backgrounds, background-audit/fallback reasoning, and background treatment selection.

Repository code such as `planning/planning_engine.py`, `media/background_selector.py`, and `media/background_treatment.py` remains a rules/evidence/reference surface and regression implementation. New planning no longer uses a planner-execution GitHub round trip. The former `planner-execution.yml` / `planning/execution_bridge.py` path is retired.

Numeric scores are evidence, not editorial authority. GitHub may not re-rank or invent a replacement candidate. It only validates candidate contracts and promotes the first candidates that pass in the exact rank order frozen by ChatGPT.

The broad Daily creative funnel still targets at least 120 raw premises. The final planning artifact submitted by ChatGPT is now exactly 36 fully developed candidates, providing 12 reserves beyond the normal 24-production target. Reserve candidates must meet the same creative bar; they are not filler.

Ad-hoc planning submits exactly five fully developed ranked candidates so one candidate-specific validation failure does not force a new planning round trip.

## Analytics

Planning uses private analytics as evidence, not direct authority. The canonical confidence input is `analytics_evidence_count`, an evidence-equivalent count based on sufficiently mature comparable videos/views. Missing metrics are never invented or silently replaced with unrelated counters.

Raw observations are collected publicly through `production-runtime/.github/workflows/observe.yml` approximately **01:30, 07:30, 13:30, and 19:30 Asia/Singapore** and written into private state. Private `analytics-collection.yml` processes/enriches them at approximately **19:45 Asia/Singapore** before normal 20:00 planning.

Age-matched 24h / 72h / 7d cohorts, smoothed creative-attribute learning, exploration, and diversity continue to prevent one early or viral outlier from dominating future planning.

## Ranked candidate pools

Daily immutable planning pool:

`content/candidate-pools/daily/YYYY-MM-DD.json`

It contains exactly 36 candidate envelopes ranked `1..36`, current rules provenance, planning mode, target count, and publication slots. A Daily candidate is complete except that `publication.publish_at` is deliberately null; the private promotion step assigns slots only after selecting the first strict-valid candidates.

Ad-hoc immutable planning pool:

`content/candidate-pools/adhoc/ap-<id>.json`

It contains exactly five candidate envelopes ranked `1..5`. Every Ad-hoc candidate already carries the final immediate-public publication contract.

The pool commit itself is not a public-runtime batch. Private production materializes a second immutable production commit/state from it.

## Strict request validation

**Schema v5 is the current production request format. Schema v4 remains executable only for existing immutable migration/recovery requests.**

The canonical strict validator checks the normal story/narration/YouTube/planning/publication schema plus hard background/treatment production safety:

- primary/backup IDs are distinct and registered;
- assets are active and verified;
- commercial use is allowed and license/source evidence exists;
- watermark and embedded-text flags are safe;
- the hard background quality floor is satisfied;
- at least one physical rendition can produce the required final crop without disallowed enlargement;
- schema-v5 treatments have valid fields and numeric bounds;
- treatment start/duration physically fit the selected asset duration.

These checks deliberately do **not** perform semantic background ranking, recency ranking, creative substitution, or treatment recalculation. AI decides; code validates.

Daily validates all 36 candidates before promotion, then validates the promoted final requests again. If fewer than the production target pass, it fails closed without a partial batch. Ad-hoc validates all five and promotes only the first valid one; if none pass, it fails closed.

## Immutable production request contract

Every promoted schema-v5 request contains canonical story/narration/YouTube/planning/publication metadata plus distinct logical `background_primary_id` / `background_backup_id` and immutable `background_primary_treatment` / `background_backup_treatment` objects.

Daily final requests carry exact UTC `publish_at` values corresponding to unique Singapore top-of-hour slots. Ad-hoc requests carry `mode=immediate`, `timezone=Asia/Singapore`, and `publish_at=null`.

The final request bytes and exact source commit remain the execution/recovery authority.

## Background and treatment planning

ChatGPT reads the verified logical registry, current policy, successful private receipts, and same-pool planned usage. It chooses logical assets and treatments before the candidate-pool commit.

The current background selector code retains normal eligibility/ranking and emergency fallback rules as a reference for ChatGPT. The current treatment code retains segment/speed anti-repetition logic and category speed ranges as planning evidence. ChatGPT applies those rules when authoring each candidate; private production validates the frozen result rather than rerunning creative allocation.

Persistent usage history still comes only from immutable successful private receipts. The public runtime does not maintain a cross-run creative ledger.

## Public runtime boundary

The public runtime owns physical execution only:

1. fetch final immutable private state at the exact promoted source SHA;
2. validate public-side request/runtime compatibility;
3. resolve the smallest sufficient physical rendition;
4. normalize/crop as required;
5. apply the frozen treatment to job-local media;
6. synthesize Kokoro narration;
7. perform Wav2Vec2 word alignment;
8. render 1080×1920 / 30 fps H.264 High + AAC-LC with active-word focus and planner-authored semantic punchline emphasis;
9. upload with durable intent/duplicate protection;
10. verify exact YouTube publication state and write immutable receipts.

The private repository does not perform TTS, rendering, media downloading for production, or direct YouTube upload.

## Batch production and recovery

`daily-production.yml` sends one opaque public dispatch after promotion. Public `run.yml` prepares once, partitions the final 24-item normal batch into bounded units, continues through item-specific failures, aggregates, and records diagnostic/completion state.

`adhoc-production.yml` creates one private one-item execution batch and dispatches public `single.yml` at concurrency one.

Private `automatic-recovery.yml` remains the recovery authority. It reconciles no-start, failed, stale and partial work, preserves immutable source identities where required, and sends unresolved subsets through the canonical public execution path. Durable intent/upload evidence remains the duplicate-publication fence.

## Render verification

The public verifier checks duration, **1080×1920** resolution, 30 fps, H.264 High, yuv420p/BT.709, exactly one AAC-LC narration stream at 48 kHz, representative frame decoding, render metadata identity, and final video SHA.

Semantic punchline timing is derived from real alignment of planner-authored punchline text; the public runtime does not infer a punchline from audio position or heuristics.

## Acceptance

Before a production architecture change is merged:

1. private Python compiles and the complete private unit/contract suite passes;
2. topology tests prove Daily uses a 36-candidate pool and Ad-hoc uses a five-candidate pool;
3. tests prove GitHub preserves frozen rank and does not restore the planner-execution bridge;
4. strict background/treatment validation fails closed for unsafe or physically impossible requests;
5. final normal Daily production remains exactly 24 unique hourly slots;
6. private/public contract fingerprints remain equal;
7. private Dry Run proves no TTS/render/upload side effects;
8. linked public Dry Run exercises production-equivalent rendering/verification without a production upload;
9. recovery/idempotency/durable-intent guarantees remain intact.
