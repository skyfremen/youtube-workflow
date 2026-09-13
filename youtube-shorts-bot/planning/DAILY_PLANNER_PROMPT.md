# Wacky Dramas — Daily Planner

This is the canonical **Daily profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — shared bootstrap/materialization/drift contract.
2. `planning/DAILY_PLANNER_RULES.md` — Daily creative/schedule/diversity/promotion rules.
3. `planning/STORY_RULES.md`.
4. `docs/background-media-strategy.md` — canonical shared background policy.

Repository code/configuration at current `main` is authoritative. Use `profile=daily` from the live `planning.planner_contract` output.

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
9. continue Daily planning only after `PASS`.

No separate manual seed/populate step is required.

## Continuous background contract

New candidates must use the current schema and `fit_to_short` background contract exposed by `planning.planner_contract`.

- Freeze distinct primary/backup logical IDs.
- Freeze one long continuous range for each slot.
- Do **not** freeze playback rate; runtime derives it after actual TTS duration is known.
- Prefer long continuous cooking/baking/food-prep/satisfying/crafting/cleaning/assembly/POV/city-motion/licensed-gameplay footage.
- Do not plan normal short-loop footage.
- Do not use any legacy recovery registry for new planning.
- Do not invent emergency default IDs.
- Avoid repeated assets, categories and substantially overlapping temporal ranges using verified private receipt history.

After authoring/final-ranking the complete Daily pool, run:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile daily \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha <rules_source_sha> \
  --verify-git-head
```

In connector/gitless fallback omit `--verify-git-head`. The gate requires all 36 candidates PASS. Manual checks or GitHub Actions are not substitutes.

ChatGPT/Work remains creative/editorial owner. Private workflows validate/promote mechanically; public runtime executes statelessly.
