# Wacky Dramas — Shared Planner Execution Contract

Daily and Ad-hoc are profiles of **one planner**. This file is the canonical shared bootstrap, execution, materialization and drift contract. `youtube-shorts-bot/planning/DAILY_PLANNER_PROMPT.md` and `youtube-shorts-bot/planning/ADHOC_PLANNER_PROMPT.md` select a profile and add only mode-specific instructions.

If older mode-specific rule text duplicates execution-environment/bootstrap or planner-source-read instructions, this shared contract wins. Creative/business rules in the mode-specific rules remain mandatory unless current executable repository code/configuration supersedes them.

## Repository-first identity

The planner identity remains one explicit immutable 40-character `rules_source_sha`. Git is now the **preferred source-acquisition path**, not the identity itself.

1. Prefer an already-authorized local Git repository for `skyfremen/youtube-workflow`; otherwise obtain one when Git access is available.
2. Run `git fetch origin main --prune`.
3. Resolve current main with `git rev-parse origin/main` and retain that exact SHA as `rules_source_sha`.
4. Create a clean detached worktree/check-out at exactly that SHA, for example `git worktree add --detach <temporary-planner-path> <rules_source_sha>`.
5. Verify `git rev-parse HEAD` equals `rules_source_sha` and `git status --porcelain` is empty in the planner snapshot.
6. Read `youtube-shorts-bot/planning/PLANNER_MATERIALIZATION.json` from that exact snapshot and select `daily` or `adhoc`.

Reuse the Git object database/clone when the environment permits persistence. **Do not require a fresh clone per invocation.** Persistence is an optimization, never a correctness dependency.

Do not execute planner Python from the user's mutable working branch or from a dirty planner worktree. Uncommitted changes in another worktree must not contaminate the detached planner snapshot.

## Connector/API fallback

Git authentication or Git availability is **not** a hard architectural dependency. If current `main` cannot be fetched and verified through Git, use the exact-SHA connector/API materialization described by `planning/PLANNER_MATERIALIZATION.json`.

The connector fallback must:

- resolve current `main` through the GitHub API/connector;
- pin one exact `rules_source_sha`;
- fetch only the declared shared source/data plus selected-profile additions;
- fetch every path from the same SHA;
- reconstruct clipped files only from non-overlapping ranges at the same SHA;
- verify chunked bytes, and preferably all bytes, with Git blob-SHA semantics;
- never mix source/state from different commits.

The connector fallback runs in an ordinary temporary directory and must continue to work without `.git` or a Git executable.

If neither an exact Git snapshot nor exact-SHA connector materialization can be obtained, **fail closed**. Never fall back to stale local source.

## No synthetic repository identity

Do not manufacture `.git`, a fake branch/ref, or a synthetic HEAD merely to make `git rev-parse HEAD` return `rules_source_sha`. Git mode uses a real fetched commit. Connector mode passes `rules_source_sha` explicitly and does not pretend to be a checkout.

GitHub Actions planner execution remains prohibited. GitHub Actions is downstream deterministic CI/production only.

## Local repository-state inspection

In Git mode, use the exact detached snapshot for repository-owned planner state: planner code/rules, schemas, background registry, analytics, immutable requests/results/pools and other relevant history. Do not individually refetch those same bytes through the connector when they are already present at the verified SHA.

In connector fallback, materialize only what the manifest requires plus targeted state needed by the selected profile. Do not broaden fallback into an unnecessary whole-repository connector download.

## Mandatory local Python checkpoints

From the exact planner snapshot/materialization run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

Consume actual output. `planner_contract` exposes both profiles and a shared-contract fingerprint. Daily and Ad-hoc must report the same shared fingerprint.

If readiness is `REPLENISH`, complete the current canonical background-replenishment procedure before freezing final backgrounds or committing a ranked pool. Refresh current `main` afterward because the accepted registry update is planner-relevant media drift.

After complete candidate authorship, run exactly one shared precommit engine. In preferred Git mode also attest the detached checkout:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile <daily|adhoc> \
  --pool <temporary-pool.json> \
  --rules-source-sha <rules_source_sha> \
  --verify-git-head
```

In connector fallback, run the same command **without** `--verify-git-head`; the explicit exact SHA and verified materialized bytes are the authority.

Compatibility wrappers `planning.daily_precommit` and `planning.adhoc_precommit` may remain for existing callers, but they are not required for planner bootstrap and must contain no independent validation logic.

**FAIL CLOSED if the exact precommit module cannot execute.** Manual schema checks, hand arithmetic, downstream admission/promotion, or GitHub Actions are not substitutes.

## Creative ownership

ChatGPT/Work retains creative ownership: premise generation/rejection, duplicate reasoning, analytics/editorial judgment, full story/title/metadata authoring, voice/punchline semantics, exact logical backgrounds, treatment choices, fallback reasoning and final rank.

Python validates contracts. It does not creatively rerank or repair.

## Planner-relevant drift

Before committing immutable planner output, refresh current `main`.

In Git mode:

```bash
git fetch origin main --prune
LATEST_MAIN_SHA="$(git rev-parse origin/main)"
```

If `LATEST_MAIN_SHA == rules_source_sha`, continue.

If it changed, classify the changed paths with:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_drift \
  --base-sha <rules_source_sha> \
  --head-sha <latest_main_sha>
```

Apply the returned policy:

- **rules** — planner/validation/media-policy/shared-contract changes: refresh the source snapshot and rerun contract, readiness and complete precommit.
- **media** — background registry/sourcing/readiness state: refresh media state, rerun readiness, revalidate exact backgrounds and rerun complete precommit.
- **history** — requests/results/planning pools/analytics: refresh affected creative-history inputs and rerun duplicate/analytics/recent-background reasoning; rerun complete precommit whenever the authored pool bytes change.
- **operational** — recovery, runtime-progress, completion or diagnostics evidence only: do not restart creative planning solely because HEAD moved.
- **unknown** — fail safe as a full refresh.

`planning.planner_drift` also reports deterministic `planner_contract_digest`, `media_state_digest` and `creative_history_digest` fingerprints in Git mode.

In connector fallback, if changed paths can be obtained safely from the API/connector, apply the same classifier with repeatable `--changed-path`. If main changed but the changed path set cannot be established safely, conservatively perform a full refresh.

The final immutable pool bytes must exactly match the successful precommit `draft_sha256`.

## Performance diagnostics

Measure planner stages with a monotonic clock where practical and report:

`materialization_mode`, `git_reused`, `bootstrap_ms`, `git_fetch_ms`, `materialization_ms`, `contract_ms`, `media_readiness_ms`, `state_load_ms`, `precommit_ms`, and `commit_ms`.

These diagnostics are observability only. They must not influence creative ranking or validation. Do not add external telemetry infrastructure just to collect them.

## Shared architecture boundary

Shared behavior exists exactly once. If a feature should apply to both profiles, classify it `SHARED` and implement it in shared code/configuration. Profiles may contain only genuine differences such as pool/count policy, identity/uniqueness policy, scheduling/publication mode and promotion cardinality.

Do not add schema, semantic, narration/voice, punchline, background, media-readiness, request-validator or common-publication overrides to a profile.

Git is a fast source-acquisition mechanism, not the planner. ChatGPT/Work owns creative planning; local canonical Python proves the frozen plan is valid; GitHub Actions owns deterministic downstream automation.
