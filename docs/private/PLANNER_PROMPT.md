# Wacky Dramas — Shared Planner Execution Contract

Daily and Ad-hoc are profiles of **one planner**. This file is the canonical shared execution/materialization contract. `youtube-shorts-bot/planning/DAILY_PLANNER_PROMPT.md` and `youtube-shorts-bot/planning/ADHOC_PLANNER_PROMPT.md` select a profile and add only mode-specific instructions.

If older mode-specific rule text duplicates execution-environment/bootstrap or planner-source-read instructions, this shared contract wins. Creative/business rules in the mode-specific rules remain mandatory unless current executable repository code/configuration supersedes them.

## Repository-first identity

1. Inspect current `main` of `skyfremen/youtube-workflow` through the GitHub API/connector.
2. Retain the exact immutable 40-character commit SHA as `rules_source_sha`.
3. Read `youtube-shorts-bot/planning/PLANNER_MATERIALIZATION.json` from that exact SHA.
4. Select the requested profile: `daily` or `adhoc`.
5. Fetch only `shared_required_python_files`, `shared_required_data_files`, and the selected profile additions declared by the manifest for executable planner bootstrap.
6. Fetch every source path from the exact `rules_source_sha`.

Do **not** separately fetch `planning/ranked_promotion.py`, `publishing/upload.py`, compatibility precommit wrappers, package `__init__` files, or opposite-profile implementation files merely to execute planner-time Python. Those are downstream/compatibility surfaces and are intentionally excluded from the canonical materialization set. Inspect them only when the user explicitly requests downstream verification or when resolving a concrete contract discrepancy.

A Git checkout, Git executable, `.git` directory, authenticated clone, repository archive, whole-repository download, synthetic HEAD, automatic connector filesystem mount, special connector bridge, or GitHub Actions planner job is **not** a planner prerequisite.

## Exact connector materialization

Prefer a complete UTF-8 fetch. When a connector response is clipped/truncated, refetch exact non-overlapping line ranges from the same path and same SHA until complete. Preserve newline boundaries.

For chunked files, and preferably every file, verify bytes using Git's blob hash algorithm without invoking Git:

`sha1(b"blob " + ascii_decimal_byte_length + b"\0" + content_bytes)`

The result must equal the connector-returned Git blob SHA.

Write verified bytes into an ordinary temporary directory preserving repository-relative paths. Set `PYTHONPATH` to the materialized `youtube-shorts-bot` directory.

## Optional immutable-SHA cache

A previously blob-verified materialization may be reused only for the identical `rules_source_sha` and manifest entry. The cache is an optimization, never a correctness dependency.

- Never cache by `main`, date, or filename alone.
- Shared files may be reused across Daily and Ad-hoc at the same SHA.
- When `main` resolves to a different SHA, treat it as a cold snapshot.
- Never mix source bytes from different SHAs.

## Mandatory local Python checkpoints

Run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

Consume actual output. `planner_contract` exposes both profiles and a shared-contract fingerprint. Daily and Ad-hoc must report the same shared fingerprint.

If readiness is `REPLENISH`, complete the current canonical background-replenishment procedure before freezing final backgrounds or committing a ranked pool. Re-read `main` afterward because the accepted registry update changes `rules_source_sha`.

After complete candidate authorship, execute exactly one shared precommit engine:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile <daily|adhoc> \
  --pool <temporary-pool.json> \
  --rules-source-sha <rules_source_sha>
```

Compatibility wrappers `planning.daily_precommit` and `planning.adhoc_precommit` may remain for existing callers, but they are not required for planner materialization and must contain no independent validation logic.

**FAIL CLOSED if the exact pre-commit module cannot be executed** after exact connector-returned source has been materialized. Planner-time Python validation is mandatory. Manual schema checks, hand arithmetic, downstream admission, promotion, or GitHub Actions are not substitutes.

Do not use `--verify-git-head` for normal ChatGPT/Work planning. It remains optional developer/CI hardening inside a real checkout only.

## Shared ownership and drift rule

Shared behavior exists exactly once. If a feature should apply to both profiles, classify it `SHARED` and implement it in shared code/configuration. Profiles may contain only genuine differences such as pool/count policy, identity/uniqueness policy, scheduling/publication mode, and promotion cardinality.

Do not add schema, semantic, narration/voice, punchline, background, media-readiness, request-validator, or common publication validation overrides to a profile.

ChatGPT/Work retains creative ownership: premise generation/rejection, duplicate reasoning, analytics/editorial judgment, full story/title/metadata authoring, voice/punchline semantics, exact logical backgrounds, treatment choices, fallback reasoning, and final rank.

Python validates contracts; it does not creatively rerank or repair.

## State and final SHA check

Materialize only the profile-specific existence/uniqueness placeholders declared by the manifest. Use targeted exact identity checks when sufficient; do not broadly enumerate same-day immutable state merely to prove an exact identity is unused.

Before committing immutable planner output, re-read current `main`. If it differs from `rules_source_sha`, refresh the manifest/source/state from the new SHA and rerun contract discovery, media readiness and complete precommit validation. The final pool bytes must match the successful precommit `draft_sha256`.

GitHub Actions remains downstream CI/production only. It is **not** the planner execution engine.
