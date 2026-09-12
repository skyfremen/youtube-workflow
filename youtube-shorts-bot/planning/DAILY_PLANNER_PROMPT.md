# Wacky Dramas — Daily Planner (schema v5 overlay)

This is the canonical Daily planner entry point. Its business objective remains aggressive **subscriber and qualified-view growth**, including **1,000 subscribers** and **10 million qualified public Shorts views** within the rolling target window.

Read `docs/DAILY_PLANNER_V4_BASE.md` **in full** first and preserve all business, creative, analytics, metadata, scheduling, safety, publication, recovery, and background-selection rules except where this overlay explicitly supersedes older deterministic-runner, winner-selection, background-selection ownership, and Daily-count instructions.

Repository code remains the source of truth for the rules. Before planning, inspect the current `planning/planning_engine.py`, `planning/planning_config.py`, `analytics/analytics_learning.py`, `validation/validate_content.py`, `common/runtime_contract.py`, `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, `media-library/backgrounds.json`, and current workflows. Do not blindly trust stale prompt text when current code has moved forward.

## Canonical ownership

For new Daily planning runs, **ChatGPT / Work is the planner**. ChatGPT / Work owns the final editorial choice **and the exact logical background asset choice**.

ChatGPT must itself perform candidate filtering, scoring analysis, diversity reasoning, analytics interpretation, editorial comparison, final winner selection, and exact primary/backup logical background selection by applying the current repository rules. GitHub Actions must not execute `planning.raw-filter`, `planning.candidate-evaluation`, `planning.validate-selection`, `final-select`, or `background.select` on ChatGPT's behalf for a new plan.

`planning_engine.py`, `planning_config.py`, analytics code, `media/background_selector.py`, `media/background_policy.py`, the background registry, and private success history are rule/specification/evidence sources that ChatGPT reads and applies. They may remain executable for tests, regression checks, legacy recovery compatibility, or independent validation, but they do not own the new-plan creative decision path.

The canonical Daily flow is:

```text
ChatGPT reads current repo rules/config/analytics/history/background registry
  -> ChatGPT generates the raw candidate pool
  -> ChatGPT applies hard rejection and duplicate/near-duplicate rules
  -> ChatGPT develops qualified semifinalists
  -> ChatGPT applies deterministic scoring formulas and analytics evidence
  -> ChatGPT reasons about diversity, originality, payoff and viewer appeal
  -> ChatGPT chooses the complete required winner set
  -> ChatGPT replenishes candidates and repeats evaluation if the required set is not yet full
  -> ChatGPT writes the complete stories
  -> ChatGPT chooses exact primary + backup logical background IDs
  -> mechanical background audit of those exact IDs
       -> pass: keep ChatGPT pair
       -> reject: resolve only to the configured default background pair
  -> mechanical treatment allocation for the resolved IDs
  -> final schema/request validation
  -> commit immutable requests + planning audit
  -> daily-production.yml
  -> public production runtime
```

There is no repository-side planner-execution round trip between ChatGPT candidate generation and ChatGPT winner selection, and no repository-side `background.select` step that may rank/select arbitrary replacement assets. The only permitted mechanical logical-background substitution is the explicit configured default pair returned by `background.audit` after ChatGPT's pair fails audit.

A numeric score or rank is evidence, not authority. Likewise, a background selector score is evidence, not authority. ChatGPT may choose a lower-ranked eligible story or a different eligible background when semantic/editorial judgment supports it, but it must not violate hard gates, duplicate/near-duplicate restrictions, diversity constraints, selection limits, safety rules, publication-slot rules, copyright/license rules, production-suitability rules, recent-use hard avoids, or primary/backup distinctness. The configured default fallback is an emergency resilience exception to topic-fit and recent-use rejection only; it remains subject to registry, licensing, watermark/text, quality, distinctness, and production-rendition safety.

## Planning audit for new plans

For new ChatGPT-direct Daily plans, `planning_execution` records planning ownership and the chosen candidate identities without pretending that GitHub executed the planning stages:

```json
{
  "editorial_selection_owner": "chatgpt",
  "planning_method": "chatgpt_direct",
  "rules_source_sha": "<exact repository parent SHA used for planning>",
  "selected_candidate_ids": ["..."]
}
```

The private validation path must fail closed if this ownership/provenance shape is invalid or if the final requests violate the canonical request/publication/background contracts. Historical runner-provenance shapes remain readable only for compatibility/recovery of already-existing plans.

## Exact Daily count contract

The normal `normal_next_day` Daily plan is an **exact-24 contract**, not an "up to 24" target. ChatGPT must return exactly 24 valid winners and exactly 24 immutable requests, one for each hourly slot from `00:00` through `23:00` Asia/Singapore.

If the initial candidate pool does not yield 24 fully valid winners after hard rejection, duplicate checks, quality thresholds, analytics reasoning, diversity constraints, story completion, background audit/treatment, and final request validation, ChatGPT must generate additional fresh non-duplicate candidates and repeat the same canonical evaluation rules. It must continue replenishing the candidate pool until the required 24 valid winners exist. It must **not** lower hard gates, weaken diversity/safety/copyright/publication rules, resurrect rejected candidates, or use weak filler merely to reach the quota.

A normal next-day planning run has only two valid outcomes:

1. exactly 24 valid immutable requests are committed; or
2. planning fails closed and no partial Daily production commit is created.

Returning or committing 1–23 requests for `normal_next_day` is invalid. The private planning audit independently enforces this invariant before Daily production can dispatch.

`same_day_catch_up` is the only new-plan exception. Catch-up must return exactly the number of still-eligible hourly slots after the 30-minute future-slot rule is applied; it must never manufacture replacements for elapsed or too-close hours. Recovery is not replanning and may separately operate on only the unresolved subset of an already-valid immutable Daily plan.

## Preserved canonical operating rules

The normal Daily Wacky Dramas Planner runs at **20:00 Asia/Singapore** and must plan the **next Singapore calendar day**, with exact hourly slots from `00:00` through `23:00` before quality/diversity filtering. Under the exact-count contract, all 24 of those slots must be filled by valid winners before a normal Daily commit is allowed.

When manually run **before 20:00 Asia/Singapore**, use same-day catch-up for the **current Singapore calendar day**. Immediately before slot assignment and again before commit, keep only exact top-of-hour slots at least **30 minutes in the future**. Never recreate, backfill, or shift elapsed/too-close hours. At `01:35`, `02:00` is too close, so the first eligible slot is `03:00`.

If `content/planning/YYYY-MM-DD.json` already exists, do **not** create a second plan or mutate immutable requests. Use the existing content IDs through `daily-production.yml` manual `workflow_dispatch` recovery. Planning audits continue to record `planning_mode` as `normal_next_day` or `same_day_catch_up`, and catch-up audits record omitted elapsed/too-close slots.

Analytics remains evidence-gated through `analytics_evidence_count`. Do not substitute `video_count`, `published_video_count`, or `mature_video_count` for `analytics_evidence_count`.

The content handoff remains one content-only commit beginning `[daily production] YYYY-MM-DD`, consumed by `daily-production.yml`. The planning audit retains `plan_date`, `planning_mode`, `final_selected`, and `content_ids`. Any background-sourcing manifest retains exact `logical_id` and `required_by_content_ids` linkage to that day's immutable requests.

## Schema-v5 and visual allocation

New immutable production requests must use schema v5. Schema v4 remains readable only for migration/recovery of requests that already exist.

The v5 `visual` object contains exactly:

- `background_primary_id`
- `background_backup_id`
- `background_primary_treatment`
- `background_backup_treatment`

Each treatment contains exactly:

- `segment_start_seconds`
- `segment_duration_seconds`
- `playback_rate`

For each final ChatGPT-selected winner:

1. ChatGPT inspects the current logical background registry, current retention-first rules, copyright/license metadata, production suitability, private successful-receipt recency/history, and same-run planned asset/category usage.
2. ChatGPT chooses the exact `background_primary_id` and `background_backup_id` itself. The two IDs must be distinct and must satisfy all normal hard eligibility rules.
3. Run the mechanical background audit against those exact ChatGPT-chosen IDs.
4. If the audit passes normally, keep ChatGPT's exact pair. If it rejects the pair, `background.audit` may resolve only to the configured default background pair. It must not rank or select any other replacement assets.
5. If the configured default pair itself fails its fallback safety checks, fail closed.
6. Run the canonical treatment allocator for the audit-resolved IDs. Treatment allocation may choose segment boundaries and playback rate, but it must not replace either resolved logical asset.
7. Freeze the resolved logical IDs plus allocator-returned treatment objects into the immutable request. When fallback was used, preserve the audit result/evidence showing the originally requested IDs, selection errors, and `fallback_used: true`.

Persistent segment/playback history comes only from private immutable successful receipts. Do not add mutable usage fields to the logical registry or a public history ledger.

## Public runtime boundary

Do not move media probing, downloading, physical rendition selection, normalization, cropping, transcoding, FFmpeg treatment, rendering, TTS, alignment, upload, or verification into the private planner. `production-runtime` remains the heavy stateless executor.

The public runtime receives the audit-resolved primary/backup logical IDs and the frozen mechanical treatment pair. It may resolve the smallest sufficient physical rendition and execute the treatment, but it must not creatively substitute a different logical background.

Do not weaken exact source-SHA validation, dispatch/start evidence, upload intent, duplicate-upload protection, recovery, idempotency, completion receipts, public/private state ownership, dry-run boundaries, or least-privilege behavior.

## Final Daily request check

Before committing, confirm:

- `normal_next_day` contains exactly 24 winners, 24 unique content IDs, 24 immutable requests, and 24 unique hourly publication slots;
- `same_day_catch_up` contains exactly the currently eligible remaining hourly slots and no elapsed/too-close slots;
- ChatGPT itself performed filtering/evaluation/editorial selection;
- when the required winner count was initially short, ChatGPT replenished with fresh candidates rather than weakening gates or committing a partial plan;
- ChatGPT itself chose the requested primary and backup logical background IDs;
- no GitHub planner-execution action chose or filtered candidates for ChatGPT;
- no GitHub `background.select` operation chose arbitrary logical backgrounds;
- `background.audit` either preserved ChatGPT's exact pair or used only the configured default background pair;
- if fallback was used, its evidence records the requested IDs and original audit errors;
- `editorial_selection_owner` is `chatgpt` and `planning_method` is `chatgpt_direct`;
- `rules_source_sha` identifies the exact repository revision whose rules were applied;
- selected candidate IDs are unique and correspond to the final requests;
- schema version is 5;
- publication slots are valid and unique;
- primary and backup IDs are distinct registered logical assets;
- both resolved backgrounds satisfy licensing, production-suitability, and current fallback/normal policy constraints as applicable;
- treatment objects came from the canonical allocator and satisfy current bounds;
- all remaining rules from `docs/DAILY_PLANNER_V4_BASE.md` continue to apply unless explicitly superseded above.
