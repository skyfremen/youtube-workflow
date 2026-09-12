# Wacky Dramas — Daily Ad-hoc Single Planner

This is the canonical ChatGPT / Work instruction for the scheduled **single-Short ad-hoc production path**.

It complements, but does not replace, `DAILY_PLANNER_PROMPT.md`. The goal is to create **exactly one additional strong Wacky Dramas Short per scheduled run**, using the same current creative rules, analytics learning, deterministic planning code, immutable request contract, background policy, metadata contract, recovery guarantees, and private → public execution architecture as the normal daily planner.

The defining difference is publication behavior: this ad-hoc Short is uploaded **immediately as Public** once production and verification reach the upload stage. It is not assigned a future YouTube `publishAt` time and must never consume or alter the 24-Short daily schedule.

This path must never accidentally invoke the 24-Short daily batch dispatcher.

## Repository-first rule

Before planning, inspect the current `main` branch of `skyfremen/youtube-workflow`. Do not assume this prompt's schema version, counts, thresholds, filenames, workflow inputs, controlled values, voices, analytics rules, publication representation, or implementation details remain current.

Read and follow the current repository as the source of truth. At minimum read:

- `planning/DAILY_PLANNER_PROMPT.md` for shared Wacky Dramas business and creative rules
- `planning/STORY_RULES.md`
- `planning/planning_config.py`
- `planning/planning_engine.py`
- `planning/planning_runner.py`
- `analytics/analytics_learning.py`
- current `analytics/latest.json` and `analytics/model.json` when present
- `media/background_policy.py`
- `media/background_selector.py`
- `docs/background-media-strategy.md`
- `media-library/backgrounds.json`
- `publishing/upload.py`
- `validation/validate_content.py`
- recent immutable `content/requests/*.json`
- recent verified `content/results/*.json`
- `.github/workflows/adhoc-production.yml`

Inspect `skyfremen/production-runtime` only as needed to verify the current single-item execution and immediate-public contract. Do not copy production execution back into the private repository.

If this prompt conflicts with current executable repository code, follow the repository and report the conflict.

## Scheduled-run identity and idempotency

This planner is intended to run at **01:00 Asia/Singapore every day**.

Resolve the current Singapore date and time at the start. For that Singapore date, use a deterministic namespace beginning with:

`wd-YYYYMMDDT010000-adhoc-`

Before generating anything, search immutable requests for an existing request in that date's scheduled ad-hoc namespace.

If one exists, do not create another. If a verified successful result already exists, report it and stop. If no successful result exists, reuse that exact content ID through the canonical private `adhoc-production.yml` path so recovery/idempotency operates on the original immutable identity. Never create a replacement content ID merely because execution failed.

Produce **at most one new immutable request per Singapore calendar date**.

## Planning intelligence

Use the same business objective and quality bar as the current daily planner. Ad-hoc content should complement the daily batch, not superficially clone a recent winner.

ChatGPT / Work owns semantic and creative judgment. Repository code owns deterministic policy.

Generate at least the current configured raw-candidate count, provide the semantic/editorial fields required by current code, and actually execute the canonical raw-filter checkpoint through `planning/planning_runner.py`. Consume the actual `result.qualified_candidates`; do not develop hard-rejected or near-duplicate candidates.

Develop semifinalists according to current repository policy, including concrete endings, openings/hooks, controlled attributes, title candidates and analytics inputs required by current code.

Actually execute the canonical `final-select` checkpoint through `planning/planning_runner.py`. Consume the actual returned result. For this single-Short path, the authoritative winner is the **first candidate returned in `result.selected`**. Only that candidate may proceed. If the selected list is empty, fail closed and create no request.

The daily planner's deterministic hourly `publication` value is not authoritative for this ad-hoc path. Preserve all deterministic scoring, title, hook, analytics, selection-class, similarity and controlled-attribute results, but replace publication with the current canonical immediate-public representation defined by the request/upload contract.

## Immediate-public publication contract

The new ad-hoc request must represent **immediate public publication** using the current canonical request schema.

Under the current contract this is expected to mean:

```json
{
  "publication": {
    "mode": "immediate",
    "timezone": "Asia/Singapore",
    "publish_at": null
  }
}
```

Do not invent or retain a future `publish_at` value for this path. Immediately before commit, validate the exact request and upload body through current repository code. The canonical upload body for an immediate request must resolve to YouTube `privacyStatus: public` with **no `publishAt` field**.

If current executable code no longer uses the representation above, use the current code's equivalent immediate-public representation instead.

## Full story and immutable request

Write exactly one complete Wacky Dramas story for the authoritative winner using current shared story rules.

Freeze every field required by the latest canonical request schema, including channel identity, story, lead gender/tone, narrator voice/speed, primary and backup backgrounds, YouTube title/description/hashtags/tags, immediate-public publication, deterministic planning scores, selected-title information, selection class/reason, similarity, controlled attributes and target duration.

Prefer the current canonical schema for new requests; do not deliberately create a legacy schema merely because older immutable requests remain supported.

Generate a content ID in the scheduled ad-hoc namespace and ensure the request filename stem exactly equals `content_id`.

## Background policy

Use **cache-first, cache-only** background selection for this scheduled single-Short path. Read `media/background_selector.py` and `docs/background-media-strategy.md`, then choose two distinct, caption-safe verified registered logical assets using the same retention-first policy as daily planning.

Prefer strong continuous visual motion such as cooking, baking, food preparation, satisfying processes, crafting, cleaning, assembly, POV movement, or city/travel motion. The clip does not have to literally depict the story. Topic relevance is a secondary boost; it must not override a materially stronger retention/readability candidate. Apply private receipt-derived recency/use/category history so the ad-hoc Short also avoids recently overused footage.

Do not create or mutate `content/background-sourcing/YYYY-MM-DD.json` from this ad-hoc run. If two suitable cached logical backgrounds cannot be selected safely, fail closed and create no request. Do not source random gameplay or creator footage from social platforms; `licensed_gameplay` is eligible only with explicit recorded commercial-use provenance.

The public runtime remains responsible for physical rendition resolution, cache lookup, download, probing, post-crop quality validation, one-time normalization and rendering. Preserve the 1080×1920/30fps **smallest-sufficient-after-crop** rule. Do not request the largest/provider-original rendition. A 1920×1080 landscape source may be insufficient after the portrait crop, while UHD landscape is permitted only when crop geometry genuinely requires it.

The current request schema freezes only logical primary/backup IDs. Do not invent persistent segment, category-history, or playback-treatment fields and do not make the public runtime stateful to compensate.

## Validation before commit

Run every current applicable request and production-payload validation. Use the repository implementation, not manually reproduced arithmetic.

Validate at minimum that the current request schema passes; content ID/path agree; story and controlled values are valid; voice matches lead gender/tone; backgrounds are distinct/valid; metadata limits pass; deterministic planning fields match the selected candidate; immediate-public publication resolves to `privacyStatus: public` with no `publishAt`; and no existing immutable production JSON is modified.

Fail closed on any validation error.

## Commit and dispatch

Commit exactly one new immutable request under the canonical request path. Do not create the normal daily planning audit. Do not modify existing immutable requests, results, recovery records, completions, diagnostics, upload evidence or daily planning/background-sourcing files.

Use a commit message that **does not contain `[daily production]`**. Use:

`[adhoc production] YYYY-MM-DD`

After commit, trigger only the private `.github/workflows/adhoc-production.yml` using the new or pre-existing ad-hoc `content_id`.

Do not use `daily-production.yml`. Do not directly dispatch the public repository when the private dispatcher is available.

The intended chain is:

```text
ChatGPT / Work
    ↓
create/reuse exactly one immutable immediate-public request
    ↓
private adhoc-production.yml
    ↓
opaque single-item execution manifest
    ↓
public production-runtime/single.yml
    ↓
validate → generate → render → verify → upload
    ↓
YouTube immediately Public
    ↓
completion / diagnostic state back to private
```

Preserve source-SHA validation, contract validation, immutable identity, upload intent, duplicate-upload protection, receipt verification, recovery reconciliation, idempotency, public/private boundaries and fail-closed behavior.

## Verify the handoff

Verify as far as the current execution allows that the private Ad-hoc Production workflow accepted the content ID, the immutable single-item execution manifest was created, public `single.yml` was dispatched and actually started, and completion/diagnostic state is returned when available.

If execution fails after the immutable request exists, recover the same content identity. Do not create a second request for the same scheduled date.

## Final report

Report the Singapore run date, content ID, selected title/category, narrator voice, primary/backup background IDs, request schema, analytics summary, private commit SHA, private ad-hoc workflow status, public single-workflow status/start evidence, YouTube video ID, confirmed Public state if available, and recovery/diagnostic state if applicable.

If no new request is created, report the canonical reason: existing completed request, existing request requiring recovery, no deterministic winner, insufficient cached backgrounds, validation failure, or another fail-closed condition.
