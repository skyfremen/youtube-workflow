# Wacky Dramas — Ad-hoc Planner (schema v5 ranked-pool contract)

This is the single canonical Ad-hoc planning instruction for Wacky Dramas. It shares creative, analytics, metadata, safety, background and schema rules with `DAILY_PLANNER_PROMPT.md`, but it produces exactly one immediate-public Short from a ranked pool of five complete candidates.

Do not use a legacy V4 base prompt and do not use a retired planner-execution bridge.

## Repository-first rule

Before planning, inspect the current `main` branch of `skyfremen/youtube-workflow`. Repository code/configuration is authoritative when implementation details change.

Read at minimum:

- `planning/DAILY_PLANNER_PROMPT.md`
- `planning/STORY_RULES.md`
- `planning/planning_config.py`
- `planning/planning_engine.py`
- `analytics/analytics_learning.py`
- current `analytics/latest.json` and `analytics/model.json` when present
- `validation/validate_content.py`
- `publishing/upload.py`
- `media/background_selector.py`
- `media/background_treatment.py` as a **policy/history reference**, not an authoritative allocator
- `media/background_policy.py`
- `docs/background-media-strategy.md`
- `media-library/backgrounds.json`
- recent immutable `content/requests/*.json` and verified `content/results/*.json`
- `.github/workflows/adhoc-production.yml`

Inspect `skyfremen/production-runtime` only when needed to verify the current single-item runtime/publication contract. Do not copy execution into the private repository.

## Ownership

**ChatGPT / Work owns the complete creative planning path and freezes final rank #1 through #5.** This includes candidate generation/rejection, duplicate reasoning, scoring/analytics interpretation, editorial comparison, story/title/metadata writing, voice, punchline semantics, exact backgrounds, planning-time background audit reasoning, fallback decision and treatment values.

GitHub does not creatively select or repair a winner. `adhoc-production.yml` validates candidates mechanically in the frozen AI order and promotes the first valid candidate.

There is no `planner-execution.yml`, no `planning/execution_bridge.py`, and no repository-side winner-selection round trip for new Ad-hoc pools.

## Scheduled vs manual planning modes

Every pool must explicitly declare one of two modes:

- `scheduled_daily` — the normal once-per-day 01:00 Asia/Singapore Ad-hoc run;
- `manual_on_demand` — a distinct user-requested extra Ad-hoc run.

Every pool also records `singapore_date` as `YYYY-MM-DD`.

### scheduled_daily idempotency

For a scheduled run, all five candidate content IDs must use the namespace:

`wd-YYYYMMDDT010000-adhoc-...`

where the date is `singapore_date`.

Before creating a scheduled pool, inspect existing immutable requests and ranked pools for that date. If a canonical scheduled request already exists, do not create another pool; report/recover that exact request instead.

If a previous scheduled pool attempt exists but failed before any canonical request was promoted, a new immutable pool attempt with a different `pool_id` is allowed. Never edit/delete the failed pool.

Repository-side promotion independently enforces that at most one canonical scheduled Ad-hoc request exists for a Singapore date. Ad-hoc promotion workflows are serialized, and uniqueness is rechecked after rebasing onto latest `main` before the validated request is pushed.

### manual_on_demand

Manual/on-demand pools may use a distinct stable Ad-hoc identity and may coexist with the scheduled Daily Ad-hoc request, while preserving all immutable/fail-closed/publication rules.

## Candidate quality

Use the same business objective and quality bar as Daily. Generate/evaluate enough raw ideas to make five strong, genuinely different final candidates. Hard reject unsafe, misleading, incoherent, duplicate/near-duplicate, weak-payoff or visually dependent concepts.

All five final candidates must be complete production-quality Shorts, not placeholders. Rank them editorially #1 through #5. The reserves exist only so candidate-specific validation failure does not collapse the Ad-hoc run.

Follow `STORY_RULES.md` and current Daily metadata/analytics rules. Each candidate must include complete story, title competition outcome, YouTube metadata, voice, semantic punchline, controlled planning fields, exact backgrounds and treatments.

## Background audit and treatment ownership

For all five candidates ChatGPT must inspect current registry/policy/private receipt history and freeze final background decisions.

For each candidate:

1. choose distinct primary/backup logical IDs;
2. require current registered/active/verified/commercial-use/watermark/text/quality/rendition hard facts;
3. apply retention/readability, recency and story-fit evidence as planning judgment;
4. scheduled Ad-hoc remains cache-first/cache-only unless current canonical policy explicitly changes; do not mutate Daily background-sourcing state from the scheduled Ad-hoc run;
5. when a normal pair cannot safely satisfy the rules, ChatGPT may use the current configured emergency pair only if it independently remains safe;
6. author both immutable treatments: `segment_start_seconds`, `segment_duration_seconds`, `playback_rate`;
7. avoid recently repeated segments/rates using current private receipt history;
8. `media/background_treatment.py` may be read for current treatment-policy constants/history interpretation, but its output is not an authoritative allocation decision;
9. when source duration is unknown/untrusted, use `segment_start_seconds=0` and `segment_duration_seconds=null` with a valid rate.

GitHub independently validates hard registry/licensing/rendition/treatment facts; it never invents a replacement story/background/treatment.

## Ranked-pool contract

ChatGPT commits exactly one new immutable file per Ad-hoc planning attempt:

`youtube-shorts-bot/content/planning-pools/adhoc/ap-<stable-id>.json`

The commit subject must begin:

`[adhoc pool]`

Do not directly commit a new `content/requests/*.json`. `adhoc-production.yml` materializes the one canonical request only after validation.

The pool shape is:

```json
{
  "schema_version": 1,
  "pool_type": "adhoc",
  "pool_id": "ap-<same filename stem>",
  "planning_mode": "scheduled_daily",
  "singapore_date": "YYYY-MM-DD",
  "target_count": 1,
  "planning_execution": {
    "editorial_selection_owner": "chatgpt",
    "planning_method": "chatgpt_ranked_pool",
    "rules_source_sha": "<exact parent SHA inspected before this pool commit>",
    "ranked_candidate_ids": ["<exact 5 IDs in rank order>"]
  },
  "ranked_candidates": [
    {
      "rank": 1,
      "candidate_id": "...",
      "request": {"...": "complete schema-v5 immediate-public request"}
    }
  ]
}
```

Requirements:

- exactly **5** candidates;
- ranks exactly `1..5`, contiguous and unique;
- unique candidate IDs and request content IDs;
- every content ID contains `-adhoc-`;
- `scheduled_daily` content IDs must use the exact date-scoped 01:00 namespace;
- every candidate uses schema v5;
- `planning_execution.ranked_candidate_ids` exactly matches candidate order;
- `rules_source_sha` equals the exact parent of the pool commit;
- every publication object is exactly:

```json
{
  "mode": "immediate",
  "timezone": "Asia/Singapore",
  "publish_at": null
}
```

The upload body must resolve to YouTube `privacyStatus: public` with no `publishAt` field.

## Promotion semantics

`adhoc-production.yml` processes only frozen rank order:

```text
#1 PASS -> promote #1 and stop
#1 FAIL, #2 PASS -> promote #2 and stop
...
all 5 FAIL -> fail closed
```

It must not re-rank, re-score, rewrite, fix or creatively substitute a candidate.

The private workflow sequence is:

```text
pool commit already on main
  -> private promotion preflight
  -> validate five candidates locally in AI rank order
  -> materialize one request locally
  -> create local [adhoc production] commit
  -> rebase onto latest main
  -> final schema/registry/immediate-public validation
  -> scheduled_daily uniqueness recheck on rebased state
  -> only then push the immutable request
  -> create opaque single execution
  -> dispatch public single.yml
```

A concurrent `main` update after final validation causes push failure rather than publication of unvalidated state.

## Recovery and idempotency

Once an immutable canonical Ad-hoc request exists, all retries/recovery reuse that exact content ID. Never create a replacement content ID merely because rendering/upload/verification failed.

Preserve exact source SHA, compatibility fingerprint, dispatch/start evidence, upload intent, duplicate-upload protection, receipt verification and public/private state boundaries.

Ad-hoc never consumes or modifies Daily's 24 scheduled publication slots.

## Final pre-commit checklist

Before committing an Ad-hoc pool confirm:

- current repository rules/config/analytics/history were inspected;
- exactly 5 complete production-quality candidates exist;
- ranks and IDs are unique;
- `planning_mode` and `singapore_date` are correct;
- scheduled mode has no existing canonical scheduled request for that Singapore date;
- scheduled content IDs use the correct 01:00 namespace;
- every candidate is schema v5 and immediate-public;
- ChatGPT owns all creative/editorial/background/treatment decisions;
- hard background/treatment expectations are satisfied;
- no planner-execution bridge is used;
- exactly one new immutable pool file is added;
- commit subject begins `[adhoc pool]`.
