# Wacky Dramas — Ad-hoc Planner

This is the canonical **new Ad-hoc planning** entry point.

Repository code/configuration at exact current `main` is authoritative. Use the authorized GitHub connector/API. Do not use shell Git, clone/fetch/pull, DNS/proxy repair, a full checkout, or reconstruction of the planner tree.

Read only the current exact-SHA files needed for this invocation:

1. `docs/private/PLANNER_PROMPT.md` — shared four-pass execution contract.
2. `planning/PLANNER_MATERIALIZATION.json` — connector-native materialization/checkpoint contract.
3. `planning/ADHOC_PLANNER_RULES.md` — Ad-hoc semantic/identity rules.
4. `planning/STORY_RULES.md` — shared story/metadata rules.
5. `docs/background-media-strategy.md` — selected-background policy.
6. Exact-SHA `planning/connector_checkpoint.py` — single mechanical planning authority.

Historical immutable pools/requests keep their historical recovery behavior. The rules below apply to **new planning**.

## Current Ad-hoc contract

- `planning_mode = manual_on_demand` only.
- `target_count = 1`.
- `candidate_count = 1`.
- `reserve_candidate_count = 0`.
- Publication is immediate/public using the canonical object:

```json
{"mode":"immediate","timezone":"Asia/Singapore","publish_at":null}
```

- Global background readiness is **not** a planner prerequisite.
- Automatic planner replenishment is **disabled**.
- Selected-background hard validation is mandatory.
- After successful immutable pool commit, ChatGPT/Work planning ends.

The single candidate may retain `rank = 1` for structural compatibility. There is no creative rank competition and no first-valid-of-five fallback.

## Exactly four passes

### PASS 1 — contract discovery and minimal preflight

1. Resolve current `main` through the connector and freeze `rules_source_sha`.
2. Fetch the exact-SHA standalone checkpoint and resolve its `contract` output.
3. Resolve the current pool/request schema, manual identity rules, immediate publication representation, voice rules, selected-background rules, canonical fallback background category, and checkpoint/evidence schema.
4. Inspect only targeted recent story history, analytics/editorial evidence, recent background use, identity allocation, and the registry entries needed to select actual candidate backgrounds.
5. Do **not** run global media readiness, inspect replenishment sessions, create discovery/replenishment state, or manually reproduce checkpoint validation.

### PASS 2 — creative authorship and semantic review

Create exactly **one** production-quality candidate. ChatGPT owns semantic/editorial judgment: originality, near-duplicate avoidance, hook, conflict/stakes, escalation, payoff, truthful title, spoken flow, lead gender/tone, voice suitability, punchline semantics, background suitability, visual continuity/readability, and undesirable recent reuse.

Author the complete story/title/metadata/voice/punchline request plus:

- one `background_category` on the pool candidate;
- one primary ordered sequence;
- one backup ordered sequence;
- exact logical clip IDs, order, segment starts and segment durations.

For schema-v7 `concatenated_fit_to_short`:

- both sequences use the candidate's **same** background category;
- 2–3 distinct clips per sequence, 3 preferred;
- primary and backup are disjoint;
- no intentional looping;
- do not author or freeze playback rate; runtime derives it after actual narration/timeline duration.

Choose the category that best fits the story. If it cannot form hard-valid primary and backup sequences, try another suitable eligible category. If needed, use the **canonical fallback category reported by the current checkpoint contract**. Fallback never relaxes hard validity.

If the story/title/voice/background is weak or invalid, repair or regenerate the affected part automatically. Do not terminate for a normal recoverable authoring problem.

### PASS 3 — one canonical deterministic checkpoint

Stage only:

- exact-SHA `connector_checkpoint.py`;
- the authored one-candidate pool JSON;
- small connector evidence JSON for drift, uniqueness, and the exact selected background IDs.

Selected-background evidence must satisfy the current checkpoint's hard requirements. Do not copy the full registry locally and do not include global readiness/replenishment state.

Run:

```bash
python connector_checkpoint.py validate \
  --profile adhoc \
  --pool /tmp/wacky-adhoc-pool.json \
  --rules-source-sha <rules_source_sha> \
  --evidence /tmp/wacky-adhoc-connector-evidence.json
```

Success requires:

```text
expected_candidates = 1
valid_candidates = 1
failed_candidates = 0
commit_allowed = true
```

A checkpoint failure is a repair instruction. Read the exact diagnostic, repair only the affected authored field/candidate/selected asset, rebuild the draft bytes if changed, refresh evidence if needed, and rerun the **same** checkpoint. Never weaken validation to obtain PASS.

### PASS 4 — drift check, immutable commit, end

Immediately before commit:

1. Re-query current `main`.
2. If `current_main_sha != rules_source_sha`, classify the drift, refresh only affected rules/evidence, repair only if required, and rerun the checkpoint.
3. Require the latest checkpoint to be `PASS` with `commit_allowed=true` and 1/1 valid.
4. Require final pool bytes to match the checkpoint `draft_sha256` exactly.
5. Commit exactly one immutable Ad-hoc planning-pool artifact using the authorized connector/API and repository commit convention.
6. Confirm only that the commit succeeded.

Then **CHATGPT / WORK PLANNING ENDS**.

Do not poll private Production, public runtime, rendering, TTS, alignment, YouTube upload, or YouTube verification after the pool commit. Those are downstream automation responsibilities and may be checked only in a separate explicit task.

## Genuine terminal blockers before commit

Terminate only after safe recovery is exhausted and one of these is genuinely true: the authoritative contract cannot be accessed; the canonical checkpoint cannot be staged/executed; no hard-valid selected background configuration exists after suitable alternatives and the canonical fallback are exhausted; the repository cannot accept the immutable commit after safe drift/conflict retry; or a current invariant makes production impossible.
