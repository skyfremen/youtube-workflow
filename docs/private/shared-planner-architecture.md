# Shared Planner Architecture

Daily and Ad-hoc are two profiles of one Wacky Dramas planner.

## Ownership

Shared behavior belongs in shared code/configuration. A new planner feature must first be classified as:

- `SHARED` — default when the behavior should apply to both Daily and Ad-hoc.
- `DAILY_ONLY` — only when Daily semantics genuinely differ.
- `ADHOC_ONLY` — only when Ad-hoc semantics genuinely differ.

Schema, semantic validation, story/title/punchline contracts, narration/voice rules, background/media readiness, background treatment validation, common publication validation and candidate validation are `SHARED`.

Pool count, identity/uniqueness policy, scheduling/publication mode and promotion cardinality may be profile-specific.

## Architecture

```text
current private main
        |
  Git fetch preferred
  connector fallback
        |
  rules_source_sha
        |
  clean exact snapshot
        |
  local ChatGPT/Work Python
        |
  planner_contract.py
        |
  creative planning
        |
  planner_precommit.py --profile daily|adhoc
        |
  planner_drift.py before commit if main moved
        |
  immutable ranked pool
        |
  private Daily/Ad-hoc production workflow
        |
  production-runtime
```

Git is a source-acquisition/state-inspection mechanism, not the planner. GitHub Actions is downstream deterministic CI/production only and never owns creative planning.

## Shared implementation

- `planning/planner_profiles.py` — declarative mode differences only.
- `planning/planner_core.py` — shared ranked-pool/candidate/date/publication validation helpers.
- `planning/planner_precommit.py` — one fail-closed planner-time validator for both profiles.
- `planning/planner_contract.py` — machine-readable contract and shared-contract fingerprint.
- `planning/planner_drift.py` — deterministic path classification/fingerprints when current `main` advances during planning.
- `validation/validate_content.py` — shared request/schema/background contract.
- `validation/publication.py` — shared publication and YouTube metadata constraints used by planner and uploader.
- `planning/daily_precommit.py` and `planning/adhoc_precommit.py` — compatibility wrappers only.
- `planning/ranked_promotion.py` — downstream immutable-state promotion; it consumes shared planner contracts rather than owning creative planning.

## Git-first bootstrap

When an authorized Git repository is available, reuse it rather than re-cloning:

```bash
git fetch origin main --prune
RULES_SOURCE_SHA="$(git rev-parse origin/main)"
git worktree add --detach <planner-worktree> "$RULES_SOURCE_SHA"
test "$(git -C <planner-worktree> rev-parse HEAD)" = "$RULES_SOURCE_SHA"
test -z "$(git -C <planner-worktree> status --porcelain)"
```

A fresh clone is allowed when no reusable repository exists. The environment's normal Git authorization is used; credentials are never encoded in planner content.

Planner source and repository-owned state are then ordinary local reads from one exact commit. This removes the repeated connector reconstruction cost on the preferred path.

Persistence/reuse is an optimization only. Every run still fetches current `main` before resolving the planning SHA.

## Connector fallback

`planning/PLANNER_MATERIALIZATION.json` retains the 14-file shared Python set plus `backgrounds.json` for environments where Git cannot access the private repository.

Connector fallback remains exact-SHA, blob-verifiable and fail closed. It deliberately excludes downstream promotion/publishing modules, package `__init__` files and compatibility wrappers from executable planner bootstrap.

Daily and Ad-hoc therefore share identical planner semantics in both acquisition modes:

```text
Git exact snapshot ───────────┐
                             ├─> same planner_contract/readiness/precommit
connector exact materialization┘
```

A synthetic `.git`/HEAD is not a valid bridge between the two modes. Git mode uses a real fetched commit; connector mode uses explicit `rules_source_sha`.

## Drift protection

Whole-repository HEAD movement is no longer treated as automatically equivalent to planner-contract drift.

`planning.planner_drift` classifies changed paths:

| Class | Examples | Required action |
| --- | --- | --- |
| rules | planner, validation, media policy, shared planner docs | refresh source; contract + readiness + full precommit |
| media | background registry/sourcing state | refresh media; readiness + background revalidation + full precommit |
| history | analytics, requests, results, planning/pools | refresh affected creative history; rerun semantic/editorial checks |
| operational | recovery, completion, diagnostics/progress evidence | no creative restart solely for this drift |
| unknown | any unclassified path | conservative full refresh |

Git mode also computes three deterministic path-scoped digests: `planner_contract_digest`, `media_state_digest` and `creative_history_digest`.

The strongest drift prevention remains structural: both profiles invoke the same `planner_precommit.validate_draft` and the same candidate/request/publication validators.

## Validation and preflight

The canonical precommit already performs structural, schema, semantic, publication, background and uniqueness validation and reports `validation_elapsed_ms`. A second independent preflight rules engine would duplicate logic and risk drift, so no parallel validator is introduced. ChatGPT/Work may run the canonical precommit repeatedly while drafting; the final successful run remains mandatory.

In Git mode the final precommit uses `--verify-git-head` so `HEAD == rules_source_sha`. Connector fallback omits that flag and relies on verified exact-SHA source bytes plus explicit `rules_source_sha`.

## Performance diagnostics

Planner runs should report bootstrap/fetch/materialization, contract, readiness, state-load, precommit and commit timings where practical. These timings are report-only and never affect ranking.

The expected performance advantage is largest when a prior local Git repository can be reused. A fresh Git acquisition may or may not beat connector fallback in every environment, so benchmark claims must be based on measurements rather than assumed.

## Production boundary

This change does not alter request schema v5, ranking/business logic, private promotion semantics or the public runtime contract. Private Daily and Ad-hoc workflows remain separate production entry points because their trigger/promotion semantics differ. Public `production-runtime` remains stateless execution.
