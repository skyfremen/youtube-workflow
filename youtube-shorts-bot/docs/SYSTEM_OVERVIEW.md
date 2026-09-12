# Wacky Dramas System Overview

## Purpose

The canonical Shorts system uses a competitive planning funnel: generate broadly, reject cheaply, fully develop a ranked reserve pool, mechanically validate the frozen AI-authored candidates, publish only the highest-ranked valid winners, then feed comparable public performance back into future planning.

The business objective remains aggressive subscriber and qualified-view growth, including the current target of **1,000 subscribers** and **10 million qualified public Shorts views within a rolling 90-day window**. In this repository, growth is business-purpose language only; technical architecture uses functional names such as planning, validation, production, publication, verification, analytics, and learning.

A normal Daily plan publishes exactly **24 Shorts**, one per hour in **Asia/Singapore**. ChatGPT authors a larger immutable ranked planning pool of **36 complete candidates** so candidate-specific validation failures can be absorbed without weakening the 24-Short production contract. Ad-hoc planning similarly authors **5 complete ranked candidates** and promotes the first mechanically valid one.

## Architecture

```text
ChatGPT / Work
  -> inspect current private repo rules/config/analytics/history/background registry
  -> generate broad creative candidates
  -> hard duplicate/quality/safety rejection
  -> editorial scoring + analytics evidence + diversity reasoning
  -> fully author complete production candidates
  -> choose exact primary/backup logical backgrounds
  -> perform background-audit reasoning
  -> choose frozen segment/playback treatments
  -> freeze final AI rank order

Daily:
  -> commit exactly one immutable 36-candidate ranked pool
  -> daily-production.yml
       -> global fail-first preflight
       -> mechanically validate candidates in frozen rank order
       -> promote the first 24 valid candidates
       -> materialize one canonical planning audit + exactly 24 immutable requests
       -> validate canonical production commit again
       -> dispatch public run.yml

Ad-hoc:
  -> commit exactly one immutable 5-candidate ranked pool
  -> adhoc-production.yml
       -> global fail-first preflight
       -> mechanically validate candidates in frozen rank order
       -> promote the first valid candidate
       -> materialize exactly one immutable request
       -> validate it again
       -> dispatch public single.yml

Public runtime:
  -> fetch exact promoted private state by opaque batch/source contract
  -> resolve/normalize physical background
  -> execute frozen segment/playback treatment
  -> TTS + alignment + captions + render
  -> upload exactly once according to immutable publication mode
  -> verify exact YouTube state
  -> persist private immutable evidence/receipt
  -> public observations feed private analytics learning
```

Schema v5 is the current production request format for newly promoted Daily and Ad-hoc Shorts. Schema v4 remains executable for recovery of immutable requests that already exist. Older schema-v3 receipts remain historical/analytics compatibility only where a consuming component explicitly supports them.

There is no mutable hourly queue and no hourly render cron. Scheduled publication cadence is delegated to YouTube after selected videos are prepared in advance; Ad-hoc publication remains immediate-public through its immutable request contract.

There is also no `planner-execution.yml` bridge. ChatGPT owns planning/background/treatment decisions directly; private code is an independent fail-closed validation gate, not a creative decision maker.

## Planning competition and ranked reserve pools

A raw pool of at least 120 premises creates room to reject duplicates, weak hooks, thin conflicts, poor payoffs and overrepresented categories without filling the day with low-quality material. Raw candidates are cheap structured premises and do not trigger media download, TTS, rendering or upload.

Central strategy values live in `planning/planning_config.py`. `planning/planning_engine.py`, `planning/planning_runner.py`, analytics code and media policy code remain executable rule/specification/regression sources. For new ranked-pool planning, **ChatGPT / Work owns the editorial decision path and final rank order**; deterministic code must not replace ChatGPT's winner ranking.

The production handoff is intentionally two-stage:

1. **planning pool** — immutable, AI-authored, larger than the production target;
2. **canonical production state** — mechanically materialized from the first candidates that pass the hard validator.

For normal Daily, the planning pool contains exactly **36** complete candidates and the production target is exactly **24**. For Ad-hoc, the pool contains exactly **5** complete candidates and the production target is exactly **1**.

A failed candidate is skipped, not repaired. Later candidates retain their original ChatGPT rank. If fewer than the required target pass, the private workflow fails closed rather than weakening validation or making an editorial substitution.

With no mature public performance evidence, selection/ranking is editorial. Analytics stays disabled until enough comparable milestone evidence exists. The planner uses `analytics_evidence_count`, an evidence-equivalent count based on both mature videos and comparable views, then increases analytics influence gradually with a hard cap so editorial judgment and exploration always remain material.

Raw YouTube metrics are never treated directly as 0–100 candidate scores. `analytics/analytics_learning.py` normalizes comparable cohort performance and builds a smoothed historical attribute model. Candidate analytics enters planning only as normalized evidence such as `historical_attribute_fit`.

Missing metrics are renormalized away. They are never replaced with invented zeros or proxy values. The exact Studio viewed-vs-swiped control is not available through the targeted API used here; `engaged_view_rate` is an `engagedViews / views` continuation proxy and must never be mislabeled as that Studio metric.

## Similarity and diversity

Duplicate filtering uses premise/conflict/context/payoff/ending/opening text plus controlled structural attributes. Strong near duplicates are hard rejected; softer overlap can reduce originality during planning.

ChatGPT applies the current category, conflict, title-pattern, ending and explore/exploit constraints while building and ranking the pool. Reserve candidates remain production-quality; they are not filler permitted to bypass diversity, safety, truthfulness, copyright, or quality rules.

A normal 24-story production set still aims for the current exploit/explore balance after promotion. The rank order should be designed so mechanically skipping an invalid candidate does not intentionally undermine those constraints.

## Immutable ranked-pool contract

Daily ChatGPT commits exactly one pool file:

`content/planning-pools/daily/YYYY-MM-DD.json`

with subject:

`[daily pool] YYYY-MM-DD`

A normal pool contains exactly 36 complete candidates, rank `1..36`, target count 24 and the 24 canonical hourly Singapore publication slots. ChatGPT does **not** commit the canonical `content/planning/YYYY-MM-DD.json` or production request files directly for a new plan.

Ad-hoc ChatGPT commits exactly one pool file under:

`content/planning-pools/adhoc/ap-<stable-id>.json`

with a commit subject beginning `[adhoc pool]`. It contains exactly 5 complete immediate-public candidates ranked `1..5`.

Planning pools are protected append-only private state. Their provenance records `editorial_selection_owner=chatgpt`, `planning_method=chatgpt_ranked_pool`, the exact `rules_source_sha`, and the complete ranked candidate identity order.

## Immutable production request contract

**Schema v5 is the current production request format. Schema v4 remains supported for existing immutable recovery requests.** Each promoted request contains the canonical story, narration, visual and YouTube fields plus:

- immutable `publication`; Daily uses `mode=scheduled`, `timezone=Asia/Singapore`, and an exact UTC `publish_at`, while Ad-hoc uses `mode=immediate` with `publish_at=null`;
- immutable `planning` metadata with scores, title competition, selected title/hook scores, analytics weight, controlled story attributes, similarity result and exploit/explore classification;
- story metadata that freezes lead gender and story tone;
- distinct logical `background_primary_id` and `background_backup_id`;
- immutable `background_primary_treatment` and `background_backup_treatment`, each freezing `segment_start_seconds`, `segment_duration_seconds`, and `playback_rate`.

For Daily pool candidates, publication is authored as a scheduled template with `publish_at=null`; the promotion gate may assign only the next frozen pool publication slot to a selected candidate. It must not rewrite creative fields.

Persistent asset/category/segment/playback history is private and derived from immutable successful receipts. ChatGPT reads and reasons over that history when authoring the pool. The public runtime does not keep a cross-run creative-history ledger.

## Background ownership and hard validation

ChatGPT chooses the logical backgrounds, performs the planning-time audit reasoning, decides whether the configured emergency default pair is necessary, and authors the treatment values. The private validator independently enforces non-negotiable facts before dispatch, including:

- registered logical IDs;
- primary/backup distinctness;
- active + verified state;
- commercial-use permission;
- watermark/text absence;
- quality floor;
- a production-suitable rendition;
- treatment field shape and playback bounds;
- segment bounds against known source duration.

The validator is a **gate**. It does not rank, repair, select an alternative story, choose a new background, or generate a replacement treatment.

The public runtime owns physical execution:

1. validate/fetch the promoted immutable request;
2. select the smallest rendition sufficient after the real 9:16 crop;
3. reuse the normalized physical cache where applicable;
4. download/normalize when needed;
5. apply the frozen segment/playback treatment to a job-local input;
6. perform narration/alignment/caption/render/upload/verification.

## Batch production and Actions cost

`daily-production.yml` is both the ranked-pool promotion gate and the lightweight cross-repository Daily dispatcher. After successfully promoting the first required valid candidates, it creates the canonical `[daily production] YYYY-MM-DD` commit and validates that commit before one opaque public dispatch.

The public `production-runtime/run.yml` prepares once, deterministically partitions a normal 24-item batch into bounded units, then performs one authoritative aggregation/finalization. All canonical requests, intents, upload evidence, receipts, completion state, diagnostics and analytics remain private.

`adhoc-production.yml` performs the equivalent 5-to-1 promotion and dispatches the public one-job `single.yml` path at concurrency one. Both private production workflows retain manual dispatch inputs for existing immutable request recovery/execution.

The public repository also owns the canonical runtime-image build through `base.yml`, `base/Dockerfile`, and `base/dependencies.txt`. The private repository does not contain a Dockerfile, runtime dependency manifest, or image-build workflow.

The public Daily batch continues after individual runtime failures so one bad execution does not prevent already-good stories from completing. The job ultimately fails if any item failed, making partial state visible. A rerun does not blindly upload again: each content ID first resolves its immutable receipt, upload intent and upload evidence.

## Upload idempotency and recovery

Before `videos.insert`, production creates immutable durable intent/evidence binding the exact request/source identity, expected channel/body, render evidence and workflow provenance.

Once an intent exists, absence of a visible video is **never** permission to insert again. Recovery searches only through the bounded, evidence-driven paths defined by the recovery contract and either imports/verifies the matching upload or fails closed for operator reconciliation.

Automatic recovery remains a private control-plane responsibility and may redispatch unresolved subsets of an already-promoted canonical production plan. Recovery does not revisit the 36/5 planning pool or re-rank reserve candidates after production has begun.

A verified result receipt uses the same supported schema version as its immutable request and is created only after exact YouTube state and render evidence verify successfully. For schema v5 it also binds the executed background treatment to the immutable request.

## Render verification

The public runtime's transformation/verification pipeline fails closed when required render evidence is missing or invalid.

The verifier checks duration, **1080×1920** resolution, 30 fps, H.264 High video, yuv420p/BT.709, exactly one AAC-LC narration stream at 48 kHz, representative frame decoding, render metadata identity and the final video SHA.

## Analytics

Raw YouTube observations are collected by public `production-runtime/.github/workflows/observe.yml` approximately **01:30, 07:30, 13:30, and 19:30 Asia/Singapore** and written into private state. Public runtime validation is isolated in credential-free `dry-run.yml`. Private `analytics-collection.yml` processes/enriches the latest observations once per day at approximately **19:45 Asia/Singapore**, before the normal 20:00 planner.

Analytics accepts canonical published success receipts for schemas v3, v4 and v5. Milestones are captured only in bounded windows around approximately 24 hours, 72 hours and 7 days so the model compares like-aged performance rather than ranking videos by raw age-dependent totals.

The performance model uses available signals including engaged-view continuation, average percentage viewed, qualified views, **net subscribers per 1,000 views**, shares, likes and comments. Metrics are normalized within the selected cohort before aggregation.

Historical learning is attributed to controlled creative dimensions including category, conflict, primary emotion, protagonist/antagonist roles, opening style, title style, ending style and duration bucket. Small samples are smoothed toward the cohort mean so one viral outlier cannot dominate future planning.

## Repository state hygiene

Transient Python caches, local environment files, render outputs and preview outputs are ignored by the root `.gitignore`. Durable ranked pools, promoted requests, recovery evidence, result receipts, canonical planning audits, analytics state and the verified media registry are intentionally tracked and append-only where specified.

## Acceptance

Before a production change is merged:

1. private planning/state checks and public runtime static/unit checks must pass;
2. ranked-pool contract tests must prove Daily 36 / Ad-hoc 5 sizes and frozen rank semantics;
3. hard request validation must reject invalid background registry/treatment contracts without mutating the AI-authored request;
4. normal Daily canonical production must still contain exactly 24 unique Singapore hourly slots;
5. dry-run must prove no TTS, render, upload or false-receipt side effects in the private control plane;
6. production must retain durable intent and duplicate-recovery invariants;
7. current secrets must remain referenced only through GitHub Actions secret expressions;
8. the public runtime must write canonical state only to this private repository;
9. the private/public semantic contract fingerprints must remain equal;
10. schema-v5 treatment execution must remain stateless publicly and receipt-derived history must remain private.
