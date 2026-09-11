# Wacky Dramas — Daily Ad-hoc Single Planner

This is the canonical ChatGPT / Work instruction for the scheduled **single-Short ad-hoc production path**.

It complements, but does not replace, the normal daily batch planner in `planning/DAILY_PLANNER_PROMPT.md`.

The objective is to create **exactly one additional strong Wacky Dramas Short per scheduled run**, using the same current creative rules, analytics learning, deterministic planning code, immutable request contract, background policy, metadata contract, and private → public execution architecture as the normal daily planner.

This path must never accidentally invoke the 24-Short daily batch dispatcher.

---

## 1. Repository-first rule

Before doing any planning, inspect the current `main` branch of `skyfremen/youtube-workflow`.

Do not assume this prompt's schema version, counts, thresholds, filenames, workflow inputs, controlled values, voices, analytics rules, publication rules, or implementation details are still current.

Read and follow the current repository as the source of truth.

At minimum, read the current versions of:

- `planning/DAILY_PLANNER_PROMPT.md`
- `planning/STORY_RULES.md`
- `planning/planning_config.py`
- `planning/planning_engine.py`
- `planning/planning_runner.py`
- `analytics/analytics_learning.py`
- `analytics/latest.json` when present/current
- `analytics/model.json` when present/current
- `media/background_policy.py`
- `media/background_selector.py`
- `media-library/backgrounds.json`
- `publishing/upload.py`
- recent immutable requests under `content/requests/`
- recent verified results under `content/results/`
- `.github/workflows/adhoc-production.yml`

Inspect `skyfremen/production-runtime` only as needed to verify the current single-item public execution contract and request schema. Do not copy production execution back into the private repository.

If this prompt conflicts with current executable repository code or the current daily planner's shared business rules, follow the repository and report the conflict.

---

## 2. Scheduled-run identity and idempotency

This planner is intended to be invoked by ChatGPT Scheduler at **01:00 Asia/Singapore every day**.

Resolve the current Singapore date and time at the start of the run.

For the scheduled calendar date, use a deterministic ad-hoc request identity namespace beginning with:

`wd-YYYYMMDDT010000-adhoc-`

Before generating anything, search current immutable requests for an existing request in that date's scheduled ad-hoc namespace.

If one already exists:

1. Do **not** create a second request.
2. If a verified successful result/receipt already exists for that content ID, report the existing completion and stop.
3. If no successful result exists, use the existing content ID through the canonical private `adhoc-production.yml` workflow so recovery/idempotency operates on the original immutable identity.
4. Never create a replacement content ID merely because execution failed.

This scheduled planner must produce **at most one new immutable request per Singapore calendar date**.

---

## 3. Shared business objective

Use the same Wacky Dramas business objective and creative standards as the current daily planner.

Optimize for subscriber growth and qualified Shorts views without weakening originality, quality, diversity, safety, truthfulness, or the immutable/recovery architecture.

Ad-hoc content should complement the normal daily batch rather than superficially cloning a recent winner.

Do not restore retired Wacky Insights rules or branding.

---

## 4. Use the same canonical planning intelligence

ChatGPT / Work owns semantic and creative judgment.

Repository code owns deterministic policy.

Use the same current candidate fields, scoring components, controlled values, analytics model, duplicate checks, title rules, hook rules, story rules, voice rules, background rules, and metadata validation used by the normal daily planner.

Do not manually reproduce canonical arithmetic when executable repository code is available.

### Raw candidate checkpoint

Generate at least the current configured `RAW_CANDIDATE_COUNT` raw premises using the current planning configuration.

Supply all semantic/editorial fields required by the current code and the real recent-history comparison set.

Actually execute the current canonical runner's raw-filter checkpoint, currently:

```bash
PYTHONPATH=youtube-shorts-bot python youtube-shorts-bot/planning/planning_runner.py \
  --stage raw-filter \
  --input /tmp/wacky-dramas-adhoc-raw-input.json \
  --output /tmp/wacky-dramas-adhoc-raw-result.json
```

Consume the actual `result.qualified_candidates` output.

Do not develop hard-rejected or near-duplicate candidates.

### Semifinalist development

From the qualified pool, creatively develop up to the current configured semifinalist target using the same quality standard as the daily planner.

For each developed semifinalist, provide all fields required by the current deterministic final-selection implementation, including a concrete ending, outline/opening, hook components, controlled attributes, and the required materially different truthful title candidates.

Use current analytics exactly as required by the repository. Never invent missing metrics and never replace the canonical analytics scoring implementation with manual arithmetic.

### Final deterministic checkpoint

Actually execute the current canonical final-select runner, currently:

```bash
PYTHONPATH=youtube-shorts-bot python youtube-shorts-bot/planning/planning_runner.py \
  --stage final-select \
  --input /tmp/wacky-dramas-adhoc-final-input.json \
  --output /tmp/wacky-dramas-adhoc-final-result.json
```

Consume the actual returned result.

For this single-Short ad-hoc path, the **authoritative winner is the first candidate returned in `result.selected`** by the successful deterministic final-select execution.

Only that one candidate may proceed to full script/request creation. All other returned candidates are discarded for this run and must not be committed.

If `result.selected` is empty, fail closed and create no request.

Do not substitute a preferred candidate after deterministic selection.

The daily planner's hourly `publication` value attached by final selection is **not** authoritative for this ad-hoc path; ad-hoc publication timing is assigned separately by the rules below. All scoring, title, hook, analytics, selection-class, similarity and controlled-attribute results must remain consistent with the selected candidate.

---

## 5. Ad-hoc publication timing

The normal daily batch may occupy every exact top-of-hour slot, so this scheduled ad-hoc path must avoid the daily cadence.

Unless current repository policy has changed, choose the earliest unoccupied **half-hour Singapore slot (`HH:30`)** that satisfies all of the following:

- it is at least **4 hours in the future** at the moment of final pre-commit validation;
- it does not duplicate any `publication.publish_at` already present in immutable requests;
- it satisfies the current upload/scheduling contract;
- it does not use a top-of-hour slot reserved for normal daily production.

For a healthy run starting at 01:00 SGT, this will normally make **05:30 SGT** the earliest candidate slot, subject to collision and validation checks.

If that slot is occupied, move to the next safe half-hour slot.

If no safe same-day half-hour slot remains, continue into the next Singapore day using the same half-hour, collision, and minimum-future-buffer rules.

Immediately before committing, re-read current Singapore time and revalidate the chosen publication timestamp. Do not silently keep a slot that has become unsafe.

---

## 6. Full story and immutable request

Write exactly one complete Wacky Dramas story for the authoritative winner using the current daily story rules.

Freeze every current request field required by the latest canonical request schema, including as applicable:

- channel identity
- story category/type/hook/script
- lead gender and story tone
- approved narrator voice and speed
- primary and backup background IDs
- YouTube title, description, hashtags and semantic tags
- scheduled publication
- deterministic planning scores and selected-title information
- selection class/reason
- similarity evidence
- controlled planning attributes
- target duration

Prefer the current canonical schema used for new production requests. Do not deliberately create a legacy request merely because older immutable requests remain supported.

Generate the content ID in the scheduled ad-hoc namespace and ensure the request filename stem exactly matches `content_id`.

---

## 7. Background policy for scheduled ad-hoc production

Use **cache-first, cache-only** background selection for this scheduled single-Short path.

Read the current verified background registry and select two genuinely suitable, distinct, caption-safe cached assets using the same semantic, freshness and quality rules as the daily planner.

Do not create or mutate the normal daily `content/background-sourcing/YYYY-MM-DD.json` manifest from this ad-hoc run. That file is immutable daily state and may already exist from the 24-Short plan.

If two suitable verified cached backgrounds cannot be selected safely, fail closed and create no request.

---

## 8. Validate before commit

Before committing, run all current applicable request and production-payload validations.

At minimum, use the current canonical request schema/guard and the current upload-body contract. For the upload-body contract, use the repository implementation rather than reproducing title/description/tag arithmetic manually.

Validate that:

- the request uses the current canonical production schema for new requests;
- content ID and request path agree;
- story fields and controlled values are valid;
- narrator voice matches the frozen lead gender/tone policy;
- primary and backup backgrounds are distinct and valid;
- YouTube metadata and final tag/description limits pass;
- publication is scheduled, future and collision-free;
- deterministic planning fields match the actual selected candidate;
- no existing immutable production JSON is modified.

Fail closed on any validation error.

---

## 9. Commit only one new request

Commit exactly one new immutable request under the current canonical request path.

Do not create the normal daily planning audit for this ad-hoc run.

Do not modify existing immutable requests, results, recovery records, completions, diagnostics, upload evidence, or daily planning/background-sourcing files.

Use a commit message that clearly identifies ad-hoc production and **does not contain `[daily production]`**. A suitable convention is:

`[adhoc production] YYYY-MM-DD`

The request-path push may cause the private `Daily Production` workflow definition to be evaluated, but its production-dispatch job must not be activated by this ad-hoc commit marker.

---

## 10. Dispatch only the canonical ad-hoc execution path

After the one immutable request is committed, trigger the private:

`.github/workflows/adhoc-production.yml`

using exactly the new or pre-existing scheduled ad-hoc `content_id`.

Do not use `daily-production.yml` for the single-Short execution.

Do not directly dispatch the public repository when the private dispatcher is available.

The intended execution chain is:

```text
ChatGPT / Work
    ↓
create/reuse exactly one immutable request
    ↓
private adhoc-production.yml
    ↓
opaque single-item execution manifest
    ↓
public production-runtime/single.yml
    ↓
validate → generate → render → verify → upload
    ↓
YouTube scheduled publication
    ↓
completion / diagnostic state back to private
```

Preserve current source-SHA validation, compatibility validation, immutable request identity, upload intent, duplicate-upload protection, receipt verification, recovery reconciliation, idempotency, public/private boundaries and fail-closed behavior.

---

## 11. Verify the handoff

After dispatching, verify as far as the current execution allows that:

1. the private Ad-hoc Production workflow accepted the content ID;
2. the immutable single-item execution manifest was created;
3. public `single.yml` was dispatched;
4. the public run actually started;
5. completion or diagnostic state is returned when available during the current execution.

If execution fails after the immutable request exists, preserve and recover the same content identity. Do not create a second story/request for the same scheduled date.

---

## 12. Final report

Report at minimum:

- Singapore plan/run date
- content ID
- selected title
- category
- publication time in Asia/Singapore
- narrator voice
- primary and backup background IDs
- request schema actually used
- analytics enabled/active cohort/evidence summary according to current repository semantics
- private commit SHA
- private ad-hoc workflow status
- public single-workflow start/status
- YouTube video ID and scheduled publication state if available
- recovery/diagnostic state if applicable

If the run creates no new request, report the canonical reason: existing completed request, existing request requiring recovery, no deterministic winner, insufficient cached backgrounds, unsafe publication timing, validation failure, or another current fail-closed condition.
