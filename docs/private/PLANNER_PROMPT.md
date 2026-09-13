# Wacky Dramas — Shared Planner Execution Contract

Daily and Ad-hoc are profiles of one planner. This file is the canonical shared execution, background-continuation, evidence, validation and drift contract. Profile entry points add only genuine mode-specific rules.

Repository code/configuration at the exact current `main` commit is authoritative. If older wording refers to ChatGPT/Work reconstructing a local repository tree, running `planning.materialization_verify`, or copying the full background registry locally, the current `planning/PLANNER_MATERIALIZATION.json` and this contract supersede that wording.

## Repository-first identity

Every planner invocation freezes one lowercase 40-character `rules_source_sha`.

For ChatGPT/Work, the authorized GitHub connector/API is the canonical repository access path. Shell Git access to `github.com` is neither attempted nor required. Do not run `git fetch`, `git clone`, `git pull`, `git ls-remote`, Git worktrees, DNS/proxy repair, or any synthetic Git-HEAD workaround.

The canonical bootstrap is:

1. Resolve the exact current `main` SHA of `skyfremen/youtube-workflow` through the authorized GitHub connector/API.
2. Freeze it as `rules_source_sha`.
3. Fetch `youtube-shorts-bot/planning/PLANNER_MATERIALIZATION.json` from that exact SHA.
4. Fetch `youtube-shorts-bot/planning/connector_checkpoint.py` from that exact SHA and record its connector-returned Git blob SHA/equivalent canonical blob identity.
5. Read the selected profile prompt/rules, shared story/background rules and targeted repository state directly through exact-SHA connector reads. These reads remain connector evidence; they do **not** have to be reconstructed as a local repository tree.
6. Write only the standalone `connector_checkpoint.py`, the authored pool JSON and a small connector-evidence JSON to a temporary local directory.
7. Run `python connector_checkpoint.py contract` to inspect the live standalone checkpoint contract.

`CHECKPOINT_STAGING_BLOCKED` is legal only after the exact-SHA checkpoint file itself cannot be fetched, its blob identity is unavailable/inconsistent, that one file cannot be written, or standard-library Python cannot execute it. A Git/DNS/checkout failure, missing `.git`, an unmaterialized repository tree, or an uncopied full `backgrounds.json` is not a valid blocker.

## Connector evidence instead of repository reconstruction

The standalone checkpoint consumes a small connector-evidence JSON. It must be assembled from current exact-SHA repository reads and contain:

- `schema_version=1`
- `repository=skyfremen/youtube-workflow`
- exact `rules_source_sha`
- connector-returned `checkpoint_blob_sha`
- `drift.status=PASS` and `drift.current_main_sha=<rules_source_sha>` immediately before final validation/commit
- `media_readiness.status=PASS`
- `uniqueness.status=PASS`
- `selected_backgrounds` containing only IDs referenced by the authored pool, each with connector-backed `eligible=true`, trusted `duration_seconds`, and source blob/path evidence

Do not invent evidence. Do not mark readiness, uniqueness, background eligibility or drift `PASS` from memory.

The full background registry is repository state, not a required local checkpoint input. Read only the repository evidence needed to establish readiness and the selected assets. Downstream private validation remains defense-in-depth, but it is not a substitute for planner-time evidence and checkpoint validation.

## Shared automatic background replenishment and continuation

`REPLENISH` is recoverable planner state, not a terminal planning failure. Daily and Ad-hoc use the same continuation procedure before final backgrounds are frozen.

1. Consume the current readiness total/category/duration/sequence deficits from repository-owned state/evidence.
2. Inspect immutable discovery requests/results/readiness manifests, matching review-evidence indexes and Background Management runs. Resume a compatible unfinished attempt instead of creating duplicates.
3. If no compatible attempt exists, create exactly one immutable discovery request using the current repository schema/convention.
4. Private Background Management may perform deterministic provider discovery, exact-source transport/download, FFmpeg contact-sheet generation, artifact upload and deterministic readiness persistence. It must never perform ChatGPT-owned creative approval, semantic classification or story planning.
5. Poll/refresh the required run for the bounded continuation window already defined by the background-media strategy. Continue in the same planner invocation when the immutable result/evidence becomes available. Report `DEFERRED_REPLENISHMENT` only when a required bounded wait genuinely expires.
6. Review actual exact-source visual evidence. Prefer the newest usable indexed artifact; verify its run/artifact identity and manifest digest. GitHub-generated frames are transport evidence only, not approval.
7. Reject candidates with missing/unsuitable evidence individually and continue reserves. Never weaken `verified_preview`.
8. Commit exactly one immutable readiness manifest from visually approved candidates, then allow Background Management to perform deterministic provider re-enrichment/persistence.
9. Re-resolve current `main`, apply drift policy, refresh media evidence and repeat until readiness is `PASS`.

GitHub Actions may continue to perform deterministic background transport/state work and downstream production. **GitHub Actions must not perform creative planning or generate/rank the Daily/Ad-hoc candidate pool.**

## Creative ownership

ChatGPT/Work owns premise generation/rejection, duplicate reasoning, analytics/editorial judgment, complete story/title/metadata writing, voice and punchline semantics, exact logical background choices/ranges, visual review, fallback reasoning and final rank.

Repository code/configuration and the standalone checkpoint own deterministic contract validation. Neither may creatively repair or rerank authored content.

## Planner-time deterministic checkpoint

After the complete ranked pool is authored, write a small connector-evidence JSON and run:

```bash
python connector_checkpoint.py validate \
  --profile <daily|adhoc> \
  --pool <pool.json> \
  --rules-source-sha <rules_source_sha> \
  --evidence <connector-evidence.json>
```

The checkpoint is standard-library-only and intentionally has no repository imports. It validates the ranked-pool envelope, provenance, current request schema, profile publication contract, controlled metadata, voice mapping, title/scoring structure, punchline semantics, schema-v7 sequence ranges, selected-background evidence, readiness, uniqueness and pre-commit drift evidence.

All expected candidates must return `PASS`; `commit_allowed` must be true. The immutable bytes committed to GitHub must exactly match the checkpoint's `draft_sha256`.

Do not replace this planner-time checkpoint with manual inspection or a GitHub Actions run.

## Repository state / uniqueness

Inspect identity state through the connector before allocating IDs.

- Daily retains one canonical plan per plan date plus immutable pool-attempt IDs.
- Ad-hoc `scheduled_daily` retains its once-per-Singapore-date namespace.
- Ad-hoc `manual_on_demand` may coexist multiple times on the same Singapore date. A same-date `scheduled_daily` request is not itself a collision for a distinct manual invocation.

The connector-evidence JSON may set `uniqueness.status=PASS` only after the required current namespace/state reads have completed.

## Drift

Immediately before immutable commit, query current `main` again through the authorized connector/API.

If it still equals `rules_source_sha`, set connector evidence `drift.status=PASS` and run the final checkpoint. If it changed, obtain changed-path evidence when possible and apply the normal classifications:

- `rules`: refresh exact-SHA rules/checkpoint and rerun the complete checkpoint.
- `media`: refresh readiness/selected-background evidence and rerun the complete checkpoint.
- `history`: refresh duplicate/analytics/recent-background reasoning and rerun the checkpoint whenever authored bytes change.
- `operational`: do not restart creative planning solely because operational evidence moved.
- unknown/untrusted changed-path set: full refresh.

Never silently mix rules or state from different commits.

## Commit and downstream production boundary

Only after checkpoint `PASS` may ChatGPT/Work commit the immutable ranked pool through the authorized GitHub connector/API.

After that, existing private workflows remain deterministic control-plane infrastructure: validate the committed pool, preserve frozen rank order, promote valid candidate(s), create canonical immutable request(s) and dispatch the public stateless runtime. The public runtime performs TTS/alignment/render/upload/verification. ChatGPT/Work does not directly render, TTS or upload unless repository architecture explicitly changes.

## Developer/CI mode

Developers/CI may still use the repository-native planner modules and full test suite from a genuine checkout. That mode is separate from canonical ChatGPT/Work execution. It does not justify shell Git attempts in ChatGPT/Work and does not make GitHub Actions a planner.
