# Wacky Dramas — Daily Planner (schema v5 ranked-pool overlay)

This is the canonical Daily planner entry point. Its business objective remains aggressive **subscriber and qualified-view growth**, including **1,000 subscribers** and **10 million qualified public Shorts views** within the rolling target window.

Read `docs/DAILY_PLANNER_V4_BASE.md` **in full** first and preserve all business, creative, analytics, metadata, scheduling, safety, publication, recovery, and content-quality rules except where this overlay explicitly supersedes older deterministic-runner, request-commit, background-audit/treatment ownership, and Daily-count instructions.

Repository code remains the source of truth. Before planning, inspect the current `planning/planning_engine.py`, `planning/planning_config.py`, `planning/ranked_promotion.py`, `analytics/analytics_learning.py`, `validation/validate_content.py`, `common/runtime_contract.py`, `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, `media-library/backgrounds.json`, current private success history, and current workflows. Do not blindly trust stale prompt text when current code has moved forward.

## Canonical ownership

For new Daily planning runs, **ChatGPT / Work is the planner**. ChatGPT owns:

- candidate generation and hard rejection;
- duplicate/near-duplicate reasoning;
- scoring/analytics interpretation;
- diversity/editorial comparison;
- complete story/title/metadata writing;
- narrator/voice decisions;
- semantic punchline/reveal/reversal identification;
- exact primary and backup logical background choice;
- background-audit reasoning against the current private registry/policy/history;
- emergency-default decision when the normal pair is not safely eligible;
- background segment and playback-rate treatment decisions using the current treatment rules/history;
- the final **rank order** of the complete candidates.

GitHub does **not** creatively rank, select, repair, rewrite, choose a background, or calculate a replacement treatment. GitHub only validates the frozen AI-authored candidates in rank order and mechanically promotes the first candidates that pass.

There is no `planner-execution.yml` bridge. Do not create `content/planner-execution/inputs/*` or wait for repository-side background-audit/treatment results.

## Canonical Daily flow

```text
ChatGPT reads current repo rules/config/analytics/history/background registry
  -> generates and evaluates the creative pool
  -> applies hard rejection and duplicate/near-duplicate rules
  -> develops strong complete candidates
  -> applies scoring/analytics/diversity/editorial reasoning
  -> chooses exact backgrounds itself
  -> performs background-audit reasoning itself
  -> chooses segment/playback treatment values itself
  -> writes exactly 36 complete candidates
  -> freezes rank #1 through #36
  -> commits one immutable Daily ranked-pool JSON
  -> daily-production.yml
       -> global fail-first preflight
       -> validate candidates mechanically in frozen rank order
       -> promote first target_count valid candidates
       -> normal_next_day: first 24 valid
       -> materialize canonical planning JSON + exactly 24 immutable requests
       -> validate canonical production commit again
       -> public run.yml
       -> YouTube
```

The reserve candidates exist only to absorb candidate-specific validation failures. They are **not** additional production requests. For normal Daily, 36 planning candidates become exactly 24 immutable production requests.

## Ranked-pool contract

ChatGPT must commit exactly one file:

`youtube-shorts-bot/content/planning-pools/daily/YYYY-MM-DD.json`

The commit subject must be:

`[daily pool] YYYY-MM-DD`

Do **not** commit `content/planning/YYYY-MM-DD.json` or `content/requests/*.json` yourself for a new plan. `daily-production.yml` owns materialization of canonical production state after validation.

The ranked-pool JSON contains exactly these top-level fields:

```json
{
  "schema_version": 1,
  "pool_type": "daily",
  "plan_date": "YYYY-MM-DD",
  "planning_mode": "normal_next_day",
  "target_count": 24,
  "publication_slots": ["<UTC top-of-hour timestamps>"],
  "planning_execution": {
    "editorial_selection_owner": "chatgpt",
    "planning_method": "chatgpt_ranked_pool",
    "rules_source_sha": "<exact parent SHA whose rules were used>",
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

- `ranked_candidates` contains **exactly 36** entries.
- `rank` is exactly `1..36`, contiguous, with no ties.
- candidate IDs are unique.
- request `content_id` values are unique.
- every request is fully authored for content, metadata, narration, punchline semantics, backgrounds, and treatments.
- Daily candidate request publication is a template only; use `mode=scheduled`, `timezone=Asia/Singapore`, and `publish_at=null`. The private promotion gate assigns the exact frozen `publication_slots` in rank-selection order before canonical validation.
- all 36 must be genuine production-quality candidates. Do not deliberately include weak filler merely because 12 are reserves.

`planning_execution.ranked_candidate_ids` must exactly equal the candidate IDs in `ranked_candidates` order. `rules_source_sha` must be the exact repository revision ChatGPT inspected before committing the pool; the pool commit's parent must equal that SHA.

## Daily target and publication-slot contract

For `normal_next_day`:

- plan the next Singapore calendar day when running at/after 20:00 Asia/Singapore;
- `target_count` is exactly **24**;
- `publication_slots` contains exactly the 24 canonical hourly slots from `00:00` through `23:00` Asia/Singapore, represented as UTC timestamps in chronological order;
- ChatGPT still returns exactly **36 ranked candidates**.

For `same_day_catch_up`:

- use the current Singapore calendar day when the canonical timing rules require catch-up;
- keep only exact top-of-hour slots at least 30 minutes in the future;
- `target_count` equals the number of eligible remaining slots, from 1 through 24;
- `publication_slots` contains exactly those eligible slots in chronological order;
- ChatGPT still returns exactly **36 ranked candidates** so candidate-specific validation failure does not unnecessarily collapse the catch-up run.

If no eligible catch-up slot remains, fail closed and do not create a pool.

If the canonical `content/planning/YYYY-MM-DD.json` already exists, do not create a second Daily pool or mutate immutable requests. Use the existing content IDs through `daily-production.yml` manual recovery.

## Promotion semantics — rank is authority

`daily-production.yml` must never make an editorial choice. It processes the 36 candidates in ChatGPT's frozen rank order:

```text
#1 PASS  -> select
#2 PASS  -> select
#3 FAIL  -> reject mechanically
#4 PASS  -> select
...
#25 PASS -> used only if an earlier candidate failed
```

The first `target_count` candidates that pass are promoted. Failed candidates are skipped; later candidates keep their original AI rank. If fewer than `target_count` candidates pass, fail closed. Never weaken validation, change rank order, repair a failed candidate, or ask deterministic code to choose a creative replacement.

For normal Daily, the only successful production outcome remains **exactly 24 immutable requests**.

## Background audit and treatment ownership

ChatGPT itself must inspect current registry/policy/history and decide the final background pair and treatment values for every one of the 36 candidates.

For each candidate:

1. Choose distinct `background_primary_id` / `background_backup_id` values.
2. Apply current hard eligibility rules: registered, active, verified, commercial-use allowed, watermark/text free, sufficient quality, production-suitable rendition, and any current normal anti-repetition/safety constraints.
3. Apply current retention/topic/diversity evidence as planning judgment.
4. If the normal pair cannot safely satisfy the rules, ChatGPT may choose the current configured emergency default pair from `media/background_selector.py`; do not invent a different automatic fallback.
5. If even the configured emergency pair is not safe, that candidate must not be presented as valid production-quality reserve material.
6. Read the current treatment policy/history and choose/freeze:
   - `segment_start_seconds`
   - `segment_duration_seconds`
   - `playback_rate`
7. Respect current asset duration, playback bounds, anti-repetition intent, and same-run treatment diversity.

GitHub's strengthened request validator independently checks hard registry/licensing/production/treatment invariants. That validation is a **gate**, not a planner.

## Schema-v5 request contract

New candidates use schema v5. The `visual` object contains exactly:

- `background_primary_id`
- `background_backup_id`
- `background_primary_treatment`
- `background_backup_treatment`

Each treatment contains exactly:

- `segment_start_seconds`
- `segment_duration_seconds`
- `playback_rate`

All non-publication request fields must already be final in the pool. Promotion may assign only the scheduled `publish_at` slot and persist the already-authored request; it must not rewrite creative fields.

## Analytics and creative rules

Analytics remains evidence-gated through `analytics_evidence_count`; do not substitute `video_count`, `published_video_count`, or `mature_video_count`. Preserve all current candidate-funnel, scoring, diversity, title, duration, narration, safety, originality and metadata rules from the base prompt/current code unless explicitly superseded here.

A score is evidence, not authority. ChatGPT may rank a lower-scoring eligible story above another when semantic/editorial judgment supports it, provided all hard rules remain satisfied.

## Public runtime boundary

Do not move media downloading, physical rendition selection, probing, normalization, cropping, transcoding, FFmpeg execution, rendering, TTS, alignment, upload, or verification into the private planner. `production-runtime` remains the heavy stateless executor.

The public runtime receives only the already-promoted immutable requests. It executes frozen background IDs/treatments and must not creatively substitute another logical asset.

Do not weaken exact source-SHA validation, dispatch/start evidence, upload intent, duplicate-upload protection, recovery, idempotency, completion receipts, public/private state ownership, dry-run boundaries, or least-privilege behavior.

## Final pre-commit checklist

Before committing the ranked pool, confirm:

- exactly 36 complete ranked candidates exist;
- ranks are exactly 1..36 and candidate/content IDs are unique;
- every candidate is production-quality, not filler;
- ChatGPT itself performed creative/editorial selection and ordering;
- ChatGPT itself chose/audited backgrounds and authored treatment values;
- no planner-execution bridge is used;
- `planning_method` is `chatgpt_ranked_pool`;
- `rules_source_sha` is the exact current repository revision used for planning;
- normal next-day target is 24 with all 24 canonical hourly slots;
- catch-up target/slots obey the 30-minute future rule;
- every candidate uses schema v5 and current metadata/narration/punchline/background contracts;
- the only new file in the ChatGPT commit is the immutable ranked-pool JSON;
- commit subject is exactly `[daily pool] YYYY-MM-DD`;
- all remaining rules from `docs/DAILY_PLANNER_V4_BASE.md` continue to apply unless explicitly superseded above.
