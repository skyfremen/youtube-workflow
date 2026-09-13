# Wacky Dramas — Shared Planner Execution Contract

Daily and Ad-hoc are profiles of **one planner**. This file is the canonical shared bootstrap, execution, materialization, background-replenishment continuation and drift contract. `youtube-shorts-bot/planning/DAILY_PLANNER_PROMPT.md` and `youtube-shorts-bot/planning/ADHOC_PLANNER_PROMPT.md` select a profile and add only mode-specific instructions.

If older mode-specific rule text duplicates execution-environment/bootstrap, planner-source-read or background-replenishment instructions, this shared contract wins. Creative/business rules in the mode-specific rules remain mandatory unless current executable repository code/configuration supersedes them.

## Repository-first identity

The planner identity remains one explicit immutable 40-character `rules_source_sha`. Git is now the **preferred source-acquisition path**, not the identity itself. Prefer an already-authorized local Git repository and obtain a clean detached exact-SHA planner snapshot with the canonical sequence:

```bash
git fetch origin main --prune
rules_source_sha="$(git rev-parse origin/main)"
git worktree add --detach <temporary-planner-path> "$rules_source_sha"
```

Execute planner Python only from that exact clean snapshot. Reuse a clone/object database when available; persistence is an optimization, never a correctness dependency.

## Connector/API fallback

Git authentication or Git availability is **not** a hard architectural dependency. If current `main` cannot be fetched and verified through Git, use the exact-SHA connector/API materialization described by `planning/PLANNER_MATERIALIZATION.json`. Pin one exact `rules_source_sha`, fetch every required path from that SHA, verify reconstructed/chunked bytes with Git blob-SHA semantics, and never mix commits. Connector mode runs in an ordinary temporary directory and does not require `.git` or a Git executable.

If neither an exact Git snapshot nor exact-SHA connector materialization can be obtained, fail closed. Never use stale local source and never manufacture synthetic Git metadata. Never manufacture a synthetic HEAD or fake repository identity.

GitHub Actions planner execution remains prohibited. GitHub Actions is deterministic downstream/credentialed infrastructure only.

## Local repository-state inspection

In Git mode, use the exact detached snapshot for repository-owned planner state. In connector fallback, materialize only manifest-required source/data plus targeted state needed by the selected profile.

## Mandatory local Python checkpoints

Run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

Consume actual output. `planner_contract` exposes both profiles and a shared-contract fingerprint. Daily and Ad-hoc must report the same shared fingerprint.

## Shared automatic background replenishment and continuation

`REPLENISH` is a recoverable planner state, not a terminal planner failure. Daily and Ad-hoc use this exact shared procedure before freezing final backgrounds or committing a ranked pool.

1. Consume the exact readiness total/category/duration deficits.
2. Before creating anything, inspect immutable discovery requests/results/readiness manifests and Background Management runs for a compatible unfinished replenishment attempt. **Resume it instead of creating duplicate requests.** A planner retry or later scheduled invocation must be able to continue an earlier attempt idempotently.
3. If no compatible unfinished attempt exists, create exactly one immutable discovery request under `youtube-shorts-bot/content/background-sourcing/discovery-requests/` using the live schema and commit it with the canonical `[media discovery]` convention.
4. Background Management may use repository code and GitHub-held provider credentials for deterministic provider discovery and readiness persistence. It must not perform ChatGPT-owned visual/editorial approval or video processing. Its discovery responsibility ends when it persists the immutable discovery result containing exact-source preview URLs.
5. After triggering or finding the matching Background Management discovery run, **do not return merely because the run is queued or in progress**. Poll/refresh its status and current `main` for a bounded continuation window of up to 10 minutes, using short checks rather than one long blocking sleep. As soon as the matching immutable discovery result appears, continue immediately. If the run reaches a terminal failure, report infrastructure/authentication failure with its evidence. If the 10-minute continuation window expires while that required discovery run is still legitimately pending, return `DEFERRED_REPLENISHMENT` rather than `FAILED`; preserve the immutable attempt identity so the next invocation resumes it.
6. Consume the matching discovery result only; never fabricate provider IDs, durations, renditions or preview URLs. Once the matching immutable discovery result exists, provider discovery is complete and the planner must continue into visual review in the **same planner invocation** whenever a trustworthy exact-source visual path exists.

   The canonical review path is ChatGPT/Work-local exact-source review:
   - Use the exact immutable `preview_video_url`, `preview_image_url`, and/or Pexels `source_page` from the discovery result. Never substitute a visually similar asset.
   - Prefer native web/browser/image-capable exact-source inspection when it can prove the same provider asset identity.
   - When the execution environment can place the exact discovered media into local working storage, use that exact downloaded source and inspect representative frames and/or a short motion sample locally with available media tooling. A generic authenticated Git checkout is not required for this visual step.
   - When local Python has outbound HTTPS and FFmpeg/media tooling, the canonical repository helper may be used directly:

```bash
PYTHONPATH=youtube-shorts-bot python -m media.preview_review_materializer \
  --discovery-result <discovery-result.json> \
  --output-dir <temporary-review-evidence-dir> \
  --include-motion-evidence
```

   - If local Python networking is unavailable but another exact download primitive is available, download the exact immutable `preview_video_url`/`preview_image_url` through that surface, then inspect/extract representative local frames with available tooling. Local Python outbound HTTP is therefore **not** a correctness dependency.
   - A public/runtime review-evidence workflow may exist as an optional non-blocking fallback transport, but it is never required for canonical planner continuation. Its absence, startup failure, expired artifact, or terminal failure must not block the planner when local or native exact-source evidence is available.
   - Failure of one evidence transport must cause the planner to try the next available exact-source transport rather than terminate the replenishment attempt.

   Inspect actual pixels for every proposed source. If a still image is genuinely insufficient to judge a candidate and an exact-source video/representative-frame surface is available, inspect representative frames or short playback; full-length/end-to-end playback is unnecessary. A successful fetch/extraction is **not** approval: ChatGPT/Work must still make the semantic/visual decision. Metadata-only approval remains prohibited. Reject candidates whose exact-source evidence remains inaccessible or is visually unsuitable and continue through the remaining discovery set. If too few candidates survive, continue with the next immutable discovery attempt under the same readiness deficits rather than weakening review.

   Only when **all available exact-source visual channels** are genuinely unusable for the discovery set may the planner stop before a readiness manifest. Report this as `EVIDENCE_ACCESS_BLOCKED`, include the attempted evidence channels and affected discovery-result path, and do not mislabel it `DEFERRED_REPLENISHMENT`.
7. Create exactly one immutable readiness manifest from visually approved candidates only. Before writing it, re-check whether that attempt already has a manifest or accepted registry update; reuse existing state on retry.
8. Commit the readiness manifest so Background Management performs canonical provider re-enrichment/persistence and reserve fallback.
9. Again, **do not stop merely because this second Background Management run is queued/in progress**. Poll/refresh for up to 10 minutes. Continue as soon as the registry commit appears. A terminal workflow failure is an infrastructure/authentication failure; a still-running job at the bounded deadline is `DEFERRED_REPLENISHMENT`, not planner failure.
10. Refresh current `main`, repin planner-relevant state as required by drift policy, rerun `planner_contract` and `media_readiness`. If readiness is still `REPLENISH`, resume/create the next immutable replenishment attempt and repeat. Candidate finalization may begin only after `PASS`.

`DEFERRED_REPLENISHMENT` is valid only when a **required** matching Background Management discovery or readiness-ingestion workflow is still legitimately queued/in-progress after its bounded wait. It is **not** valid merely because visual review remains, because local Python lacks outbound HTTP, because a browser/connector cannot render one provider URL, because an optional public evidence workflow failed, or because one candidate's preview/extraction failed. A `DEFERRED_REPLENISHMENT` report must include profile, plan date, rules/source SHA used before drift refresh, discovery request ID/path, matching required workflow run ID/status, matching discovery-result/readiness-manifest paths if present, current readiness deficits, and the exact continuation point. It must explicitly say that no ranked pool/request was created. This state is resumable and must never be described as a creative/content failure.

Do not bypass provider discovery by guessing metadata from public pages. Do not move creative/editorial review into GitHub Actions. Do not create a second discovery request simply because an existing required workflow is still running. Do not make Git, local Python outbound HTTP, or any public review-evidence workflow a prerequisite for visual review: exhaust the available exact-source native/local surfaces according to step 6, reject candidate-specific evidence failures individually, and use `EVIDENCE_ACCESS_BLOCKED` only when no trustworthy exact-source visual channel remains usable.

## Shared precommit engine

After complete candidate authorship, run exactly one shared precommit engine. In preferred Git mode also attest the detached checkout:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile <daily|adhoc> \
  --pool <temporary-pool.json> \
  --rules-source-sha <rules_source_sha> \
  --verify-git-head
```

In connector fallback omit `--verify-git-head`. The explicit exact SHA and verified materialized bytes are authoritative. Compatibility wrappers may remain but contain no independent validation logic. FAIL CLOSED if the exact precommit module cannot execute; manual schema checks, arithmetic, downstream admission/promotion or GitHub Actions are not substitutes.

## Creative ownership

ChatGPT/Work retains creative ownership: premise generation/rejection, duplicate reasoning, analytics/editorial judgment, full story/title/metadata authoring, voice/punchline semantics, exact logical backgrounds, treatment choices, visual preview approval/fallback reasoning and final rank. Python validates contracts; it does not creatively rerank or repair.

## Planner-relevant drift

Before committing immutable planner output, refresh current `main`. In Git mode fetch `origin/main`; if it changed, classify changed paths with `planning.planner_drift`. Apply the returned policy: `rules` refreshes source and reruns contract/readiness/precommit; `media` refreshes media state and reruns readiness/background validation/precommit; `history` refreshes creative-history inputs and duplicate/analytics reasoning and reruns precommit when pool bytes change; `operational` does not restart creative planning solely because HEAD moved; `unknown` performs a full refresh. Connector fallback applies the same classifier when changed paths are safely available, otherwise conservatively performs a full refresh.

The final immutable pool bytes must exactly match the successful precommit `draft_sha256`.

## Performance diagnostics

Measure planner stages with a monotonic clock where practical and report `materialization_mode`, `git_reused`, `bootstrap_ms`, `git_fetch_ms`, `materialization_ms`, `contract_ms`, `media_readiness_ms`, `state_load_ms`, `precommit_ms`, and `commit_ms`. Diagnostics are observability only.

## Shared architecture boundary

Shared behavior exists exactly once. If a feature applies to both profiles, classify it `SHARED` and implement it here/shared code/configuration. Profiles contain only genuine differences such as pool/count policy, identity/uniqueness policy, scheduling/publication mode and promotion cardinality.

Do not add schema, semantic, narration/voice, punchline, background, media-readiness, request-validator, replenishment-continuation or common-publication overrides to a profile.

Git is a source-acquisition mechanism, not the planner. ChatGPT/Work owns creative planning and planner-time visual review; local canonical Python proves the frozen plan is valid; private GitHub Actions owns deterministic control-plane/provider/state work; the public stateless runtime owns production execution. GitHub Actions does not own creative/editorial approval.
