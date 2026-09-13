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
authorized GitHub connector/API
        |
resolve exact current-main SHA
        |
freeze rules_source_sha
        |
materialize exact manifest + required files
        |
verify per-file source/blob evidence
        |
planning.materialization_verify PASS
        |
local ChatGPT/Work Python
        |
planner_contract.py + media_readiness
        |
creative planning
        |
planner_precommit.py --profile daily|adhoc
        |
connector/API current-main SHA drift check
        |
immutable ranked pool
        |
private Daily/Ad-hoc production workflow
        |
production-runtime
```

For ChatGPT/Work, the authorized GitHub connector/API is the repository source-acquisition mechanism, not the planner. Shell Git access to `github.com` is neither attempted nor required. GitHub Actions is downstream deterministic CI/production/control-plane infrastructure only and never owns creative planning.

## Shared implementation

- `planning/planner_profiles.py` — declarative mode differences only.
- `planning/planner_core.py` — shared ranked-pool/candidate/date/publication validation helpers.
- `planning/planner_precommit.py` — one fail-closed planner-time validator for both profiles.
- `planning/planner_contract.py` — machine-readable contract and shared-contract fingerprint.
- `planning/planner_drift.py` — deterministic path classification for connector/API drift, with real-Git comparison retained only for genuine checkout contexts.
- `planning/materialization_verify.py` — exact-SHA connector materialization/evidence verifier.
- `validation/validate_content.py` — shared request/schema/background contract.
- `validation/publication.py` — shared publication and YouTube metadata constraints used by planner and uploader.
- `planning/daily_precommit.py` and `planning/adhoc_precommit.py` — compatibility wrappers only.
- `planning/ranked_promotion.py` — downstream immutable-state promotion; it consumes shared planner contracts rather than owning creative planning.

## Canonical ChatGPT/Work connector bootstrap

ChatGPT/Work begins directly with the authorized GitHub connector/API. It does not first try `git fetch`, `git clone`, `git pull`, `git ls-remote`, `git rev-parse origin/main`, worktree creation, Git authentication repair, DNS/proxy/network repair, or any `.git`-dependent health check.

The canonical acquisition sequence is:

1. Query the connector/API for the exact current `main` commit SHA and freeze it as `rules_source_sha`.
2. Fetch `youtube-shorts-bot/planning/PLANNER_MATERIALIZATION.json` at that exact SHA.
3. Materialize every manifest-required path from that same SHA into an ordinary temporary directory.
4. Record the connector-returned source SHA and Git blob SHA/equivalent canonical blob identity for every path, including the manifest itself.
5. Run `planning.materialization_verify --profile <daily|adhoc> --root ... --rules-source-sha ... --evidence ...`.
6. Continue only after `status=PASS`, then run `planning.planner_contract` and `media.media_readiness audit --allow-not-ready` from that same materialized snapshot.

No synthetic `.git`, HEAD, clone, worktree or shell-network probe is created to satisfy planner validation. `MATERIALIZATION_BLOCKED` is reserved for a concrete named connector/API fetch/reconstruction/evidence/write failure or a verifier `FAIL`; local Git/DNS/checkout absence is not a ChatGPT/Work blocker.

Persistence/reuse is an optimization only. Cached source is reusable only when its connector evidence belongs to the identical immutable SHA.

## Real Git checkout mode outside ChatGPT/Work

Developer tooling, CI and GitHub Actions may legitimately use a real Git checkout when that execution context is already based on Git metadata. That mode remains supported for tasks such as immutable-history checks, cross-repository contract parity, normal source development and other deterministic CI operations.

A real Git checkout may use `--verify-git-head` and the Git-based `planning.planner_drift --base-sha/--head-sha` helpers. These are deliberately separate from the canonical ChatGPT/Work path and must not be presented as a prerequisite, preferred path, initial attempt or fallback prerequisite for ChatGPT/Work.

## Drift protection

Whole-repository branch movement is not automatically equivalent to planner-contract drift.

Immediately before immutable output is committed, ChatGPT/Work re-queries current `main` through the authorized GitHub connector/API and compares the returned SHA to `rules_source_sha`. No shell Git network command is used.

If the SHA changed, connector/API compare evidence supplies changed paths when available. `planning.planner_drift.classify_connector_transition` or its CLI connector mode applies the existing path categories without Git:

| Class | Examples | Required action |
| --- | --- | --- |
| rules | planner, validation, media policy, shared planner docs | refresh exact connector snapshot; materialization verify + contract + readiness + full precommit |
| media | background registry/sourcing state | refresh media; readiness + background revalidation + full precommit |
| history | analytics, requests, results, planning/pools | refresh affected creative history; rerun semantic/editorial checks |
| operational | recovery, completion, diagnostics/progress evidence | no creative restart solely for this drift |
| unknown | any unclassified path | conservative full refresh |

If the branch moved but a trustworthy changed-path set is unavailable, connector mode conservatively performs a full refresh. Real-Git developer/CI mode may additionally compute the existing path-scoped fingerprints from local Git objects.

The strongest drift prevention remains structural: both profiles invoke the same `planner_precommit.validate_draft` and the same candidate/request/publication validators.

## Validation and preflight

The canonical precommit already performs structural, schema, semantic, publication, background and uniqueness validation and reports `validation_elapsed_ms`. A second independent preflight rules engine would duplicate logic and risk drift, so no parallel validator is introduced. ChatGPT/Work may run the canonical precommit repeatedly while drafting; the final successful run remains mandatory.

For the canonical connector-materialized ChatGPT/Work path, precommit does **not** use `--verify-git-head`:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile <daily|adhoc> \
  --pool <pool-file> \
  --rules-source-sha <rules_source_sha>
```

The source-integrity proof is the exact `rules_source_sha`, exact connector-materialized bytes, verified per-file connector evidence and `planning.materialization_verify PASS`. A local HEAD is never fabricated. `--verify-git-head` is retained only for genuine real-Git developer/CI checkout mode.

## Performance diagnostics

Canonical ChatGPT/Work planner runs may report connector resolution/materialization, contract, readiness, state-load, precommit and commit timings. These timings are report-only and never affect ranking. Git-specific reuse/fetch timings are applicable only to the separate developer/CI real-Git mode.

## Production boundary

This transport change does not alter request schemas, ranking/business logic, private promotion semantics, background readiness/replenishment behavior, visual-review ownership or the public runtime contract. Private Daily and Ad-hoc workflows remain separate production entry points because their trigger/promotion semantics differ. Public `production-runtime` remains stateless execution.
