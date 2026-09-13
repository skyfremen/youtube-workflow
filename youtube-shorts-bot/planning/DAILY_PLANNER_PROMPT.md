# Wacky Dramas — Daily Planner

This is the canonical **Daily profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — canonical shared Git-first/bootstrap/materialization/drift contract.
2. `planning/DAILY_PLANNER_RULES.md` — Daily creative, schedule, diversity, analytics, promotion and recovery rules.
3. `planning/STORY_RULES.md` and current shared background/analytics rules referenced by the Daily rules.

Repository code/configuration at current `main` remains the source of truth. If older Daily rule text repeats bootstrap/materialization instructions, `docs/private/PLANNER_PROMPT.md` supersedes only those duplicated execution-environment instructions; Daily business/creative rules remain mandatory.

Prefer the shared contract's **Git-first exact detached snapshot** and reuse an existing authorized clone when possible. If Git cannot obtain and verify current `main`, use the exact-SHA connector/API fallback in `planning/PLANNER_MATERIALIZATION.json`. GitHub Actions planner execution is prohibited.

## Profile

Use `profile=daily` from the live `planning.planner_contract` output.

Daily and Ad-hoc must use the same shared request/schema/semantic/background/media/narration/publication-validation implementation and the same shared-contract fingerprint. Daily-specific behavior may differ only where the `daily` profile declares it.

## Mandatory checkpoints

After exact SHA-pinned planner bootstrap, run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

Consume the actual live contract, including Daily pool size, planning modes, target rules, publication template, content/candidate identity patterns, controlled values and media-readiness thresholds.

If readiness is `REPLENISH`, complete the canonical replenishment path and refresh current `main` before candidate finalization.

After authoring/final-ranking the complete Daily pool, run the shared precommit engine. In Git mode use `--verify-git-head`; in connector fallback omit that flag:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile daily \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha <rules_source_sha> \
  --verify-git-head
```

The gate requires **all 36 candidates PASS** before immutable pool commit. `planning.daily_precommit` remains only a backward-compatible wrapper.

**FAIL CLOSED if the exact precommit module cannot execute.** Manual checks, downstream pool admission, ranked promotion or GitHub Actions are not substitutes for planner-time pre-commit.

Before immutable commit, apply the shared planner-relevant drift policy from `docs/private/PLANNER_PROMPT.md`; do not restart the whole planner merely because operational-only commits advanced `main`. The final immutable pool bytes must exactly match the successful `draft_sha256`.

ChatGPT/Work remains the creative/editorial owner and freezes Daily rank order. Private workflows validate/promote mechanically; public runtime executes statelessly.
