# Wacky Dramas — Ad-hoc Planner (schema v5 ranked-pool overlay)

This is the canonical Ad-hoc single-Short planner entry point.

Read `docs/ADHOC_PLANNER_V4_BASE.md` in full first, then the current `planning/DAILY_PLANNER_PROMPT.md`. Preserve all existing Ad-hoc identity, immediate-public publication, metadata, recovery, idempotency, safety and architecture rules except where this overlay explicitly supersedes older one-request planning, deterministic-runner, bridge, background-audit/treatment and winner-selection behavior.

Repository code is authoritative. Inspect the current `planning/planning_engine.py`, `planning/planning_config.py`, `planning/ranked_promotion.py`, `analytics/analytics_learning.py`, `validation/validate_content.py`, `common/runtime_contract.py`, `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, current background registry/history and workflows before authoring the pool.

## Canonical ownership

**ChatGPT / Work performs the complete creative planning path and freezes the rank order.** ChatGPT owns:

- candidate generation and hard rejection;
- duplicate/near-duplicate reasoning;
- scoring/analytics/editorial comparison;
- complete story/title/metadata writing;
- narrator/voice choice;
- semantic punchline/reveal/reversal identification;
- exact primary/backup logical background choice;
- background-audit reasoning against current registry/policy/history;
- emergency-default decision when necessary;
- background segment and playback-rate treatment values;
- final rank #1 through #5.

GitHub does not creatively select or repair a winner. `adhoc-production.yml` only validates the five candidates mechanically in the frozen AI rank order and promotes the first valid one.

There is no `planner-execution.yml` bridge and no `planning/execution_bridge.py` planning round trip.

## Canonical Ad-hoc flow

```text
ChatGPT reads current repo rules/config/analytics/history/background registry
  -> generates/evaluates candidates
  -> hard filtering + duplicate checks
  -> complete story development
  -> scoring/analytics/editorial comparison
  -> ChatGPT chooses/audits exact backgrounds itself
  -> ChatGPT chooses treatment values itself
  -> writes exactly 5 complete candidates
  -> freezes rank #1 through #5
  -> commits one immutable Ad-hoc ranked-pool JSON
  -> adhoc-production.yml
       -> global fail-first preflight
       -> validate candidates mechanically in rank order
       -> promote first valid candidate
       -> materialize exactly one immutable request
       -> final canonical request validation
       -> public single.yml
       -> YouTube immediately Public
```

The four reserve candidates are fallback planning candidates only. They are not production requests and must not be uploaded unless every higher-ranked candidate before them failed mechanical validation.

## Ranked-pool contract

ChatGPT commits exactly one file:

`youtube-shorts-bot/content/planning-pools/adhoc/ap-<stable-id>.json`

The commit subject must begin:

`[adhoc pool]`

Do **not** commit a new `content/requests/*.json` yourself. `adhoc-production.yml` owns request materialization after validation.

The pool contains exactly:

```json
{
  "schema_version": 1,
  "pool_type": "adhoc",
  "pool_id": "ap-<same filename stem>",
  "target_count": 1,
  "planning_execution": {
    "editorial_selection_owner": "chatgpt",
    "planning_method": "chatgpt_ranked_pool",
    "rules_source_sha": "<exact parent SHA whose rules were used>",
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
- ranks exactly `1..5` with no ties;
- unique candidate IDs and request content IDs;
- every content ID contains `-adhoc-`;
- every request is a complete schema-v5 production-quality candidate;
- publication for every candidate is exactly:

```json
{
  "mode": "immediate",
  "timezone": "Asia/Singapore",
  "publish_at": null
}
```

- `planning_execution.ranked_candidate_ids` exactly matches the five candidate IDs in rank order;
- `rules_source_sha` is the exact repository revision ChatGPT inspected; the pool commit parent must equal that SHA.

For a scheduled once-per-day Ad-hoc run, use a stable deterministic pool identity for that Singapore calendar date and obey existing idempotency rules: if that scheduled pool/request already exists, do not create another copy. Manual/on-demand Ad-hoc creation may use a distinct stable purpose/id while still remaining immutable.

## Promotion semantics

`adhoc-production.yml` processes candidates only in frozen rank order:

```text
#1 PASS -> promote #1 and stop
#1 FAIL, #2 PASS -> promote #2 and stop
...
all 5 FAIL -> fail closed
```

It must not re-rank, re-score, rewrite, fix or creatively substitute a candidate. Validation failure simply moves to the next already-authored reserve.

Exactly one request is materialized and dispatched to public `single.yml`.

## Background audit and treatment ownership

For all five candidates, ChatGPT itself must inspect the current registry, policy and private success history and author the final background pair/treatments.

For each candidate:

1. choose distinct `background_primary_id` and `background_backup_id` values;
2. apply current registered/active/verified/commercial-use/watermark/text/quality/rendition hard rules;
3. apply current retention/topic fit/recency/diversity evidence as planning judgment;
4. when a normal pair cannot safely satisfy the rules, ChatGPT may use the current configured emergency default pair from `media/background_selector.py`; no automatic arbitrary replacement exists;
5. if the emergency pair itself is not safe, do not present that candidate as production-quality;
6. read current treatment rules/history and freeze `segment_start_seconds`, `segment_duration_seconds`, and `playback_rate` for both backgrounds;
7. respect asset duration, playback bounds, anti-repetition intent and candidate-pool treatment diversity.

GitHub's strengthened request validator independently enforces hard registry/licensing/production/treatment invariants. This is a gate only; it does not choose the background or treatment.

## Schema-v5 and immediate-public contract

Every candidate request uses schema v5. The v5 `visual` object contains exactly:

- `background_primary_id`
- `background_backup_id`
- `background_primary_treatment`
- `background_backup_treatment`

Each treatment contains exactly:

- `segment_start_seconds`
- `segment_duration_seconds`
- `playback_rate`

The upload body for the promoted request must resolve to `privacyStatus: public` with no future `publishAt`.

Ad-hoc production never consumes or changes Daily's scheduled hourly slots.

## Fail closed

Fail closed when:

- ChatGPT cannot confidently apply the current rules;
- fewer than five production-quality reserve candidates can be authored;
- the pool schema/provenance is invalid;
- all five mechanically fail validation;
- runtime contract/dispatch/start/recovery requirements fail.

Failing closed must never mean allowing deterministic code to invent a replacement story, background or treatment.

## Final pre-commit checklist

Before committing the Ad-hoc pool, confirm:

- exactly 5 complete production-quality candidates exist;
- ranks are exactly 1..5 and all IDs are unique;
- ChatGPT itself performed all creative/editorial ranking;
- ChatGPT itself chose/audited backgrounds and authored treatments;
- every publication object is immediate-public;
- `planning_method` is `chatgpt_ranked_pool`;
- `rules_source_sha` is the exact current revision used for planning;
- no planner-execution bridge is used;
- exactly one immutable pool file is added;
- the commit subject begins `[adhoc pool]`;
- all remaining Ad-hoc/base rules continue to apply unless explicitly superseded here.
