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
  -> immutable schema-v3 requests
  -> one batch production job
  -> render selected stories only
  -> upload each exactly once as private + publishAt
  -> verify exact YouTube state
  -> immutable schema-v3 receipt
  -> age-matched 24h / 72h / 7d analytics learning
```

There is no mutable hourly queue and no hourly render cron. Publication cadence is delegated to YouTube's scheduled publication state after selected videos are prepared in advance.

## Planning competition

Twenty-four final uploads should be winners of a real competition. A raw pool of at least 120 premises creates room to reject duplicates, weak hooks, thin conflicts, poor payoffs and overrepresented categories without filling the day with low-quality material.

Raw candidates are cheap structured premises. They do not trigger media download, TTS, rendering or upload. Expensive production begins only after final selection.

Central strategy values live in `planning/planning_config.py`. `planning/planning_engine.py` owns deterministic arithmetic so prompt wording cannot silently change weighting.

With no mature public performance evidence, selection is 100% editorial. Analytics stays disabled until at least 10 comparable ~24-hour milestone snapshots exist and view evidence is sufficient. The planner uses `analytics_evidence_count`, an evidence-equivalent count based on both mature videos and comparable views, then increases analytics influence gradually with a hard cap of **60%** so editorial judgment and exploration always remain material.

Raw YouTube metrics are never treated directly as 0–100 candidate scores. `analytics/analytics_learning.py` normalizes comparable cohort performance and builds a smoothed historical attribute model. Candidate analytics enters `planning/planning_engine.py` only as normalized `historical_attribute_fit`.

Missing metrics are renormalized away. They are never replaced with invented zeros or proxy values. The exact Studio viewed-vs-swiped control is not available through the targeted API used here; `engaged_view_rate` is an `engagedViews / views` continuation proxy and must never be mislabeled as that Studio metric.

## Similarity and diversity

Duplicate filtering uses premise/conflict/context/payoff/ending/opening text plus controlled structural attributes. Strong near duplicates are hard rejected; softer overlap can reduce originality during planning.

Final selection enforces approximate daily caps for category, core conflict and title pattern, and the scheduler avoids repeated ending/title patterns in adjacent hours when alternatives exist.

A full 24-story plan aims for roughly 19 exploit and 5 explore selections. Exploration still has to pass every hard quality, safety and truthfulness gate.

## Immutable request contract

**Schema v3 is the only supported production request format.** Every request contains the canonical story, narration, visual and YouTube fields plus:

- immutable `publication` with `mode=scheduled`, `timezone=Asia/Singapore`, and exact UTC `publish_at`
- immutable `planning` metadata with scores, title competition, selected title/hook scores, analytics weight, controlled story attributes, similarity result and exploit/explore classification

The schedule is bound to the same immutable request bytes and source commit as the story. Production requires a complete scheduled publication contract.

## Batch production and Actions cost

`daily-production.yml` processes selected requests in one heavy container job instead of starting one full production runner each hour. This removes repeated image/container setup while retaining per-content isolation through dedicated output directories and durable GitHub state.

The batch continues after individual failures so one bad story does not prevent already-good stories from completing. The job ultimately fails if any item failed, making partial state visible. A rerun does not blindly upload again: each content ID first resolves its immutable receipt, upload intent and upload evidence.

The production upload concurrency group prevents overlapping daily insertion activity.

## Upload idempotency and recovery

Before `videos.insert`, production creates an immutable durable intent containing:

- exact request identity/blob SHA/source commit
- expected channel ID
- exact private + scheduled `publishAt` upload body
- verified render metadata and background selection
- workflow provenance

Once an intent exists, absence of a visible video is **never** permission to insert again. Recovery searches the authenticated channel for the deterministic non-viewer-facing content marker and either imports the matching upload or fails closed for operator reconciliation.

If verification happens after a scheduled video has already transitioned public, recovery may accept that state only when durable evidence proves the exact intended schedule and YouTube is not observed public before that instant.

A schema-v3 result receipt is created only after exact YouTube state and render evidence verify successfully. Existing receipts are immutable and reused unchanged.

## Render verification

The production render writes inline black-detection evidence during the render pass. `rendering/verify_render.py` requires that evidence and fails closed if it is missing or failed.

The verifier independently checks duration, 720×1280 resolution, 30 fps, H.264 video, exactly one AAC narration stream, representative frame decoding, render metadata identity and the final video SHA.

## Analytics

`analytics/analytics_collection.py` runs at approximately **01:30, 07:30, 13:30, and 19:30 Asia/Singapore**. The 19:30 snapshot is the final refresh before the normal 20:00 daily planner.

Analytics reads only canonical scheduled schema-v3 receipts with planning metadata. Milestones are captured only in bounded windows around approximately 24 hours, 72 hours and 7 days so the model compares like-aged performance rather than ranking a two-hour-old Short against a week-old Short by raw views.

The performance model uses available signals including engaged-view continuation, average percentage viewed, qualified views, **net subscribers per 1,000 views**, shares, likes and comments. Metrics are normalized within the selected cohort before aggregation.

Historical learning is attributed to controlled creative dimensions including category, conflict, primary emotion, protagonist/antagonist roles, opening style, title style, ending style and duration bucket. Small samples are smoothed toward the cohort mean so one viral outlier cannot dominate future planning.

The planner prefers the most mature cohort with enough usable evidence: 7d, otherwise 72h, otherwise 24h. If no cohort qualifies, analytics remains disabled and planning falls back to editorial scoring with a documented reason.

## Daily content commit

The external daily planner follows `planner/DAILY_PLANNER_PROMPT.md` and creates exactly one immutable planning audit plus 1–24 immutable schema-v3 request files in one content-only commit whose message begins:

`[daily production] YYYY-MM-DD`

That commit is routed to `daily-production.yml`, the only production-upload workflow in the supported tree.

## Repository state hygiene

Transient Python caches, local environment files, render outputs and preview outputs are ignored by the root `.gitignore`. Durable requests, recovery evidence, result receipts, planning/background-sourcing audits, analytics state and the verified media registry are intentionally tracked and must not be treated as disposable generated files.

## Acceptance

Before a production change is merged:

1. static compilation and all unit/contract tests must pass
2. planning acceptance must generate at least 120 raw premises and valid selected requests
3. selected requests must have unique Singapore hourly slots
4. dry-run must prove no TTS, render, upload or false-receipt side effects
5. production must retain durable intent and duplicate-recovery invariants
6. current secrets must remain referenced only through GitHub Actions secret expressions
