# Wacky Dramas — Ad-hoc Planner

This is the canonical **Ad-hoc profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — shared bootstrap/materialization/drift contract.
2. `planning/ADHOC_PLANNER_RULES.md` — Ad-hoc creative/identity/promotion rules.
3. `planning/STORY_RULES.md`.
4. `docs/background-media-strategy.md` — canonical shared background policy.

Repository code/configuration at current `main` is authoritative. Use `profile=adhoc` from the live `planning.planner_contract` output. For any **background-specific** conflict with older profile-rule wording, the live planner contract plus `docs/background-media-strategy.md` supersede legacy schema-v5, `selection_enabled`, emergency-default, short-window, or planner-frozen-playback wording; non-background Ad-hoc rules remain mandatory.

## Mandatory checkpoints

After exact SHA-pinned planner bootstrap, run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

An empty active background registry is a normal `REPLENISH` state, not a terminal failure. If readiness is `REPLENISH`, **automatically complete the canonical replenishment path before candidate finalization**:

1. consume exact total/category/duration deficits;
2. discover licensed long continuous Pexels footage;
3. visually review every proposed source before `verified_preview=true`;
4. create exactly one immutable readiness manifest;
5. commit that manifest so Background Management performs official API enrichment/persistence;
6. refresh current `main`;
7. rerun contract + readiness;
8. repeat with a new immutable manifest if deficits remain;
9. continue Ad-hoc planning only after `PASS`.

No separate manual seed/populate step is required.

## Continuous background contract

New candidates must use the current schema and `fit_to_short` background contract exposed by `planning.planner_contract`.

- Freeze distinct primary/backup logical IDs and one long continuous range for each slot.
- Do **not** freeze playback rate; runtime derives it after actual TTS duration is known.
- Prefer long continuous retention-first footage; reject normal short-loop footage.
- Do not use the legacy recovery registry or hard-coded emergency background IDs for new planning.
- Avoid repeated assets, categories and substantially overlapping temporal ranges using verified private receipt history.

After authoring the complete five-candidate ranked pool, run:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile adhoc \
  --pool /tmp/wacky-adhoc-pool.json \
  --rules-source-sha <rules_source_sha> \
  --verify-git-head
```

In connector/gitless fallback omit `--verify-git-head`. The gate requires all five candidates PASS.

For `manual_on_demand`, distinct same-date invocations may coexist. For `scheduled_daily`, preserve current once-per-date uniqueness. Every promoted Ad-hoc request remains immediate-public according to the live profile contract.

ChatGPT/Work remains creative/editorial owner. Private promotion preserves frozen rank order; public runtime executes statelessly.
