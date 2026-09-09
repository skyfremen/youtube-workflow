# Wacky Dramas Growth System

## Purpose

The canonical Shorts system uses a competitive daily funnel: generate broadly, reject cheaply, develop selectively, publish only winners, then feed comparable public performance back into future selection.

The system targets up to **24 Shorts per day**, one scheduled publication per hour in **Asia/Singapore**, while preserving one immutable `content_id` per story and the existing durable upload/recovery guarantees.

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
  -> immutable receipt
  -> 24h / 72h / 7d analytics snapshots
```

There is no mutable hourly queue and no hourly render cron. Publication cadence is delegated to YouTube's scheduled publication state after the selected videos are prepared in advance.

## Why 120 premises

Twenty-four final uploads should be the winners of a real competition. A five-times-larger raw pool creates room to reject duplicates, weak hooks, thin conflicts, poor payoffs and overrepresented categories without filling the day with low-quality material.

Raw candidates are cheap structured premises. They do not trigger media download, TTS, rendering or upload. Expensive production begins only after final selection.

## Scoring

Central strategy values live in `growth_config.py`. `growth_planner.py` owns deterministic arithmetic so prompt wording cannot silently change the weighting.

With no useful public performance history, selection is 100% editorial. Analytics influence rises smoothly with the number of growth-eligible public videos and is capped at 75%, preserving editorial judgment and exploration.

Missing metrics are renormalized away. They are never replaced with invented zeros or proxy values. The exact Studio viewed-vs-swiped control is not available through the targeted API used here; the separately named `engaged_view_rate` is an `engagedViews / views` continuation proxy and must never be mislabeled as that Studio metric.

## Similarity and diversity

Duplicate filtering uses premise/conflict/context/payoff/ending/opening text plus controlled structural attributes. Strong near duplicates are hard rejected; softer overlap can reduce originality during AI planning.

Final selection enforces approximate daily caps for category, core conflict and title pattern, and the scheduler avoids repeated ending/title patterns in adjacent hours when alternatives exist.

A full 24-story plan aims for roughly 19 exploit and 5 explore selections. Exploration still has to pass every hard quality, safety and truthfulness gate.

## Immutable request versions

Schema v2 remains the ad-hoc private/unscheduled compatibility path.

Schema v3 is the daily-growth path. It keeps the same canonical story/narration/visual/YouTube fields and adds:

- immutable `publication` with `mode=scheduled`, `timezone=Asia/Singapore`, exact UTC `publish_at`
- immutable `planning` metadata with scores, title competition, selected title/hook scores, analytics weight, controlled story attributes, similarity result and exploit/explore classification

The schedule is therefore bound to the same immutable request bytes and source commit as the story itself.

## Batch production and Actions cost

`daily-growth-batch.yml` processes the selected requests in one heavy container job instead of starting one full production runner each hour. This removes repeated image/container setup while retaining per-content isolation through a dedicated output directory and durable GitHub state.

The batch continues after individual failures so one bad story does not prevent already-good stories from completing. The job ultimately fails if any item failed, making the partial state visible. A rerun does not blindly upload again: each content ID first resolves its immutable receipt/upload intent/upload evidence.

The ad-hoc workflow and batch workflow share the same `wacky-dramas-youtube-upload` concurrency group, preventing overlapping YouTube insert activity.

## Upload idempotency and recovery

Before `videos.insert`, production creates an immutable durable intent containing:

- exact request identity/blob SHA/source commit
- expected channel ID
- exact upload body, including scheduled `publishAt` for schema v3
- verified render metadata and background selection
- workflow provenance

Once an intent exists, absence of a visible video is **never** permission to insert again. Recovery searches the authenticated channel for the deterministic non-viewer-facing content marker and either imports the matching upload or fails closed for operator reconciliation.

If verification happens after a scheduled video has already transitioned public, recovery may accept that state only when the durable intent proves the exact intended schedule and YouTube is not observed public before that instant.

A result receipt is created only after the exact YouTube state and render evidence verify successfully. Existing receipts are immutable and reused unchanged.

## Analytics

`analytics.py` collects the best available 90-day YouTube metrics and derives normalized rates. Private/test receipts do not increase growth confidence. Only receipts with scheduled growth planning metadata and a non-negative public age are `growth_eligible`.

The collector maintains first-available milestone snapshots after approximately 24 hours, 72 hours and 7 days. Future planning should compare comparable ages instead of ranking a two-hour-old video against a week-old video by raw views.

Receipt planning metadata allows analysis by category, conflict, emotion, roles, opening style, title style, ending style and target duration without uncontrolled free-text taxonomies.

## Daily content commit

The external daily planner follows `planner/DAILY_GROWTH_PROMPT.md` and creates exactly one immutable planning audit plus 1–24 immutable schema-v3 request files in one content-only commit whose message begins:

`[daily growth] YYYY-MM-DD`

That commit is routed to the batch workflow. The ad-hoc workflow explicitly ignores it.

## Acceptance and safe rollout

Before recurring planning is enabled:

1. branch/static compilation and all unit tests must pass
2. growth acceptance must generate at least 120 raw premises
3. hard rejection, title/hook scoring, analytics cold-start and diversity must execute
4. selected requests must have unique Singapore hourly slots
5. dry-run must prove no TTS, render, upload or false receipt side effects
6. production workflow must retain the durable intent/duplicate-recovery invariant
7. current secrets must remain referenced only through GitHub Actions secret expressions

Recurring production should remain disabled until those checks pass on `main`.
