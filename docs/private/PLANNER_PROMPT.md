# Wacky Dramas — Shared Planner Execution Contract

Daily and Ad-hoc are profiles of one planner. Repository code/configuration at exact current `main` is authoritative. The authorized GitHub connector/API is the canonical ChatGPT/Work repository source; shell Git is neither attempted nor required.

This document describes **new planning**. Historical immutable pools, requests, recovery artifacts and older schemas retain their historical compatibility behavior.

## Guiding principle

```text
semantic / creative decision
→ ChatGPT / Work

mechanical / structural validation
→ one canonical deterministic checkpoint

recoverable failure
→ repair / retry / regenerate / substitute / fallback / revalidate

successful immutable pool commit
→ planner ends
```

Normal recoverable problems are not terminal planner results.

## Repository-first identity

1. Resolve exact current `main` through the authorized GitHub connector/API.
2. Freeze the lowercase 40-character SHA as `rules_source_sha`.
3. Read only the current exact-SHA profile rules, story/background rules, machine-readable materialization contract, standalone `planning/connector_checkpoint.py`, and targeted state required by the current invocation.
4. Stage locally only the standalone checkpoint, authored pool JSON and small connector-evidence JSON required by the current checkpoint contract.

Do not require or attempt shell Git, clone/fetch/pull/ls-remote, worktrees, GitHub DNS/proxy repair, a full repository checkout, a reconstructed planner module tree, or a local copy of the complete background registry merely to plan.

`CHECKPOINT_STAGING_BLOCKED` is legal only when the exact-SHA standalone checkpoint cannot actually be fetched, staged or executed. Absence of Git/DNS/checkout is not a ChatGPT/Work blocker.

## Profile cardinality

### Ad-hoc

```text
planning_mode = manual_on_demand
target_count = 1
candidate_count = 1
reserve_candidate_count = 0
publication = immediate/public
```

New Ad-hoc planning does not support `scheduled_daily`.

### Daily

Normal full day:

```text
planning_mode = normal_next_day
target_count = 24
candidate_count = 24
reserve_candidate_count = 0
```

Same-day catch-up, when supported by current `main`:

```text
target_count = eligible_slot_count
candidate_count = target_count
```

There is no new-planning first-valid reserve walk. If a required candidate is weak or invalid, repair/regenerate that candidate while preserving unaffected valid candidates.

## Background policy for planning

Global media-library readiness is **not** a prerequisite for Daily or Ad-hoc planning. A repository-wide `REPLENISH` state, total inventory deficit, category inventory deficit, sequence-capacity deficit or historical replenishment session does not by itself block a new planner invocation.

Normal Daily/Ad-hoc planning does not create, resume, wait for or interpret planner-bound replenishment sessions, discovery attempts, readiness manifests/events or attempt loops. Background discovery/review/maintenance tooling may remain available as a **separate media-library maintenance workflow**, independent of the planner.

Removing global readiness does not weaken selected-media validation. Every background actually referenced by an authored pool must satisfy the current hard requirements, including registration, selectability, active/verified/visual-reviewed state, commercial-use eligibility, watermark/text rules, trusted duration, production rendition, quality/retention rules, valid segment ranges and schema compatibility.

For each schema-v7 candidate:

- ChatGPT chooses one `background_category`;
- every primary and backup clip must belong to that same category;
- each ordered sequence contains 2–3 distinct clips, 3 preferred;
- primary and backup are disjoint;
- exact logical IDs, order, segment starts and segment durations are frozen;
- no intentional looping is allowed;
- ChatGPT does **not** choose, calculate or freeze playback rate;
- runtime derives playback rate after the actual narration/timeline duration is known.

Selection fallback is:

```text
preferred suitable category
→ another suitable eligible category
→ canonical fallback category exposed by the exact-SHA checkpoint contract
```

Fallback never relaxes hard selected-asset validation.

## Exactly four ChatGPT / Work passes

### PASS 1 — contract discovery and minimal preflight

Resolve `rules_source_sha`, current profile/cardinality/publication contract, current schemas/controlled values/voice rules, selected-background rules and canonical fallback configuration. Load only targeted recent story history, analytics/editorial learning, recent background use, identity/uniqueness state and Daily slot evidence that materially affects this invocation.

PASS 1 is evidence collection, not a manual validation pass. Do not run global background readiness, inspect replenishment history, start replenishment, reproduce schema validation or build a second mechanical checklist.

### PASS 2 — creative authorship and semantic review

Author exactly the candidates actually required by the profile. ChatGPT/Work owns originality, semantic duplicate reasoning, hook/conflict/stakes/escalation/payoff/ending quality, truthful title quality, spoken flow, lead gender/tone, voice appropriateness, punchline semantics, background category suitability, visual continuity/readability, undesirable recent background reuse and Daily batch diversity.

If a story/premise/title/voice/background choice is weak, repair or regenerate the affected input automatically. For Daily, preserve already-good candidates instead of restarting the batch.

PASS 2 may use the contract to author correct values but must not manually prove candidate-count arithmetic, regexes, enum membership, publication JSON exactness, sequence arithmetic/disjointness or other facts covered by PASS 3.

### PASS 3 — one canonical deterministic checkpoint

Assemble small connector evidence with:

- repository and exact `rules_source_sha`;
- checkpoint blob identity;
- drift evidence valid for the checkpoint moment;
- profile uniqueness/identity evidence;
- only the exact selected background IDs and the hard-valid facts required by the checkpoint.

Do not include global `media_readiness` or replenishment state in current evidence and do not copy the complete background registry merely to validate the pool.

Run:

```bash
python connector_checkpoint.py validate \
  --profile <daily|adhoc> \
  --pool <pool.json> \
  --rules-source-sha <rules_source_sha> \
  --evidence <connector-evidence.json>
```

The checkpoint is the single mechanical planning authority. A failure is normally an actionable repair instruction:

```text
read exact diagnostic
→ identify affected authored candidate/field/selected asset
→ repair only what is necessary
→ rebuild draft bytes if changed
→ refresh affected connector evidence if needed
→ rerun the same checkpoint
```

Never weaken/bypass validation simply to obtain PASS. A successful checkpoint supersedes manual re-verification of the mechanical rules it covers.

### PASS 4 — drift check, immutable commit, end

Immediately before commit:

1. Re-query current `main` through the connector/API.
2. Compare it with `rules_source_sha`.
3. If relevant drift occurred, refresh only affected rules/evidence, repair authored content only when necessary and rerun the canonical checkpoint.
4. Require the latest checkpoint to show `PASS`, `commit_allowed=true` and every required candidate valid.
5. Require final pool bytes to exactly match checkpoint `draft_sha256`.
6. Commit exactly one immutable planning-pool artifact using the authorized connector/API and repository commit convention.
7. Confirm only that the immutable pool commit succeeded.

Then **CHATGPT / WORK PLANNING ENDS**.

Do not wait for private Production, canonical request materialization, public runtime, TTS, forced alignment, FFmpeg, YouTube upload or YouTube verification after a successful pool commit. Those are downstream automation responsibilities and may be inspected later only as a separate explicit task.

## Automatic recovery rules

Normal creative/mechanical failures are recoverable:

- weak/duplicated/confusing/poorly sized story → repair or regenerate that candidate;
- weak title/metadata/punchline field → repair that field;
- invalid voice value → read current voice contract and choose the appropriate valid value;
- preferred category unavailable → try another suitable eligible category, then canonical fallback;
- one selected clip invalid → replace it with another hard-valid clip from the same chosen category;
- sequence invalid → rebuild the affected sequence;
- checkpoint failure → repair exact failure and rerun;
- repository drift → refresh affected rules/evidence and revalidate;
- retryable commit conflict → refresh main, apply drift policy, revalidate if needed and retry safely.

Do not force-push, overwrite immutable state or model ordinary repairable failures as terminal outcomes.

## Genuine terminal blockers before commit

The planner may terminate before a successful commit only after safe recovery has genuinely been exhausted, for example:

1. the authoritative current repository contract cannot be accessed;
2. the mandatory standalone checkpoint cannot be fetched/staged/executed;
3. no hard-valid selected-background configuration can be formed after suitable alternate categories/assets and the canonical fallback have all been exhausted;
4. the authorized repository cannot accept the immutable commit after safe retry/drift recovery;
5. a current repository invariant makes the requested production state genuinely impossible.

Report the exact blocker rather than a generic `validation failed` message.

## Ownership and downstream boundary

ChatGPT/Work owns the creative result. Repository code must not creatively rewrite, rerank or replace authored stories/background choices. The standalone checkpoint and repository validators own deterministic validation.

Private production workflows may perform deterministic defense-in-depth validation, immutable request materialization and dispatch. Historical schema-v1 pools retain their historical compatibility path. Public `production-runtime` remains stateless and receives the same immutable schema-v7 request shape; candidate `background_category` is planning-pool metadata and is not added to the runtime request.
