# Wacky Dramas — Daily Planner (ranked-pool contract)

This is the canonical Daily planner entry point. The business objective remains aggressive **subscriber and qualified-view growth**, including **1,000 subscribers** and **10 million qualified public Shorts views** within the rolling target window.

Read `docs/DAILY_PLANNER_V4_BASE.md` in full first. Preserve its business, creative, analytics, metadata, safety, originality, diversity and publication principles except where this file explicitly supersedes older runner ownership, background execution, final-count and commit-shape instructions.

Repository code on the current `main` branch is the source of truth. Before planning, inspect the current `planning/planning_engine.py`, `planning/planning_config.py`, `analytics/analytics_learning.py`, `validation/validate_content.py`, `planning/candidate_pool.py`, `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, `media-library/backgrounds.json`, current private successful receipts, and current workflows. Do not trust stale filenames, constants or architecture descriptions.

## Ownership

**ChatGPT / Work owns planning and creative choice.** It must itself perform candidate generation, hard filtering, duplicate/near-duplicate reasoning, scoring analysis, analytics interpretation, diversity reasoning, story development, editorial ranking, title/story writing, voice choice, semantic punchline identification, logical background choice, background-audit reasoning, fallback choice when required, and background treatment choice.

GitHub must not creatively re-rank or replace a story, logical background, or treatment. The private production workflow may only validate candidates mechanically and promote them in the rank order already frozen by ChatGPT.

The current `planning_engine.py`, `background_selector.py`, `background_treatment.py` and related code are **rules/evidence sources for ChatGPT**, plus regression/reference implementations. There is no `planner-execution.yml` round trip and no repository-side creative background/treatment allocator in the new-plan path.

## Canonical Daily flow

```text
ChatGPT reads current repo rules/config/analytics/history/background registry
  -> generate the configured broad raw pool
  -> hard rejection + duplicate/near-duplicate reasoning
  -> develop qualified semifinalists
  -> scoring + analytics + diversity/editorial comparison
  -> build exactly 36 complete production candidates
  -> rank them exactly 1..36
  -> for every candidate, ChatGPT chooses story/title/voice/punchline/backgrounds/treatments
  -> commit one immutable ranked Daily candidate-pool JSON
  -> daily-production.yml
       -> global compatibility/registry preflight
       -> strictly validate all 36 candidates
       -> preserve ChatGPT rank; take the first target-count candidates that pass
       -> normal_next_day target = exactly 24
       -> materialize only those selected immutable request JSONs
       -> assign the exact Daily publication slots mechanically in selected rank order
       -> final strict validation
       -> create one canonical final planning JSON + final immutable requests
       -> dispatch public run.yml using the promotion commit SHA
  -> public runtime renders/uploads/verifies
```

A failed candidate is skipped. GitHub may not repair it, lower a gate, re-rank the pool, invent a replacement story, choose another background, or recalculate a treatment. If fewer than the required target pass strict validation, fail closed and create **no partial final production batch**.

## Ranked candidate pool contract

For every new Daily planning run ChatGPT returns **exactly 36 complete ranked candidates**, regardless of whether the production target is 24 or a smaller same-day catch-up target.

Write exactly one new file:

`youtube-shorts-bot/content/candidate-pools/daily/YYYY-MM-DD.json`

The pool commit must add only that file. Its commit subject must be:

`[daily production] YYYY-MM-DD`

The pool root contains exactly:

- `schema_version`: `1`
- `pool_type`: `"daily"`
- `plan_date`: same date as filename
- `planning_mode`: `normal_next_day` or `same_day_catch_up`
- `target_count`: number of final publication slots
- `rules_source_sha`: exact 40-character repository SHA whose rules/state ChatGPT read before committing the pool
- `publication_slots`: exact UTC RFC3339 timestamps ending `Z`
- `candidates`: exactly 36 ranked candidate envelopes

Each candidate envelope contains exactly:

- `rank`: contiguous integer `1` through `36`; this order is authoritative
- `candidate_id`: unique stable candidate identity
- `request`: a complete schema-v5 production candidate except that Daily `publication.publish_at` is intentionally `null` until promotion assigns a slot

Every Daily candidate request must use this publication template:

```json
{
  "mode": "scheduled",
  "timezone": "Asia/Singapore",
  "publish_at": null
}
```

All other required request fields must already be complete, including story, narration, YouTube metadata, planning metadata, punchline semantics, distinct logical background IDs, and both full background treatment objects. Candidate `content_id` values must be unique and production-safe; do not use acceptance/test/smoke/dry-run/ad-hoc identity markers.

The candidate pool is immutable planning state. It is **not** itself a public-runtime batch. `daily-production.yml` materializes the final immutable production requests only after validation.

## Daily counts and scheduling

### Normal next-day

At or after 20:00 Asia/Singapore, plan the next Singapore calendar day. `normal_next_day` requires:

- exactly **36 ranked candidates** in the pool;
- `target_count = 24`;
- exactly 24 unique `publication_slots`, corresponding to Singapore local `00:00` through `23:00`, each converted to UTC;
- production succeeds only if at least 24 of the 36 candidates pass strict validation.

The private workflow promotes the first 24 valid candidates by ChatGPT rank and assigns those 24 slots in chronological order. Final production remains exactly 24 immutable requests.

### Same-day catch-up

Before 20:00, preserve the current same-day catch-up rule. Include only exact Singapore top-of-hour slots at least 30 minutes in the future. `target_count` must equal the number of listed eligible slots. ChatGPT still supplies exactly 36 ranked candidates. Immediately before promotion the private workflow rechecks the 30-minute safety window and mechanically drops any slot that has become too close; it never manufactures a replacement time.

If no safe slot remains, do not create a pool. If fewer valid candidates remain than the final safe target, production fails closed.

## Background choice and audit reasoning now belong to ChatGPT

For every one of the 36 candidates, ChatGPT must inspect the current registry, hard eligibility policy, private successful-receipt history and same-pool planned usage before freezing backgrounds.

ChatGPT chooses exact distinct:

- `background_primary_id`
- `background_backup_id`

ChatGPT must apply the current background audit rules itself. At minimum, the final frozen assets must be registered, active, verified, commercial-use eligible, watermark-free, embedded-text-free, above the current hard quality floor, and have a production-suitable rendition. Apply the current retention/semantic/recency/diversity reasoning as planning logic rather than delegating it to GitHub.

If ChatGPT's preferred pair does not satisfy the current normal rules, apply the currently configured emergency fallback policy from repository code. At the time this contract was authored the configured pair is `satisfying-001` / `satisfying-002`, but **always inspect current code rather than trusting this sentence**. The fallback itself must satisfy all hard production-safety checks.

GitHub's later strict validator may reject an invalid final pair, but it does not choose another pair.

## Background treatment now belongs to ChatGPT

For every candidate ChatGPT also freezes:

- `background_primary_treatment`
- `background_backup_treatment`

Each contains exactly:

- `segment_start_seconds`
- `segment_duration_seconds`
- `playback_rate`

Read and apply the current `media/background_treatment.py` logic and private successful-treatment history as evidence. Avoid unnecessary recent segment/speed repetition across the ranked pool. Respect current playback-rate bounds and asset duration. The chosen segment must physically fit inside the selected logical asset.

GitHub later checks those facts mechanically. It does not recalculate or substitute treatment values.

## Strict production validation

`daily-production.yml` runs the canonical strict request validator. The validator is intentionally mechanical. It checks schema/publication/content invariants plus hard registered-background and treatment safety, including registry existence, active/verified/commercial-use status, license/source evidence, watermark/text flags, hard quality floor, production-suitable rendition, treatment numeric bounds, and treatment fit within asset duration.

A candidate that fails is simply unavailable for promotion. The workflow takes the next valid candidate by frozen rank. If fewer than the final target pass, fail closed.

After promotion, all selected requests are validated again before public dispatch.

## Planning and analytics rules

Preserve the current scoring, title competition, duplicate, diversity and explore/exploit rules from the repository/base prompt. Numeric scoring is evidence; ChatGPT retains editorial ownership subject to hard gates.

Use only canonical analytics state. The authoritative confidence input is `analytics_evidence_count`; do **not** substitute `video_count`, `published_video_count`, or `mature_video_count`. Missing metrics are not invented.

For the 36 ranked candidates, diversity must be considered across the whole candidate pool, with special attention to the top 24 because those are most likely to be promoted. Reserve candidates must still be genuinely strong; do not use weak filler simply to reach 36.

If the creative funnel initially yields fewer than 36 fully developed candidates satisfying ChatGPT's planning gates, generate additional fresh non-duplicate premises and repeat the same evaluation. Do not weaken quality/safety/copyright/diversity rules or resurrect rejected candidates.

## Final ChatGPT check before candidate-pool commit

Confirm all of the following:

- exactly 36 candidate envelopes exist and ranks are exactly `1..36`;
- candidate IDs and request content IDs are unique;
- every candidate is a complete schema-v5 story/request candidate;
- every candidate has a complete punchline semantic object;
- every candidate has a canonical Kokoro voice consistent with lead gender/tone;
- primary/backup logical backgrounds are distinct and ChatGPT has applied current audit/fallback reasoning;
- both AI-authored treatment objects obey current policy and asset duration;
- Daily publication is the scheduled/null-slot template in every candidate;
- root publication slots and target count are correct for the planning mode;
- `rules_source_sha` is the exact repository revision used for planning;
- no `planner-execution.yml`, `background.audit`, `background.treatment` or `request.validate` GitHub round trip is required before the pool commit;
- the commit contains only the one immutable candidate-pool file.

Planning ends after this pool commit. ChatGPT must not render, synthesize TTS, upload directly to YouTube, or bypass `daily-production.yml` / public `run.yml`.
