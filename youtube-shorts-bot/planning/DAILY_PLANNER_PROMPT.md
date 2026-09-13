# Wacky Dramas — Daily Planner

This is the canonical **Daily profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — shared bootstrap/materialization/drift contract.
2. `planning/DAILY_PLANNER_RULES.md` — Daily creative/schedule/diversity/promotion rules.
3. `planning/STORY_RULES.md`.
4. `docs/background-media-strategy.md` — canonical shared background policy.

Repository code/configuration at current `main` is authoritative. Prefer the shared **Git-first exact detached snapshot**. If Git cannot obtain the exact current-main snapshot, use the canonical **connector/API fallback**; Git metadata is not required to execute deterministic planner Python. Use `profile=daily` from the live `planning.planner_contract` output.

For any **background-specific** conflict with older profile-rule wording, the live planner contract plus `docs/background-media-strategy.md` supersede legacy single-source, schema-v5/v6, `selection_enabled`, emergency-default, short-loop, or planner-frozen-playback wording; non-background Daily rules remain mandatory.

## Mandatory checkpoints

After exact SHA-pinned planner bootstrap, run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

An empty active background registry is a normal `REPLENISH` state, not a terminal failure. If readiness is `REPLENISH`, **automatically complete the canonical replenishment path before candidate finalization**:

1. consume exact total/category/duration deficits;
2. discover licensed Pexels footage, prioritizing visually satisfying atomic clips of at least the live minimum duration (currently 60 seconds);
3. visually review every proposed source before `verified_preview=true`;
4. create exactly one immutable readiness manifest;
5. commit that manifest so Background Management performs official API enrichment/persistence;
6. refresh current `main`;
7. rerun contract + readiness;
8. repeat with a new immutable manifest if deficits remain;
9. continue Daily planning only after `PASS`.

No separate manual seed/populate step is required.

## Sequence background contract

New candidates must use the current schema and `concatenated_fit_to_short` background contract exposed by `planning.planner_contract`.

- Freeze one **primary ordered sequence** and one **backup ordered sequence**.
- Each sequence contains exactly 2-3 distinct atomic clips; 3 is preferred.
- Freeze exact logical IDs, order, segment start and segment duration for every clip.
- Each selected range must be at least the live atomic minimum (currently 60 seconds).
- Each sequence must provide 210-300 seconds total unique source coverage; 240-300 seconds is preferred.
- Primary and backup sequences must be disjoint.
- Do **not** freeze playback rate; runtime concatenates the frozen sequence once and derives one overall rate after actual TTS duration is known.
- Prefer coherent retention-first progressions across cooking/baking/food-prep/satisfying/crafting/cleaning/assembly/POV/city-motion/licensed-gameplay footage.
- Never repeat a clip to fill time and never plan intentional loops.
- Runtime may fail over only from the entire frozen primary sequence to the entire frozen backup sequence; it may not mix sequences or creatively substitute footage.
- Old pre-reset backgrounds were deleted; do not reference, recreate, or assume hidden legacy IDs.
- Avoid repeated assets, exact sequences, categories and substantially overlapping temporal ranges using verified private receipt history.

After authoring/final-ranking the complete Daily pool, run:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile daily \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha <rules_source_sha> \
  --verify-git-head
```

In connector/API fallback omit `--verify-git-head`. The gate requires **all 36 candidates PASS** before immutable commit. The compatibility wrapper `planning.daily_precommit` remains available for existing callers but contains no independent validation logic.

The final immutable pool bytes must exactly match the successful `draft_sha256`. Manual checks, downstream admission/promotion, or GitHub Actions are **not substitutes for planner-time pre-commit**.

ChatGPT/Work remains creative/editorial owner. Private workflows validate/promote mechanically; public runtime executes statelessly.
