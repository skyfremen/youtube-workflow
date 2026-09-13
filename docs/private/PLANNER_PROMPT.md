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

### Connector materialization completion gate

Selecting connector/API fallback is an execution path, not a return condition. When connector/API access and local file execution are available, the current planner invocation must perform the materialization work instead of reporting that it has not yet been done.

For the selected profile:

1. Materialize `youtube-shorts-bot/planning/PLANNER_MATERIALIZATION.json` itself from the pinned `rules_source_sha`.
2. Materialize every path required by that exact manifest from the same exact SHA.
3. For every materialized path, record the connector-returned `rules_source_sha` and Git blob SHA in `materialization-evidence.json`; never invent either value.
4. Run:

```bash
PYTHONPATH=<temporary-planner-path>/youtube-shorts-bot python -m planning.materialization_verify \
  --profile <daily|adhoc> \
  --root <temporary-planner-path> \
  --rules-source-sha <rules_source_sha> \
  --evidence <materialization-evidence.json>
```

5. Connector materialization is complete only when the verifier returns `status=PASS`. Continue immediately to `planner_contract` and `media_readiness`.

`MATERIALIZATION_BLOCKED` is legal only when an exact named connector fetch/reconstruction/write operation actually fails, or the verifier returns `FAIL`. Report the exact path/operation and verifier error code. A generic statement such as “could not complete materialization” or “materialization is unavailable” is not a valid terminal result while connector/API reads and local file execution remain available. Do not return merely because connector files are not yet materialized; materialization is work the current invocation must perform.

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
2. Inspect immutable discovery requests/results/readiness manifests, matching `content/background-sourcing/review-evidence/<request_id>-run-*.json` indexes, and Background Management runs. **Resume a compatible unfinished attempt instead of creating duplicates.**
3. If no compatible attempt exists, create exactly one immutable discovery request with the live schema and canonical `[media discovery]` convention.
4. Private Background Management owns deterministic provider discovery, exact-source **transport-only** review evidence generation and readiness persistence. It may read/download exact Pexels preview media, run FFmpeg to derive representative JPEG contact sheets, upload a private short-lived GitHub artifact, and commit an immutable run-scoped review-evidence index. It must never perform ChatGPT-owned approval, set `verified_preview`, assign semantic metadata/scores, or create the reviewed readiness manifest.
5. After triggering/finding the matching Background Management discovery/evidence run, poll/refresh for up to 10 minutes rather than returning merely because it is queued/in progress. Normal continuation requires the matching immutable discovery result and at least one matching run-scoped review-evidence index with an available artifact. Terminal workflow failure is infrastructure/authentication failure. A still-running required run at the bounded deadline is `DEFERRED_REPLENISHMENT`.
6. Review actual exact-source pixels. Prefer the newest usable indexed private Background Management artifact:
   - Read exact `workflow_run_id`, `artifact_id`, `artifact_name`, `artifact_digest`, and `evidence_manifest_sha256`; never guess a run/artifact.
   - Through the authorized GitHub connection, list the indexed run artifacts, verify identity/digest, download the exact ZIP and extract it locally. Connector-delivered artifact files are the canonical binary bridge and do not require local outbound internet.
   - Verify the extracted evidence-manifest hash and provider/source identity against the immutable discovery result.
   - Inspect actual `*/contact-sheet.jpg` pixels (and exact stills where useful). Artifact creation is transport evidence only; ChatGPT/Work remains the sole visual/editorial approval owner.
   - Reject candidate-specific missing/unsuitable evidence and continue remaining candidates/reserves.

   If an indexed artifact expired, regenerate a new run-scoped evidence artifact/index for the same immutable discovery result when possible. Native exact Pexels inspection, exact preview-image download, and exact preview-video staging remain fallbacks; `media.preview_review_materializer --input-dir` remains available for trustworthy staged bytes.

   `EVIDENCE_ACCESS_BLOCKED` is legal only after usable indexed private artifacts and all other trustworthy exact-source visual transports available to the run are unusable for the remaining candidates needed for readiness. A successful required Background Management evidence run with a missing/mismatched index/artifact is `REVIEW_EVIDENCE_TRANSPORT_FAILED`, not a creative/content failure.
7. Create exactly one immutable readiness manifest from visually approved candidates only. Never overwrite prior immutable state.
8. Commit the readiness manifest so Background Management performs canonical provider re-enrichment/persistence and reserve fallback.
9. Poll/refresh that required ingestion run for up to 10 minutes. Continue when the registry commit appears; terminal failure is infrastructure/authentication failure and a still-running job at the deadline is `DEFERRED_REPLENISHMENT`.
10. Refresh current `main`, apply drift policy, rerun `planner_contract` and `media_readiness`, and repeat replenishment if required. Candidate finalization begins only after `PASS`.

Do not bypass provider discovery, fabricate metadata, or move creative/editorial approval into GitHub Actions. Private GitHub Actions may perform deterministic provider/media **transport** work; ChatGPT/Work performs the visual decision.

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
