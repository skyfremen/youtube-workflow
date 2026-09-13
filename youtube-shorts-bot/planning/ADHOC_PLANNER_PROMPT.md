# Wacky Dramas — Ad-hoc Planner

This is the canonical **Ad-hoc profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — canonical shared Git-first/bootstrap/materialization/drift contract.
2. `planning/ADHOC_PLANNER_RULES.md` — Ad-hoc ranked-pool, identity, immediate-public, promotion and recovery rules.
3. `planning/STORY_RULES.md` and current shared background/analytics rules referenced by the Ad-hoc rules.

Repository code/configuration at current `main` remains the source of truth. If older Ad-hoc rule text repeats bootstrap/materialization instructions, `docs/private/PLANNER_PROMPT.md` supersedes only those duplicated execution-environment instructions; Ad-hoc business/creative rules remain mandatory.

Prefer the shared contract's **Git-first exact detached snapshot** and reuse an existing authorized clone when possible. If Git cannot obtain and verify current `main`, use the exact-SHA connector/API fallback in `planning/PLANNER_MATERIALIZATION.json`. GitHub Actions planner execution is prohibited.

## Profile

Use `profile=adhoc` from the live `planning.planner_contract` output.

Daily and Ad-hoc must use the same shared request/schema/semantic/background/media/narration/publication-validation implementation and the same shared-contract fingerprint. Ad-hoc-specific behavior may differ only where the `adhoc` profile declares it.

## Mandatory checkpoints

After exact SHA-pinned planner bootstrap, run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

Consume the actual live contract, including Ad-hoc pool size, planning modes, identity policy, immediate-public template, content/candidate identity patterns, controlled values and media-readiness thresholds.

If readiness is `REPLENISH`, complete the canonical replenishment path and refresh current `main` before candidate finalization.

After authoring and freezing the complete five-candidate ranked pool, run the shared precommit engine. In Git mode use `--verify-git-head`; in connector fallback omit that flag:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile adhoc \
  --pool /tmp/wacky-adhoc-pool.json \
  --rules-source-sha <rules_source_sha> \
  --verify-git-head
```

The gate requires **all five candidates PASS** before immutable pool commit. `planning.adhoc_precommit` remains only a backward-compatible wrapper.

**FAIL CLOSED if the exact precommit module cannot execute.** Manual checks, downstream pool admission, ranked promotion or GitHub Actions are not substitutes for planner-time pre-commit.

For `manual_on_demand`, multiple same-date manual runs remain allowed under distinct stable immutable invocation identities. Existing `scheduled_daily` state is not a reuse/stop condition for a distinct manual invocation. Scheduled-daily uniqueness remains fail closed.

Before immutable commit, apply the shared planner-relevant drift policy from `docs/private/PLANNER_PROMPT.md`; do not restart the whole planner merely because operational-only commits advanced `main`. The final immutable pool bytes must exactly match the successful `draft_sha256`.

ChatGPT/Work remains the creative/editorial owner and freezes rank #1 through #5. Private workflow promotion preserves rank order and selects the first valid candidate mechanically; public runtime executes statelessly.
