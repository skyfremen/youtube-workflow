# Wacky Dramas — Daily Planner (schema v5 ranked-pool contract)

This is the single canonical Daily planning instruction for Wacky Dramas. Do not use a legacy V4 base prompt or a retired repository-side planner bridge.

The business objective is aggressive subscriber and qualified-view growth, including the current target of **1,000 subscribers** and **10 million qualified public Shorts views within a rolling 90-day window**, without weakening safety, originality, copyright, immutable-state, recovery or publication guarantees.

## Repository-first rule

Before planning, inspect the current `main` branch of `skyfremen/youtube-workflow`. Repository code/configuration is authoritative when implementation details change.

Read at minimum:

- `planning/STORY_RULES.md`
- `planning/planning_config.py`
- `planning/planning_engine.py`
- `analytics/analytics_learning.py`
- current `analytics/latest.json` and `analytics/model.json` when present
- `validation/validate_content.py`
- `publishing/upload.py`
- `common/runtime_contract.py`
- `media/background_selector.py`
- `media/background_treatment.py` as a **policy/history reference**, not an authoritative allocator
- `media/background_policy.py`
- `docs/background-media-strategy.md`
- `media-library/backgrounds.json`
- recent immutable `content/requests/*.json` and verified `content/results/*.json`
- `.github/workflows/daily-production.yml`

Do not blindly reproduce old prompt arithmetic if executable/configured rules have changed.

## Canonical ownership

**ChatGPT / Work is the planner.** ChatGPT owns:

- raw premise generation and hard semantic rejection;
- duplicate/near-duplicate reasoning against recent history and the current pool;
- semantic/editorial scoring and analytics interpretation;
- exploit/explore and diversity judgment;
- semifinalist development, endings, hooks and truthful title competition;
- complete story/title/metadata authoring;
- narrator perspective, lead gender, tone and voice choice;
- semantic punchline/reveal/reversal identification;
- exact primary and backup logical background choice;
- planning-time background audit reasoning against current registry/policy/history;
- emergency-default decision when the normal pair is not safely eligible;
- background segment and playback-rate treatment decisions using current policy/history;
- final rank #1 through #36.

Private GitHub code does **not** creatively rank, select, repair, rewrite, choose replacement backgrounds or calculate replacement treatments. It validates facts and mechanically promotes candidates in ChatGPT's frozen order.

There is no `planner-execution.yml`, no `content/planner-execution/*`, and no requirement to execute `planning_runner.py` as a winner-selection authority for new ranked pools. `planning_engine.py`, configuration and historical runner code remain useful rule/regression references, not a substitute for ChatGPT's editorial rank.

## Planning date and schedule

The normal Daily planner runs at **20:00 Asia/Singapore**.

For `normal_next_day`:

- at/after 20:00 Asia/Singapore, plan the **next Singapore calendar day**;
- `target_count` is exactly **24**;
- `publication_slots` contains exactly the 24 top-of-hour slots from `00:00` through `23:00` Asia/Singapore, stored as UTC RFC3339 timestamps in chronological order;
- ChatGPT still returns exactly **36 ranked candidates**.

For `same_day_catch_up`:

- use the **current Singapore calendar day** when the canonical timing rules require catch-up;
- keep only exact top-of-hour slots at least **30 minutes in the future**;
- `target_count` equals the number of eligible remaining slots, from 1 through 24;
- `publication_slots` contains exactly those eligible slots in chronological order;
- ChatGPT still returns exactly **36 ranked candidates**;
- immediately before committing the pool, re-read Singapore time and remove any slot that is no longer at least 30 minutes away;
- `daily-production.yml` independently rechecks the 30-minute lead at promotion time, so a delayed pool fails closed rather than materializing stale requests.

If no eligible catch-up slot remains, fail closed.

If canonical `content/planning/YYYY-MM-DD.json` already exists, do **not** create another pool or mutate requests. Use existing content IDs through `daily-production.yml` manual recovery.

## Creative funnel and quality

Generate broadly before fully scripting. The current target shape remains:

`>=120 raw premises → hard semantic filtering → qualified pool → roughly 36 strong developed contenders → >=5 materially different truthful title options for serious contenders → final editorial/diversity/analytics comparison → exactly 36 fully authored ranked candidates`.

Hard rejection overrides scores. Reject unsafe, misleading, incoherent, weak-payoff, exposition-dependent, visually dependent, duplicate/near-duplicate or superficial role-swap concepts.

Use current weights, controlled attributes, diversity limits and analytics-confidence rules from `planning_config.py`/current code. A score is evidence, not authority. ChatGPT may rank a lower numeric scorer above another eligible candidate when semantic/editorial judgment supports it.

All 36 candidates must be genuine production-quality material. The 12 reserves are resilience capacity, not permission for filler.

## Story, title and metadata contract

Follow `STORY_RULES.md`. Each candidate must contain a complete original first-person story with a real setup, escalation and payoff, plus planner-authored semantic punchline metadata.

Use the current approved Kokoro mapping and one narrator per Short. Under the current contract:

- female natural/general → `af_heart`
- female expressive/funny/dramatic/sarcastic → `af_bella`
- male natural/general → `am_echo`
- male expressive/funny/dramatic/sarcastic → `am_fenrir`
- narration speed remains `1.75` unless current code/config changes it.

For every candidate author complete YouTube metadata before the pool is committed:

- title truthful, curiosity-driven, <=100 characters total and containing `#Shorts`;
- concise story-specific description, normally 1–3 short sentences;
- 3–8 visible relevant hashtags, normally including `#Shorts` and `#WackyDramas`;
- 4–12 explicit backend semantic tags without `#`;
- canonical category/made-for-kids values from current schema;
- no misleading SEO padding, competitor/channel impersonation or fabricated claims.

Use `publishing.upload.build_upload_body(..., require_future=False)` semantics as the final local payload contract. Metadata must fit YouTube payload limits after the hidden recovery marker and hashtag-derived tags are added.

## Analytics learning

Use only valid/current analytics state. Never invent Studio-only metrics. `analytics_evidence_count` is the canonical confidence input; do not substitute `video_count`, `published_video_count` or `mature_video_count`.

When evidence is weak/zero, rely mainly on editorial quality and diversity. When enabled, use normalized historical attribute evidence from `analytics_learning.py`; raw views, retention, subscriber/share/like/comment rates are not direct 0–100 story scores.

## Background audit and treatment ownership

ChatGPT must inspect the current registry, policy and private successful-receipt history and freeze final background decisions for **all 36** candidates.

For each candidate:

1. Choose distinct `background_primary_id` and `background_backup_id` values.
2. Require registered, active, verified, commercial-use-allowed, watermark/text-free assets with sufficient quality and at least one production-suitable rendition.
3. Apply retention/readability, recency, category variety and story-fit evidence as planning judgment. Visual retention/readability outranks literal reenactment.
4. If the normal pair cannot safely satisfy the rules, ChatGPT may use the current configured emergency default pair from `media/background_selector.py`; do not invent an automatic arbitrary fallback.
5. If the emergency pair itself is unsafe, reject/fix the candidate before the pool is authored.
6. Read current treatment policy/history and choose/freeze for primary and backup:
   - `segment_start_seconds`
   - `segment_duration_seconds`
   - `playback_rate`
7. Avoid recently repeated segments/rates and coordinate same-pool variety. `media/background_treatment.py` may be consulted for current policy constants/history interpretation, but ChatGPT—not that module—is the decision owner.
8. When source duration is unknown/untrusted, use the safe full-source treatment: `segment_start_seconds=0`, `segment_duration_seconds=null`, with a valid playback rate.

Private validation independently enforces hard registry/licensing/rendition/treatment facts. Validation is a **gate**, not a planner.

## Retryable immutable Daily pool contract

ChatGPT commits exactly one new immutable attempt file per planning attempt:

`youtube-shorts-bot/content/planning-pools/daily/YYYY-MM-DD/dp-<attempt-id>.json`

Use a stable sequential attempt identity such as:

- first attempt: `dp-YYYYMMDD-a01`
- second attempt after a failed promotion: `dp-YYYYMMDD-a02`
- and so on.

A failed pool is never edited or deleted. If there is no canonical Daily plan and a prior pool attempt failed, create a **new immutable attempt** with corrected/replenished candidates. Do not reuse the old path. Once canonical `content/planning/YYYY-MM-DD.json` exists, no further planning attempt is allowed for that date; use recovery instead.

Commit subject must begin:

`[daily pool] YYYY-MM-DD`

The pool shape is:

```json
{
  "schema_version": 1,
  "pool_type": "daily",
  "pool_id": "dp-YYYYMMDD-a01",
  "plan_date": "YYYY-MM-DD",
  "planning_mode": "normal_next_day",
  "target_count": 24,
  "publication_slots": ["<UTC top-of-hour timestamps>"],
  "planning_execution": {
    "editorial_selection_owner": "chatgpt",
    "planning_method": "chatgpt_ranked_pool",
    "rules_source_sha": "<exact parent SHA inspected before this pool commit>",
    "ranked_candidate_ids": ["<exact 36 IDs in rank order>"]
  },
  "ranked_candidates": [
    {
      "rank": 1,
      "candidate_id": "...",
      "request": {"...": "complete schema-v5 request template"}
    }
  ]
}
```

Requirements:

- exactly 36 candidates;
- ranks exactly `1..36`, contiguous, no ties;
- unique candidate IDs and content IDs;
- `planning_execution.ranked_candidate_ids` exactly equals candidate order;
- `rules_source_sha` equals the exact parent of the pool commit;
- every candidate uses schema v5;
- every non-publication request field is final;
- Daily candidate publication must be **exactly**:

```json
{
  "mode": "scheduled",
  "timezone": "Asia/Singapore",
  "publish_at": null
}
```

The promoter validates that exact template and changes **only `publish_at`** to the selected frozen slot. It must not silently repair mode/timezone/creative fields.

## Promotion semantics

`daily-production.yml` processes candidates only in ChatGPT's frozen rank order:

```text
#1 PASS  -> select
#2 PASS  -> select
#3 FAIL  -> skip mechanically
#4 PASS  -> select
...
```

The first `target_count` candidates that pass are promoted. Failed candidates are not repaired or re-ranked. If fewer than `target_count` pass, the attempt fails closed and no canonical production state is pushed; a later new immutable pool attempt may be authored.

For normal Daily the successful canonical outcome remains exactly **24 immutable requests** plus one canonical planning audit.

The private workflow sequence is:

```text
pool commit already on main
  -> private promotion preflight
  -> validate/rank-walk locally
  -> materialize candidate canonical state locally
  -> create local [daily production] commit
  -> rebase onto latest main
  -> final planning/request validation on the rebased local commit
  -> only then push canonical immutable production state
  -> opaque dispatch to public run.yml
```

A concurrent `main` update after final validation causes the push to fail non-fast-forward; it is never permission to publish unvalidated rebased state.

## Public runtime boundary

Do not move media download, physical rendition resolution, FFmpeg work, rendering, TTS, Wav2Vec2 alignment, upload or YouTube verification into the private planner. `production-runtime` remains the heavy stateless executor.

Preserve exact source-SHA validation, compatibility fingerprints, dispatch/start evidence, immutable upload intent, duplicate-upload protection, recovery reconciliation, result receipts, public/private state ownership and least privilege.

## Final pre-commit checklist

Before committing a Daily pool confirm:

- current repository files were inspected;
- canonical plan for the date does not already exist;
- the attempt path is new and immutable;
- exactly 36 production-quality candidates exist;
- ranks and all IDs are unique;
- normal mode target is exactly 24 with all 24 hourly slots, or catch-up slots obey the 30-minute rule;
- every candidate is schema v5 and uses the exact scheduled publication template;
- ChatGPT performed all creative/editorial ranking, background audit reasoning and treatment choices;
- backgrounds/treatments satisfy current policy/history and hard safety expectations;
- story/punchline/voice/title/metadata contracts are complete;
- no planner-execution bridge is used;
- only one new ranked-pool JSON is added in the ChatGPT commit;
- the commit subject begins `[daily pool] YYYY-MM-DD`.
