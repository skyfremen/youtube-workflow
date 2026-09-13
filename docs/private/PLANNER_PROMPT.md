# Wacky Dramas — Shared Planner Execution Contract

Daily and Ad-hoc are profiles of **one planner**. This file is the canonical shared bootstrap, execution, materialization, background-replenishment continuation and drift contract. `youtube-shorts-bot/planning/DAILY_PLANNER_PROMPT.md` and `youtube-shorts-bot/planning/ADHOC_PLANNER_PROMPT.md` select a profile and add only mode-specific instructions.

If older mode-specific rule text duplicates execution-environment/bootstrap, planner-source-read or background-replenishment instructions, this shared contract wins. Creative/business rules in the mode-specific rules remain mandatory unless current executable repository code/configuration supersedes them.

## Repository-first identity and canonical ChatGPT/Work acquisition

The planner identity is one explicit immutable 40-character `rules_source_sha`.

**For ChatGPT/Work planner execution, the authorized GitHub connector/API is the canonical repository source-acquisition mechanism. Shell Git access to github.com is neither attempted nor required.**

ChatGPT/Work must begin directly with the authorized GitHub connector/API. Do not use shell Git as a prerequisite, preferred path, health check, initial attempt, or fallback prerequisite. In particular, do not run `git fetch`, `git clone`, `git pull`, `git ls-remote`, `git rev-parse origin/main`, or create Git worktrees. Do not test local DNS reachability to `github.com`, modify Git proxy/DNS/network configuration, or attempt Git-network repair. A `.git` directory and a Git executable are not required for the canonical planner path.

The canonical bootstrap is:

1. Resolve the exact current `main` commit SHA for `skyfremen/youtube-workflow` through the authorized GitHub connector/API.
2. Freeze that lowercase 40-character commit SHA as `rules_source_sha` for the planner snapshot.
3. Fetch `youtube-shorts-bot/planning/PLANNER_MATERIALIZATION.json` from that exact SHA, not from a mutable branch view.
4. Materialize every path required by that exact manifest from the same exact `rules_source_sha`. Never mix files from different commits.
5. For every materialized path, record the connector-returned source commit SHA and Git blob SHA/equivalent canonical blob identity in `materialization-evidence.json`. Never infer, synthesize, or fabricate evidence.
6. Run the materialization verifier from the temporary materialized tree:

```bash
PYTHONPATH=<temporary-planner-path>/youtube-shorts-bot \
python -m planning.materialization_verify \
  --profile <daily|adhoc> \
  --root <temporary-planner-path> \
  --rules-source-sha <rules_source_sha> \
  --evidence <materialization-evidence.json>
```

7. Continue only when verification returns `status=PASS`.
8. Then run the shared planner checkpoints from the same materialized snapshot:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

Connector materialization is normal planner work, not a fallback failure state. If connector/API access and local file execution are available, the current invocation must perform the materialization rather than report that it has not yet been done.

`MATERIALIZATION_BLOCKED` is legal only when a concrete named exact-SHA connector fetch/reconstruction/write operation actually fails, required connector-returned evidence is invalid or inconsistent, or `planning.materialization_verify` returns `FAIL`. Report the exact path/operation and verifier error. `git fetch failed`, `github.com could not resolve`, `no Git checkout exists`, `Git is unavailable`, and `connector files have not been materialized yet` are not valid `MATERIALIZATION_BLOCKED` reasons for ChatGPT/Work.

Never use stale local source. Never manufacture synthetic Git metadata, a synthetic HEAD, or a fake repository identity.

### Real Git checkout mode outside ChatGPT/Work

A real verified Git checkout may still be used by developers, CI, GitHub Actions, or other execution contexts that genuinely operate from Git metadata. In that separate mode, `--verify-git-head` remains an optional integrity check and `planning.planner_drift --base-sha/--head-sha` may use local Git objects. This developer/CI mode is not the normal ChatGPT/Work planner bootstrap and must never be attempted before or instead of the connector/API path in ChatGPT/Work.

GitHub Actions planner execution remains prohibited. GitHub Actions is deterministic downstream/credentialed infrastructure only.

## Local repository-state inspection

For ChatGPT/Work, inspect repository-owned planner state through connector/API reads pinned to `rules_source_sha` and materialize only the manifest-required source/data plus targeted state needed by the selected profile. Targeted state reads must use the same exact SHA unless the drift procedure explicitly advances the snapshot.

A persistent local cache is optional. Reuse is valid only for bytes whose connector evidence was already verified for the identical immutable SHA. Persistence is never a correctness dependency.

## Mandatory local Python checkpoints

Run locally in ChatGPT/Work from the verified materialized tree:

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
10. Re-resolve current `main` through the authorized GitHub connector/API, apply the shared drift policy, rematerialize only required affected state, rerun `planner_contract` and `media_readiness`, and repeat replenishment if required. Candidate finalization begins only after `PASS`.

Do not bypass provider discovery, fabricate metadata, or move creative/editorial approval into GitHub Actions. Private GitHub Actions may perform deterministic provider/media **transport** work; ChatGPT/Work performs the visual decision.

## Shared precommit engine

After complete candidate authorship, run exactly one shared precommit engine from the verified connector-materialized planner tree:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile <daily|adhoc> \
  --pool <temporary-pool.json> \
  --rules-source-sha <rules_source_sha>
```

Do **not** add `--verify-git-head` for the canonical ChatGPT/Work connector-materialized path. Its integrity proof is the exact `rules_source_sha` plus exact connector-materialized bytes plus verified per-file source/blob evidence plus `planning.materialization_verify PASS`.

`--verify-git-head` remains available only for a genuine real-Git checkout context such as developer tooling or CI. Do not fabricate a local Git HEAD to satisfy it. Compatibility wrappers may remain but contain no independent validation logic. FAIL CLOSED if the exact precommit module cannot execute; manual schema checks, arithmetic, downstream admission/promotion or GitHub Actions are not substitutes for planner-time pre-commit.

## Creative ownership

ChatGPT/Work retains creative ownership: premise generation/rejection, duplicate reasoning, analytics/editorial judgment, full story/title/metadata authoring, voice/punchline semantics, exact logical backgrounds, treatment choices, visual preview approval/fallback reasoning and final rank. Python validates contracts; it does not creatively rerank or repair.

## Planner-relevant drift

Immediately before committing immutable planner output, query the authorized GitHub connector/API for the current `main` SHA again. Do not run `git fetch origin main` or any other shell Git network command to detect drift.

If the connector-returned current-main SHA still equals `rules_source_sha`, continue. If it changed:

1. Treat the new connector-returned SHA as `latest_main_sha` and obtain the required exact-SHA state through the connector/API.
2. Obtain the changed-path set through connector/API compare evidence when available and apply the existing deterministic `planning.planner_drift` category policy using supplied paths. The canonical connector form is repeatable `--changed-path` input or the connector-SHA transition helper; neither requires Git.
3. If a trustworthy changed-path set is unavailable, conservatively use the existing full-refresh semantics.
4. `rules` refreshes source and reruns materialization verification, contract/readiness and complete precommit; `media` refreshes media state and reruns readiness/background validation/precommit; `history` refreshes creative-history inputs and duplicate/analytics reasoning and reruns precommit when pool bytes change; `operational` does not restart creative planning solely because the branch moved; `unknown` performs a full refresh.
5. Freeze the refreshed exact SHA as the new `rules_source_sha` when the policy requires a source refresh. Never mix old and new snapshot bytes.

The final immutable pool bytes must exactly match the successful precommit `draft_sha256`.

## Performance diagnostics

Measure planner stages with a monotonic clock where practical and report `materialization_mode`, `bootstrap_ms`, `connector_resolve_ms`, `materialization_ms`, `contract_ms`, `media_readiness_ms`, `state_load_ms`, `precommit_ms`, and `commit_ms`. Diagnostics are observability only. Developer/CI Git-mode diagnostics may additionally report Git-specific timings, but those are not part of the ChatGPT/Work canonical bootstrap.

## Shared architecture boundary

Shared behavior exists exactly once. If a feature applies to both profiles, classify it `SHARED` and implement it here/shared code/configuration. Profiles contain only genuine differences such as pool/count policy, identity/uniqueness policy, scheduling/publication mode and promotion cardinality.

Do not add schema, semantic, narration/voice, punchline, background, media-readiness, request-validator, replenishment-continuation or common-publication overrides to a profile.

The authorized GitHub connector/API is the ChatGPT/Work source-acquisition mechanism, not the planner. ChatGPT/Work owns creative planning and planner-time visual review; local canonical Python proves the frozen plan is valid; private GitHub Actions owns deterministic control-plane/provider/state work; the public stateless runtime owns production execution. GitHub Actions does not own creative/editorial approval.
