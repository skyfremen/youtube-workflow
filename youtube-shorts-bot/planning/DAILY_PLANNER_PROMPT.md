# Wacky Dramas — Daily Planner

This is the canonical **Daily profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — canonical shared execution/materialization/drift contract.
2. `planning/DAILY_PLANNER_RULES.md` — Daily creative, schedule, diversity, analytics, promotion and recovery rules.
3. `planning/STORY_RULES.md` and the current shared background/analytics rules referenced by the Daily rules.

Repository code/configuration at current `main` remains the source of truth. If older Daily rule text repeats Git/bootstrap/materialization instructions, `docs/private/PLANNER_PROMPT.md` supersedes only those duplicated execution-environment instructions; the Daily business/creative rules remain mandatory.

A Git checkout, Git executable, `.git` directory, authenticated clone, repository archive, synthetic HEAD or GitHub Actions planner execution is not required for normal ChatGPT/Work planning. Do not use `--verify-git-head` for the canonical planner path.

## Profile

Use `profile=daily` from the live `planning.planner_contract` output.

Daily and Ad-hoc must use the same shared request/schema/semantic/background/media/narration/publication-validation implementation and the same shared-contract fingerprint. Daily-specific behavior may differ only where the `daily` profile declares it.

Do not materialize Ad-hoc-only or downstream production modules merely to run planner-time Python.

## Mandatory checkpoints

After exact SHA-pinned shared materialization, run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

Consume the actual live contract, including Daily pool size, planning modes, target rules, publication template, content/candidate identity patterns, controlled values and media readiness thresholds.

If readiness is `REPLENISH`, complete the canonical replenishment path and refresh `rules_source_sha` before candidate finalization.

After authoring/final-ranking the complete Daily pool, run the single shared precommit engine:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile daily \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha <rules_source_sha>
```

All **36 candidates must PASS** the actual validator before immutable pool commit. `planning.daily_precommit` remains only a backward-compatible wrapper and is not required for canonical materialization.

**FAIL CLOSED if the exact pre-commit module cannot be executed** after exact materialization. Manual checks, downstream pool admission, ranked promotion, or GitHub Actions are **not substitutes for planner-time pre-commit**.

Before immutable commit, re-read current `main`; if its SHA changed, refresh and rerun the shared checkpoints. The final immutable pool bytes must exactly match the successful `draft_sha256`.

ChatGPT/Work remains the creative/editorial owner and freezes Daily rank order. Private workflows validate/promote mechanically; public runtime executes statelessly.
