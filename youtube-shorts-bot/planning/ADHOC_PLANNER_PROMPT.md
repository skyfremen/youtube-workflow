# Wacky Dramas — Ad-hoc Single Planner (ranked-pool contract)

This is the canonical Ad-hoc planner entry point.

Read `docs/ADHOC_PLANNER_V4_BASE.md` in full first, then read the current `planning/DAILY_PLANNER_PROMPT.md`. Preserve all Ad-hoc identity, exactly-one-production-Short, immediate-public, metadata, analytics, safety, recovery and idempotency principles except where this overlay supersedes older direct-request and planner-execution behavior.

Repository code on current `main` is authoritative. Inspect the current planning config/engine, analytics state, `validation/validate_content.py`, `planning/candidate_pool.py`, background registry/policy/history, current workflows, and public single-item contract before authoring the pool.

## Ownership

**ChatGPT / Work owns the complete Ad-hoc planning decision.** It generates and evaluates candidates, chooses story/title/voice/punchline, chooses exact logical backgrounds, applies current background-audit/fallback reasoning, chooses background treatments, and freezes a final rank order.

GitHub does not creatively re-rank, repair, or replace those choices. `adhoc-production.yml` performs mechanical validation only and promotes the first valid candidate in ChatGPT's frozen order.

There is no `planner-execution.yml` bridge in the new-plan path.

## Canonical Ad-hoc flow

```text
ChatGPT reads current repo rules/config/analytics/history/background registry
  -> generate/evaluate candidates
  -> develop exactly 5 complete production candidates
  -> rank them exactly 1..5
  -> freeze story/title/voice/punchline/backgrounds/treatments for all 5
  -> commit one immutable Ad-hoc candidate-pool JSON
  -> adhoc-production.yml
       -> global compatibility/registry preflight
       -> strictly validate all 5 candidates
       -> take the first valid candidate by frozen ChatGPT rank
       -> materialize exactly one immutable request
       -> final strict validation
       -> create one-item private execution state
       -> dispatch public single.yml
  -> YouTube immediately Public
```

If rank 1 fails validation, rank 2 is considered, then rank 3, and so on. GitHub may not change a candidate to make it pass. If all five fail, fail closed and materialize no production request.

## Ranked candidate pool contract

ChatGPT must return exactly **5 complete ranked Ad-hoc candidates**.

Write exactly one new file:

`youtube-shorts-bot/content/candidate-pools/adhoc/ap-<stable-id>.json`

The pool commit must add only that file and use commit subject:

`[adhoc production] YYYY-MM-DD`

The root contains exactly:

- `schema_version`: `1`
- `pool_type`: `"adhoc"`
- `pool_id`: exactly the filename stem, beginning `ap-`
- `rules_source_sha`: exact 40-character repository SHA whose rules/state ChatGPT read before committing
- `candidates`: exactly 5 ranked candidate envelopes

Each candidate contains exactly:

- `rank`: contiguous integer `1` through `5`
- `candidate_id`: unique stable candidate identity
- `request`: one complete schema-v5 immediate-public production candidate

Every request must use:

```json
{
  "mode": "immediate",
  "timezone": "Asia/Singapore",
  "publish_at": null
}
```

Every Ad-hoc candidate request must have a unique `content_id` containing the Ad-hoc identity marker (`-adhoc-`). All other request fields must already be final, including story, YouTube metadata, planning metadata, narration voice, semantic punchline, primary/backup backgrounds, and both treatment objects.

The five candidate requests are **not** five production Shorts. They are one immutable ranked planning pool. Only the first candidate that passes strict validation becomes the one immutable production request.

## Background audit/fallback reasoning belongs to ChatGPT

For each of the five candidates, inspect the current background registry, policy, private successful receipt history and same-pool planned usage.

ChatGPT chooses exact distinct primary/backup logical IDs and applies the current normal eligibility/audit rules itself. Final frozen assets must satisfy hard safety including registered/active/verified/commercial-use status, license/source evidence, no watermark or embedded text, current hard quality floor and a production-suitable rendition.

Apply current semantic/retention/recency/diversity reasoning as AI planning logic. If the preferred pair cannot safely be used, inspect the current configured emergency fallback pair in repository code and apply it only if it satisfies the fallback contract. Do not assume a stale pair from previous conversations.

The private validator may reject an invalid pair. It does not select another pair.

## Background treatment belongs to ChatGPT

For each candidate, freeze:

- `background_primary_treatment`
- `background_backup_treatment`

Each contains exactly `segment_start_seconds`, `segment_duration_seconds`, and `playback_rate`.

Read current `media/background_treatment.py` and successful private treatment history as planning evidence. Avoid unnecessary recent segment/speed repetition, obey current playback-rate bounds, and ensure the chosen segment fits within the asset duration.

The private validator checks these mechanical facts. It does not recalculate the treatment.

## Strict production validation and promotion

`adhoc-production.yml` runs the canonical strict request validator against all five candidates. Candidate-specific failures only remove that candidate from consideration. The workflow then promotes the first valid candidate by ChatGPT rank.

The selected final request is validated again before the one-item execution state is created and public `single.yml` is dispatched.

The workflow retains manual `workflow_dispatch(content_id)` support for an already-materialized immutable request. Manual/recovery execution does not create a new candidate pool or alter the existing request.

## Creative and analytics rules

Use the same current Wacky Dramas quality, originality, title, hook, duplicate/near-duplicate, safety and analytics rules as Daily unless the Ad-hoc base prompt explicitly differs. Use `analytics_evidence_count` as the authoritative analytics confidence input; never invent missing metrics.

The five reserve candidates must all be publishable-quality ideas. Do not create weak filler just to reach five. If the initial funnel cannot produce five candidates satisfying ChatGPT's planning gates, generate additional fresh non-duplicate premises and repeat the evaluation without weakening hard gates.

## Final ChatGPT check before commit

Confirm:

- exactly five candidate envelopes exist, ranked exactly `1..5`;
- candidate IDs and request content IDs are unique;
- every candidate uses schema v5;
- every request is immediate-public with `publish_at=null`;
- every content ID carries the Ad-hoc identity marker;
- voice/gender/tone, metadata and punchline semantics are complete;
- ChatGPT itself chose and audited primary/backup logical backgrounds;
- ChatGPT itself chose both treatment objects using current policy/history evidence;
- `rules_source_sha` is the exact repository revision used for planning;
- no planner-execution GitHub round trip is required;
- the commit contains only the one immutable candidate-pool file.

Planning ends after the candidate-pool commit. Do not render, synthesize TTS, directly upload to YouTube, create a Daily batch, or bypass `adhoc-production.yml` / public `single.yml`.
