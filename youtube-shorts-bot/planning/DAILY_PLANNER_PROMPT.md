# Wacky Dramas — Daily Planner

This is the canonical **Daily profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — shared bootstrap/materialization/replenishment-continuation/drift contract.
2. `planning/DAILY_PLANNER_RULES.md` — Daily creative/schedule/diversity/promotion rules.
3. `planning/STORY_RULES.md`.
4. `docs/background-media-strategy.md` — canonical shared background policy.

Repository code/configuration at current `main` is authoritative. Prefer the shared Git-first exact detached snapshot. If Git cannot obtain the exact current-main snapshot, use the canonical connector/API fallback; Git metadata is not required to execute deterministic planner Python. Use `profile=daily` from the live `planning.planner_contract` output.

For any background-specific or replenishment-continuation conflict with older profile-rule wording, the live planner contract, `docs/private/PLANNER_PROMPT.md` and `docs/background-media-strategy.md` supersede legacy wording; non-background Daily rules remain mandatory.

## Mandatory checkpoints

After exact SHA-pinned planner bootstrap, run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

An empty or insufficient active background registry is a normal `REPLENISH` state, not a terminal failure. If readiness is `REPLENISH`, execute the **shared automatic resumable replenishment procedure in `docs/private/PLANNER_PROMPT.md` exactly** before candidate finalization. In particular: resume compatible unfinished attempts; do not create duplicates; do not return merely because Background Management is queued/in-progress; use the shared bounded continuation polling window; continue through visual review, readiness-manifest ingestion and the second Background Management run when they complete in-window; and report `DEFERRED_REPLENISHMENT` rather than failure only when the bounded window genuinely expires. A later scheduled Daily invocation must resume that immutable attempt from its exact continuation point rather than creating a parallel replenishment attempt.

Do not bypass discovery results by guessing provider metadata. Do not move creative/editorial review into GitHub Actions. No separate manual seed/populate step is required.

## Sequence background contract

New candidates must use the current schema and `concatenated_fit_to_short` background contract exposed by `planning.planner_contract`.

- Freeze one primary ordered sequence and one backup ordered sequence.
- Each sequence contains exactly 2-3 distinct atomic clips; 3 is preferred.
- Freeze exact logical IDs, order, segment start and segment duration for every clip.
- Each selected range must be at least the live atomic minimum.
- Each sequence must provide the live required unique source coverage; prefer the live preferred coverage.
- Primary and backup sequences must be disjoint.
- Do not freeze playback rate; runtime concatenates the frozen sequence once and derives one overall rate after actual TTS duration is known.
- Prefer coherent retention-first progressions across the live high-retention background categories.
- Never repeat a clip to fill time and never plan intentional loops.
- Runtime may fail over only from the entire frozen primary sequence to the entire frozen backup sequence; it may not mix sequences or creatively substitute footage.
- Old pre-reset backgrounds were deleted; do not reference, recreate or assume hidden legacy IDs.
- Avoid repeated assets, exact sequences, categories and substantially overlapping temporal ranges using verified private receipt history.

After authoring/final-ranking the complete Daily pool, run:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile daily \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha <rules_source_sha> \
  --verify-git-head
```

In connector/API fallback omit `--verify-git-head`. The gate requires all candidates required by the live Daily profile PASS before immutable commit. The compatibility wrapper `planning.daily_precommit` remains available for existing callers but contains no independent validation logic.

The final immutable pool bytes must exactly match the successful `draft_sha256`. Manual checks, downstream admission/promotion or GitHub Actions are not substitutes for planner-time precommit.

ChatGPT/Work remains creative/editorial owner. Private workflows validate/promote mechanically; public runtime executes statelessly.