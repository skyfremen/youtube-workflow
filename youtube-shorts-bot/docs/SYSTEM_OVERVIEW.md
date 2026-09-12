# Wacky Dramas System Overview

## Purpose

The canonical Shorts system uses a competitive daily funnel: generate broadly, reject cheaply, develop selectively, publish only winners, then feed comparable public performance back into future selection.

The business objective remains aggressive subscriber and qualified-view growth, including the current target of **1,000 subscribers** and **10 million qualified public Shorts views within a rolling 90-day window**. In this repository, growth is business-purpose language only; technical architecture uses functional names such as planning, production, publication, verification, analytics, and learning.

The system targets up to **24 Shorts per day**, one scheduled publication per hour in **Asia/Singapore**, while preserving one immutable `content_id` per story and durable upload/recovery guarantees.

## Architecture

```text
Daily planner
  -> >=120 raw premises
  -> hard duplicate/quality/safety rejection
  -> editorial cold-start scoring
  -> ~36 semifinalists
  -> ending + opening-line + >=5-title competition
  -> confidence-weighted analytics adjustment
  -> diversity + ~80/20 exploit/explore
  -> <=24 winners
  -> full scripts + verified background IDs
  -> private segment/playback treatment allocation
  -> immutable schema-v5 requests
  -> one lightweight private dispatch (batch_id + source_sha + contract_hash)
  -> one public runtime workflow and bounded production units
  -> resolve/normalize physical background once
  -> apply frozen job-local segment/playback treatment
  -> render selected stories only
  -> upload each exactly once according to immutable publication mode
  -> verify exact YouTube state
  -> immutable verified receipt using the request schema version
  -> age-matched 24h / 72h / 7d analytics learning
```

Schema v5 is the current production request format for newly authored Daily and Ad-hoc Shorts. Schema v4 remains executable only for staged migration/recovery of immutable requests that already exist. Older schema-v3 receipts remain historical/analytics compatibility only where the consuming component explicitly supports them.

There is no mutable hourly queue and no hourly render cron. Scheduled publication cadence is delegated to YouTube after selected videos are prepared in advance; Ad-hoc publication remains immediate-public through its immutable request contract.

## Planning competition

Twenty-four final uploads should be winners of a real competition. A raw pool of at least 120 premises creates room to reject duplicates, weak hooks, thin conflicts, poor payoffs and overrepresented categories without filling the day with low-quality material.

Raw candidates are cheap structured premises. They do not trigger media download, TTS, rendering or upload. Expensive production begins only after final selection.

Central strategy values live in `planning/planning_config.py`. `planning/planning_engine.py` owns deterministic arithmetic so prompt wording cannot silently change weighting. `planning/planning_runner.py` is the required executable checkpoint for raw filtering and final deterministic selection; Work consumes its actual returned result rather than reproducing the arithmetic manually.

With no mature public performance evidence, selection is 100% editorial. Analytics stays disabled until enough comparable milestone evidence exists. The planner uses `analytics_evidence_count`, an evidence-equivalent count based on both mature videos and comparable views, then increases analytics influence gradually with a hard cap so editorial judgment and exploration always remain material.

Raw YouTube metrics are never treated directly as 0–100 candidate scores. `analytics/analytics_learning.py` normalizes comparable cohort performance and builds a smoothed historical attribute model. Candidate analytics enters `planning/planning_engine.py` only as normalized `historical_attribute_fit`.

Missing metrics are renormalized away. They are never replaced with invented zeros or proxy values. The exact Studio viewed-vs-swiped control is not available through the targeted API used here; `engaged_view_rate` is an `engagedViews / views` continuation proxy and must never be mislabeled as that Studio metric.

## Similarity and diversity

Duplicate filtering uses premise/conflict/context/payoff/ending/opening text plus controlled structural attributes. Strong near duplicates are hard rejected; softer overlap can reduce originality during planning.

Final selection enforces approximate daily caps for category, core conflict and title pattern, and the scheduler avoids repeated ending/title patterns in adjacent hours when alternatives exist.

A full 24-story plan aims for roughly 19 exploit and 5 explore selections. Exploration still has to pass every hard quality, safety and truthfulness gate.

## Immutable request contract

**Schema v5 is the current production request format. Schema v4 remains supported for existing immutable migration/recovery requests.** Every newly authored request contains the canonical story, narration, visual and YouTube fields plus:

- immutable `publication`; Daily uses `mode=scheduled`, `timezone=Asia/Singapore`, and exact UTC `publish_at`, while Ad-hoc uses `mode=immediate` with `publish_at=null`
- immutable `planning` metadata with scores, title competition, selected title/hook scores, analytics weight, controlled story attributes, similarity result and exploit/explore classification
- story metadata that freezes lead gender and story tone so the approved narration voice can be selected deterministically
- distinct logical `background_primary_id` and `background_backup_id`
- immutable `background_primary_treatment` and `background_backup_treatment`, each freezing `segment_start_seconds`, `segment_duration_seconds`, and `playback_rate`

Persistent asset/category/segment/playback history is owned by the private planner and derived from immutable successful receipts. Daily may additionally use same-run ephemeral planned state. The public runtime does not keep a cross-run creative-history ledger.

The schedule/publication contract and visual treatment are bound to the same immutable request bytes and exact source commit as the story.

## Background execution boundary

The private planner chooses logical assets and their temporal/playback treatments. The public runtime owns physical execution:

1. validate the frozen logical primary/backup IDs and treatment objects;
2. select the smallest rendition that remains sufficient after the real 9:16 crop;
3. reuse the normalized physical cache when available;
4. download only when needed and normalize once to 1080×1920/30 H.264 when required;
5. apply the frozen segment/playback treatment to a job-local normalized input;
6. render captions, brand treatments and narration.

The normalized cache is treatment-agnostic and is only a physical optimization. A different temporal treatment must not create persistent public creative state or force re-download of an already cached normalized master.

## Batch production and Actions cost

`daily-production.yml` performs one lightweight cross-repository dispatch. The public `production-runtime` workflow prepares once, deterministically partitions a normal 24-item batch into bounded units, then performs one authoritative aggregation/finalization. All canonical requests, intents, upload evidence, receipts, completion state, diagnostics and analytics remain private. Ad-hoc generation uses the separate one-job `single.yml` path at concurrency one.

The public repository also owns the canonical runtime-image build through `base.yml`, `base/Dockerfile`, and `base/dependencies.txt`. The private repository does not contain a Dockerfile, runtime dependency manifest, or image-build workflow.

The batch continues after individual failures so one bad story does not prevent already-good stories from completing. The job ultimately fails if any item failed, making partial state visible. A rerun does not blindly upload again: each content ID first resolves its immutable receipt, upload intent and upload evidence.

The opaque batch concurrency group prevents overlapping execution of the same logical batch.

## Upload idempotency and recovery

Before `videos.insert`, production creates an immutable durable intent containing:

- exact request identity/blob SHA/source commit
- expected channel ID
- exact immutable upload body
- verified render metadata and background selection
- workflow provenance

Once an intent exists, absence of a visible video is **never** permission to insert again. Recovery searches only through the bounded, evidence-driven paths defined by the recovery contract and either imports/verifies the matching upload or fails closed for operator reconciliation.

If verification happens after a scheduled video has already transitioned public, recovery may accept that state only when durable evidence proves the exact intended schedule and YouTube is not observed public before that instant.

A verified result receipt uses the same supported schema version as its immutable request and is created only after exact YouTube state and render evidence verify successfully. For schema v5 it also binds the executed background treatment to the immutable request. Existing receipts are immutable and reused unchanged.

## Render verification

The public runtime's transformation/verification pipeline fails closed when required render evidence is missing or invalid.

The verifier checks duration, **1080×1920** resolution, 30 fps, H.264 High video, yuv420p/BT.709, exactly one AAC-LC narration stream at 48 kHz, representative frame decoding, render metadata identity and the final video SHA.

## Analytics

Raw YouTube observations are collected by the public `production-runtime/.github/workflows/observe.yml` approximately **01:30, 07:30, 13:30, and 19:30 Asia/Singapore** and written into private state. Public runtime validation is isolated in credential-free `dry-run.yml`. The private `analytics-collection.yml` processes/enriches the latest observations once per day at approximately **19:45 Asia/Singapore**, before the normal 20:00 planner.

Analytics accepts canonical published success receipts for schemas v3, v4 and v5. Schema v3 is historical analytics compatibility; v4 covers immutable pre-v5 production; v5 is current production. Milestones are captured only in bounded windows around approximately 24 hours, 72 hours and 7 days so the model compares like-aged performance rather than ranking a two-hour-old Short against a week-old Short by raw views.

The performance model uses available signals including engaged-view continuation, average percentage viewed, qualified views, **net subscribers per 1,000 views**, shares, likes and comments. Metrics are normalized within the selected cohort before aggregation.

Historical learning is attributed to controlled creative dimensions including category, conflict, primary emotion, protagonist/antagonist roles, opening style, title style, ending style and duration bucket. Small samples are smoothed toward the cohort mean so one viral outlier cannot dominate future planning.

The planner prefers the most mature cohort with enough usable evidence: 7d, otherwise 72h, otherwise 24h. If no cohort qualifies, analytics remains disabled and planning falls back to editorial scoring with a documented reason.

## Daily content commit

The external daily planner follows `planning/DAILY_PLANNER_PROMPT.md` and creates exactly one immutable planning audit plus 1–24 immutable schema-v5 request files in one content-only commit whose message begins:

`[daily production] YYYY-MM-DD`

That commit is routed to `daily-production.yml`, which dispatches the only authoritative execution/upload implementation in the public runtime.

## Repository state hygiene

Transient Python caches, local environment files, render outputs and preview outputs are ignored by the root `.gitignore`. Durable requests, recovery evidence, result receipts, planning/background-sourcing audits, analytics state and the verified media registry are intentionally tracked and must not be treated as disposable generated files.

## Acceptance

Before a production change is merged:

1. private planning/state checks and public runtime static/unit checks must pass
2. planning acceptance must generate at least 120 raw premises and valid selected requests
3. selected requests must have unique Singapore hourly slots
4. dry-run must prove no TTS, render, upload or false-receipt side effects in the private control plane
5. production must retain durable intent and duplicate-recovery invariants
6. current secrets must remain referenced only through GitHub Actions secret expressions
7. the public runtime must write canonical state only to this private repository
8. the private/public semantic contract fingerprints must remain equal
9. schema-v5 treatment execution must remain stateless publicly and receipt-derived privately
