# Wacky Dramas — Daily Planner

This is the canonical **new Daily planning** entry point.

Repository code/configuration at exact current `main` is authoritative. Use the authorized GitHub connector/API. Do not use shell Git, clone/fetch/pull, DNS/proxy repair, a full checkout, or reconstruction of the planner tree.

Read only the current exact-SHA files needed for this invocation:

1. `docs/private/PLANNER_PROMPT.md` — shared four-pass execution contract.
2. `planning/PLANNER_MATERIALIZATION.json` — connector-native materialization/checkpoint contract.
3. `planning/DAILY_PLANNER_RULES.md` — Daily schedule/diversity/identity rules.
4. `planning/STORY_RULES.md` — shared story/metadata rules.
5. `docs/background-media-strategy.md` — selected-background policy.
6. Exact-SHA `planning/connector_checkpoint.py` — single mechanical planning authority.

Historical immutable pools/requests keep their historical recovery behavior. The rules below apply to **new planning**.

## Current Daily contract

For a normal full day:

```text
planning_mode = normal_next_day
target_count = 24
candidate_count = 24
reserve_candidate_count = 0
publication = canonical 24 hourly slots
```

For `same_day_catch_up`, if supported by current `main`:

```text
target_count = eligible remaining slot count
candidate_count = target_count
```

There is no 36-candidate pool, reserve walk, or first-24-valid promotion for new planning. If one required candidate has a problem, repair/regenerate that candidate while preserving the other valid candidates.

Global background readiness is **not** a planner prerequisite. Automatic planner replenishment is **disabled**. Selected-background hard validation remains mandatory. After successful immutable pool commit, ChatGPT/Work planning ends.

## Exactly four passes

### PASS 1 — contract discovery and minimal preflight

1. Resolve current `main` through the connector and freeze `rules_source_sha`.
2. Fetch the exact-SHA standalone checkpoint and resolve its `contract` output.
3. Resolve current planning mode, plan date, publication-slot contract, eligible slot count, `target_count`, `candidate_count=target_count`, schemas, identities, story/diversity rules, voice rules, selected-background rules, canonical fallback category, and checkpoint/evidence schema.
4. Inspect only targeted recent story history, analytics/editorial evidence, recent background reuse, identity state, existing-plan/idempotency state, publication-slot evidence, and registry entries needed for actual candidate backgrounds.
5. Do **not** run global media readiness, inspect replenishment sessions, start replenishment, or manually duplicate checkpoint validation.

### PASS 2 — creative authorship and semantic review

Create exactly `target_count` production-quality candidates. For a normal day this is **24**. ChatGPT owns semantic/editorial judgment: originality, near-duplicate avoidance, hook, exposition, stakes, escalation, payoff, title truth/attractiveness, spoken flow, voice suitability, punchline semantics, background suitability/readability, recent media reuse, and batch diversity across conflict/category/title/ending patterns.

Each pool candidate includes:

- complete immutable production request;
- one `background_category`;
- primary ordered background sequence;
- backup ordered background sequence;
- exact logical clip IDs, order, segment starts and segment durations.

For schema-v7 `concatenated_fit_to_short`:

- primary and backup use the candidate's **same** category;
- 2–3 distinct clips per sequence, 3 preferred;
- primary and backup are disjoint;
- no intentional looping;
- do not author/freeze playback rate; runtime derives it after actual narration/timeline duration.

Choose the best-fitting category first. If it cannot form hard-valid primary and backup sequences, try another suitable eligible category, then the canonical fallback category reported by the checkpoint contract. Fallback never relaxes hard validity.

If candidate 17 is weak or invalid, repair/regenerate candidate 17 only. Preserve unaffected good candidates. Normal recoverable story/title/voice/background failures do not terminate the planner.

### PASS 3 — one canonical deterministic checkpoint

Stage only:

- exact-SHA `connector_checkpoint.py`;
- the authored pool JSON;
- small connector evidence JSON for drift, uniqueness, publication/identity facts as required, and the exact selected background IDs.

Do not copy the full background registry locally and do not include global readiness/replenishment state.

Run:

```bash
python connector_checkpoint.py validate \
  --profile daily \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha <rules_source_sha> \
  --evidence /tmp/wacky-daily-connector-evidence.json
```

Normal full-day success requires:

```text
expected_candidates = 24
valid_candidates = 24
failed_candidates = 0
commit_allowed = true
```

Catch-up success requires `expected_candidates = valid_candidates = target_count` and zero failures.

A checkpoint failure is a repair instruction. Read the exact diagnostic, repair only affected authored input/selected assets, rebuild draft bytes if changed, refresh evidence if needed, and rerun the **same** checkpoint. Never weaken validation to obtain PASS.

### PASS 4 — drift check, immutable commit, end

Immediately before commit:

1. Re-query current `main`.
2. If `current_main_sha != rules_source_sha`, classify drift, refresh only affected rules/evidence, repair only if required, and rerun the checkpoint.
3. Require the latest checkpoint to be `PASS`, `commit_allowed=true`, and every required candidate valid.
4. Require final pool bytes to match `draft_sha256` exactly.
5. Commit exactly one immutable Daily planning-pool artifact through the authorized connector/API using the repository commit convention.
6. Confirm only that the commit succeeded.

Then **CHATGPT / WORK PLANNING ENDS**.

Do not poll private Production, public runtime, rendering, TTS, alignment, YouTube upload, or YouTube verification after pool commit. Those are downstream automation responsibilities and may be inspected only as a separate explicit task.

## Genuine terminal blockers before commit

Terminate only after safe recovery is exhausted and one of these is genuinely true: the authoritative contract cannot be accessed; the canonical checkpoint cannot be staged/executed; no hard-valid selected background configuration exists after suitable alternatives and canonical fallback are exhausted; the repository cannot accept the immutable commit after safe drift/conflict retry; or a current invariant makes production impossible.
