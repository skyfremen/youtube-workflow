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
GitHub main
    |
rules_source_sha
    |
PLANNER_MATERIALIZATION.json
    |
shared planner source + selected profile
    |
local ChatGPT/Work Python
    |
planner_contract.py
    |
planner_precommit.py --profile daily|adhoc
    |
immutable ranked pool
    |
private Daily/Ad-hoc production workflow
    |
production-runtime
```

GitHub Actions is downstream CI/production only. It is not the planner execution engine.

## Shared implementation

- `planning/planner_profiles.py` — declarative mode differences only.
- `planning/planner_core.py` — shared ranked-pool/candidate/date/publication validation helpers.
- `planning/planner_precommit.py` — one fail-closed planner-time validator for both profiles.
- `planning/planner_contract.py` — machine-readable contract and shared-contract fingerprint.
- `validation/validate_content.py` — shared request/schema/background contract.
- `validation/publication.py` — shared publication and YouTube metadata constraints used by planner and uploader.
- `planning/daily_precommit.py` and `planning/adhoc_precommit.py` — compatibility wrappers only.
- `planning/ranked_promotion.py` — downstream Git/immutable-state promotion; consumes shared planner contracts rather than owning planner validation.

## Materialization performance

Before this refactor the canonical planner materialization contract required 19 Python files for both profiles plus `backgrounds.json`.

The shared planner bootstrap now requires 14 Python files plus `backgrounds.json`, a reduction of 5 Python fetches (26.3%). It deliberately excludes downstream promotion/publishing modules, package `__init__` files and compatibility precommit wrappers.

The remaining heavy cost is shared request/background validation. Future performance work should reduce real transitive dependencies rather than duplicate validator logic.

An optional cache may reuse already blob-verified source only for the identical immutable `rules_source_sha`. Shared cache entries may be reused across profiles at the same SHA. Cache availability is never required for correctness.

## Drift protection

`planner_contract.py` computes one shared contract fingerprint and attaches the same fingerprint to both profiles. `PlannerProfile` intentionally contains no schema/semantic/background/narration/punchline/media-readiness validator fields. Tests fail if shared contract ownership leaks into profile structure or if materialization reintroduces downstream modules.

The strongest drift prevention remains structural: both profiles invoke the same `planner_precommit.validate_draft` and the same candidate/request/publication validators.

## Git-less execution

Canonical ChatGPT/Work execution requires only exact SHA-pinned source/config/data bytes returned by the GitHub connector/API. It must work in an ordinary temporary directory without `.git`, a Git executable, checkout, clone, repository archive, synthetic HEAD, automatic connector mount or GitHub Actions planner execution.

The immutable GitHub source commit is passed explicitly as `rules_source_sha`. Before committing a ranked pool, ChatGPT/Work re-reads `main`; if the SHA changed, it refreshes materialization and reruns contract discovery, readiness and precommit.

## Production boundary

The refactor does not change request schema v5 or the public runtime contract. Private Daily and Ad-hoc workflows remain separate production entry points because their trigger/promotion semantics differ. Public `production-runtime` remains stateless execution.
