# Wacky Dramas — Daily Planner (schema v5 ranked-pool contract)

This is the single canonical Daily planning instruction for Wacky Dramas. Do not use a legacy V4 base prompt or a retired repository-side planner bridge.

The business objective is aggressive subscriber and qualified-view growth, including the current target of **1,000 subscribers** and **10 million qualified public Shorts views within a rolling 90-day window**, without weakening safety, originality, copyright, immutable-state, recovery or publication guarantees.

## Repository-first rule

Before planning, inspect the current `main` branch of `skyfremen/youtube-workflow`. Repository code/configuration is authoritative when implementation details change.

Read at minimum:

- `planning/STORY_RULES.md`
- `planning/planning_config.py`
- `planning/planning_engine.py`
- `planning/planner_contract.py`
- `planning/daily_precommit.py`
- `analytics/analytics_learning.py`
- current `analytics/latest.json` and `analytics/model.json` when present
- `validation/validate_content.py`
- `publishing/upload.py`
- `common/runtime_contract.py`
- `media/media_readiness.py`
- `media/background_selector.py`
- `media/background_treatment.py` as a **policy/history reference**, not an authoritative allocator
- `media/background_policy.py`
- `media/pexels_registry.py`
- `docs/background-media-strategy.md`
- `media-library/backgrounds.json`
- recent immutable `content/requests/*.json` and verified `content/results/*.json`
- `.github/workflows/background-management.yml`
- `.github/workflows/daily-production.yml`

Do not blindly reproduce old prompt arithmetic if executable/configured rules have changed.

Before authoring the ranked pool, execute the current machine-readable planner contract:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
```

Consume the actual output. In particular, discover the current request schema version, Daily pool size, Daily planning modes, target count, content-ID pattern, score-component keys, controlled values, Daily publication template, and shared media-readiness inventory/category minimums from the repository rather than reproducing them from memory.

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
- readiness/replenishment candidate discovery and visual review when the shared media gate reports a deficit;
- exact primary and backup logical background choice;
- planning-time background audit reasoning against current registry/policy/history;
- emergency-default decision when the normal pair is not safely eligible;
- background segment and playback-rate treatment decisions using current policy/history;
- final rank #1 through #36.

Private GitHub code does **not** creatively rank, select, repair, rewrite, choose replacement backgrounds or calculate replacement treatments. It validates facts, enriches reviewed Pexels candidates with official physical rendition metadata, persists the shared registry, and mechanically promotes candidates in ChatGPT's frozen order.

There is no `planner-execution.yml`, no `content/planner-execution/*`, and no requirement to execute `planning_runner.py` as a winner-selection authority for new ranked pools. `planning_engine.py`, configuration and historical runner code remain useful rule/regression references, not a substitute for ChatGPT's editorial rank.

## Shared media readiness and replenishment prerequisite

**Daily and Ad-hoc use this same prerequisite.** Before fully authoring a ranked pool, execute from `youtube-shorts-bot`:

```bash
python -m media.media_readiness audit --allow-not-ready
```

Consume the actual JSON result.

If `status` is `PASS`, continue planning using only selectable assets. Any registry asset with `selection_enabled=false` is recovery-only historical state and must never be selected for new production, including as an emergency default.

If `status` is `REPLENISH`, do **not** author or commit a Daily ranked pool yet. Instead:

1. Use the current `media_readiness` values returned by `planning.planner_contract` and the audit deficits as the authoritative inventory target.
2. Search Pexels for production-appropriate continuous-motion footage, prioritizing the configured high-retention categories such as cooking, baking, food preparation, satisfying processes, crafting, cleaning, assembly, POV movement and city/travel motion.
3. Visually review every proposed source before setting `verified_preview=true`; reject watermarks, embedded text, unsafe material, static/weak footage and misleading metadata.
4. Prefer portrait footage when quality is comparable, while allowing landscape/square only when current post-crop rendition policy can satisfy 1080x1920 output without prohibited upscaling.
5. Use deterministic logical IDs `satisfying-px-<PexelsID>` and the exact sourcing-manifest schema implemented by `media/pexels_registry.py`.
6. Create exactly one new immutable replenishment manifest under:
   `content/background-sourcing/readiness/<stable-id>.json`
   containing enough reviewed candidates to satisfy the returned total/category deficits. `required_by_content_ids` must contain stable upcoming Daily candidate content IDs that motivated the replenishment.
7. Commit only that readiness manifest for the replenishment attempt. Background Management owns official Pexels API rendition enrichment, hard registry validation and persistence of the refreshed cache.
8. Re-read current `main` after Background Management has persisted the registry, rerun `planning.planner_contract`, then rerun `python -m media.media_readiness audit --allow-not-ready`.
9. Continue to ranked-pool authorship only when the new audit returns `status: PASS` and `ready: true`. If deficits remain, create a new immutable readiness-manifest attempt and repeat; never edit/delete an earlier manifest.

Do not bypass readiness, keep using a retired old background because it remains resolvable for recovery, or create a ranked pool while the registry is `REPLENISH`. Repository validation independently rejects new production against a non-ready shared registry. Existing immutable requests remain recoverable against historical background IDs.

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

ChatGPT must inspect the **readiness-PASS selectable registry**, policy and private successful-receipt history and freeze final background decisions for **all 36** candidates.

For each candidate:

1. Choose distinct `background_primary_id` and `background_backup_id` values.
2. Require selectable, registered, active, verified, commercial-use-allowed, watermark/text-free assets with sufficient quality and at least one production-suitable rendition.
3. Reject any asset with `selection_enabled=false`; those entries exist only so historical immutable requests remain recoverable.
4. Apply retention/readability, recency, category variety and story-fit evidence as planning judgment. Visual retention/readability outranks literal reenactment.
5. If the normal pair cannot safely satisfy the rules, ChatGPT may use the current configured emergency default pair from `media/background_selector.py` only if both defaults remain selectable and safe; retired defaults are not permitted.
6. If the emergency pair itself is unsafe or retired, reject/fix the candidate before the pool is authored.
7. Read current treatment policy/history and choose/freeze for primary and backup:
   - `segment_start_seconds`
   - `segment_duration_seconds`
   - `playback_rate`
8. Avoid recently repeated segments/rates and coordinate same-pool variety. `media/background_treatment.py` may be consulted for current policy constants/history interpretation, but ChatGPT—not that module—is the decision owner.
9. When source duration is unknown/untrusted, use the safe full-source treatment: `segment_start_seconds=0`, `segment_duration_seconds=null`, with a valid playback rate.

Private validation independently enforces shared readiness plus hard registry/licensing/rendition/treatment facts. Validation is a **gate**, not a planner.

## Mandatory ChatGPT pre-commit validation and repair loop

The immutable Daily pool must **not** be ChatGPT's first serialization of its work.

After ChatGPT has authored all 36 complete candidates and frozen rank order, it must first write the complete pool JSON to a **temporary working file outside `content/planning-pools/`**. That temporary file is not production state and must not be committed.

Then execute the canonical repository validator against that exact temporary file and the exact current checkout HEAD:

```bash
rules_source_sha="$(git rev-parse HEAD)"
PYTHONPATH=youtube-shorts-bot python -m planning.daily_precommit \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha "${rules_source_sha}"
```

ChatGPT must consume the actual returned JSON. The result must explicitly contain:

- `status: PASS`;
- `commit_allowed: true`;
- `expected_candidates: 36`;
- `valid_candidates: 36`;
- `failed_candidates: 0`;
- a non-empty `draft_sha256`.

This is a **36/36 requirement**. Production promotion may still skip a later-invalid reserve candidate in rank order for resilience, but ChatGPT is not allowed to commit a malformed reserve candidate in the first place.

If any candidate or pool-level check fails, ChatGPT must read the exact `pool_errors` / `candidate_results[*].errors`, repair its own temporary draft, and execute `planning.daily_precommit` again. Repeat until 36/36 pass or fail closed if the repository contract cannot be satisfied.

Do not substitute manual arithmetic, remembered field names, visual inspection, stale cached validator output, or a statement that the pool "should pass" for actual execution of the validator. In particular, ChatGPT must not guess score-component keys or content-ID syntax; the live repository contract and validator are authoritative.

Immediately before creating the immutable pool file:

1. re-read `git rev-parse HEAD` and require it to still equal the validated `rules_source_sha`;
2. rerun shared media readiness and require `status: PASS` on that same HEAD;
3. compute SHA-256 of the temporary file and require it to exactly equal the validator's `draft_sha256`;
4. copy the **exact validated bytes** into the new immutable pool path—do not reconstruct, reserialize or rewrite the JSON after validation;
5. verify the immutable destination did not already exist;
6. commit only that one new pool JSON with the required `[daily pool] YYYY-MM-DD` subject.

No PASS evidence means no immutable pool commit.

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
shared media readiness PASS
  -> pool commit already on main
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

Do not move physical media download, physical rendition resolution, FFmpeg work, rendering, TTS, Wav2Vec2 alignment, upload or YouTube verification into the private planner. `production-runtime` remains the heavy stateless executor. Background Management may call the official Pexels metadata API to enrich ChatGPT-reviewed logical candidates before planning; it does not render/download production footage.

Preserve exact source-SHA validation, compatibility fingerprints, dispatch/start evidence, immutable upload intent, duplicate-upload protection, recovery reconciliation, result receipts, public/private state ownership and least privilege.

## Final pre-commit checklist

Before committing a Daily pool confirm:

- current repository files were inspected;
- `planning.planner_contract` was actually executed and consumed;
- shared `media.media_readiness` was actually executed and returned `PASS` on current `main`;
- if replenishment was needed, it completed through an immutable readiness manifest and Background Management before pool authorship;
- canonical plan for the date does not already exist;
- the attempt path is new and immutable;
- exactly 36 production-quality candidates exist;
- ranks and all IDs are unique;
- normal mode target is exactly 24 with all 24 hourly slots, or catch-up slots obey the 30-minute rule;
- every candidate is schema v5 and uses the exact scheduled publication template;
- ChatGPT performed all creative/editorial ranking, background audit reasoning and treatment choices;
- every selected background is currently selectable and none has `selection_enabled=false`;
- backgrounds/treatments satisfy current policy/history and hard safety expectations;
- story/punchline/voice/title/metadata contracts are complete;
- `planning.daily_precommit` was actually executed against the temporary draft;
- final pre-commit validation is `PASS`, `commit_allowed=true`, and **36/36** candidates pass;
- current HEAD still equals the validated `rules_source_sha`;
- the temporary file SHA-256 still equals `draft_sha256`;
- the immutable pool receives the exact validated bytes without reserialization;
- no planner-execution bridge is used;
- only one new ranked-pool JSON is added in the ChatGPT commit;
- the commit subject begins `[daily pool] YYYY-MM-DD`.
