# Wacky Dramas — Daily Planner (schema v5 overlay)

This is the canonical Daily planner entry point. Its business objective remains aggressive **subscriber and qualified-view growth**, including **1,000 subscribers** and **10 million qualified public Shorts views** within the rolling target window.

Read `docs/DAILY_PLANNER_V4_BASE.md` **in full** first and preserve all business, creative, analytics, metadata, scheduling, safety, publication, recovery, and background-selection rules except where this overlay explicitly supersedes older deterministic-runner and winner-selection instructions.

Repository code remains the source of truth for the rules. Before planning, inspect the current `planning/planning_engine.py`, `planning/planning_config.py`, `analytics/analytics_learning.py`, `validation/validate_content.py`, `common/runtime_contract.py`, `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, `media-library/backgrounds.json`, and current workflows. Do not blindly trust stale prompt text when current code has moved forward.

## Canonical ownership

For new Daily planning runs, **ChatGPT / Work is the planner**.

ChatGPT must itself perform candidate filtering, scoring analysis, diversity reasoning, analytics interpretation, editorial comparison, and final winner selection by applying the current repository rules. GitHub Actions must not execute `planning.raw-filter`, `planning.candidate-evaluation`, `planning.validate-selection`, or `final-select` on ChatGPT's behalf for a new plan.

`planning_engine.py`, `planning_config.py`, and analytics code are the canonical rule/specification sources that ChatGPT reads and applies. They may remain executable for tests, regression checks, historical compatibility, or independent validation, but they do not own the new-plan decision path.

The canonical Daily flow is:

```text
ChatGPT reads current repo rules/config/analytics/history
  -> ChatGPT generates the raw candidate pool
  -> ChatGPT applies hard rejection and duplicate/near-duplicate rules
  -> ChatGPT develops qualified semifinalists
  -> ChatGPT applies deterministic scoring formulas and analytics evidence
  -> ChatGPT reasons about diversity, originality, payoff and viewer appeal
  -> ChatGPT chooses the final eligible winner set
  -> ChatGPT writes the complete stories
  -> mechanical background selection/audit/treatment as required
  -> final schema/request validation
  -> commit immutable requests + planning audit
  -> daily-production.yml
  -> public production runtime
```

There is no repository-side planner-execution round trip between ChatGPT candidate generation and ChatGPT winner selection.

A numeric score or rank is evidence, not authority. ChatGPT may choose a lower-scored eligible candidate when semantic/editorial judgment supports it, but it must not violate hard gates, duplicate/near-duplicate restrictions, diversity constraints, selection limits, safety rules, or publication-slot rules.

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

The private validation path must fail closed if this ownership/provenance shape is invalid or if the final requests violate the canonical request/publication contracts. Historical runner-provenance shapes remain readable only for compatibility/recovery of already-existing plans.

## Preserved canonical operating rules

The normal Daily Wacky Dramas Planner runs at **20:00 Asia/Singapore** and plans the **next Singapore calendar day**, with exact hourly slots from `00:00` through `23:00` before quality/diversity filtering. When manually run **before 20:00 Asia/Singapore**, use same-day catch-up for the current Singapore calendar day. Immediately before slot assignment and again before commit, keep only exact top-of-hour slots at least **30 minutes in the future**. Never recreate, backfill, or shift elapsed/too-close hours.

If `content/planning/YYYY-MM-DD.json` already exists, do not create a second plan or mutate immutable requests. Use existing content IDs through `daily-production.yml` manual recovery.

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

For each final ChatGPT-selected winner, use the current retention-first private background rules, mechanical background audit, and canonical treatment allocator where execution is required. Freeze the returned logical IDs and treatments into the immutable request. Background/treatment execution is mechanical media allocation, not editorial candidate selection.

Persistent segment/playback history comes only from private immutable successful receipts. Do not add mutable usage fields to the logical registry or a public history ledger.

## Public runtime boundary

Do not move media probing, downloading, physical rendition selection, normalization, cropping, transcoding, FFmpeg treatment, rendering, TTS, alignment, upload, or verification into the private planner. `production-runtime` remains the heavy stateless executor.

Do not weaken exact source-SHA validation, dispatch/start evidence, upload intent, duplicate-upload protection, recovery, idempotency, completion receipts, public/private state ownership, dry-run boundaries, or least-privilege behavior.

## Final Daily request check

Before committing, confirm:

- ChatGPT itself performed filtering/evaluation/editorial selection;
- no GitHub planner-execution action chose or filtered candidates for ChatGPT;
- `editorial_selection_owner` is `chatgpt` and `planning_method` is `chatgpt_direct`;
- `rules_source_sha` identifies the exact repository revision whose rules were applied;
- selected candidate IDs are unique and correspond to the final requests;
- schema version is 5;
- publication slots are valid and unique;
- primary and backup IDs are distinct registered logical assets;
- treatment objects satisfy current canonical bounds;
- all remaining rules from `docs/DAILY_PLANNER_V4_BASE.md` continue to apply unless explicitly superseded above.
