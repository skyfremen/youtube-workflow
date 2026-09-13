# Wacky Dramas — Shared Planner Execution Contract

Daily and Ad-hoc are profiles of one planner. Repository code/configuration at exact current `main` is authoritative. The authorized GitHub connector/API is the canonical ChatGPT/Work repository source; shell Git is neither attempted nor required.

## Repository-first identity

Freeze one exact lowercase 40-character `rules_source_sha`. Fetch the current `PLANNER_MATERIALIZATION.json`, standalone `planning/connector_checkpoint.py`, selected profile rules, story/background rules and targeted state through exact-SHA connector reads. Stage locally only the standalone checkpoint, authored pool and small connector-evidence JSON. `CHECKPOINT_STAGING_BLOCKED` is legal only when that connector-native checkpoint cannot actually be fetched/staged/executed; Git/DNS/checkout failure is not a blocker.

## Shared automatic background replenishment and continuation

`REPLENISH` is a recoverable intermediate planner state. It is **not** a final result while bounded recovery remains possible. Daily and Ad-hoc must use the same procedure and preserve the original planner invocation throughout it.

1. Read current total/category/duration/sequence deficits from repository-owned readiness evidence.
2. Resume a compatible unfinished replenishment session for this planner invocation; otherwise create one stable session identity. Never create a second Daily/Ad-hoc planning invocation merely because replenishment is needed.
3. Use discovery-request schema v3 for automatic retries. Freeze `planner_invocation_id`, profile/mode, Singapore date and `initial_rules_source_sha`; target only positive `category_deficits`; carry `attempt` (1-5) and the stable `replenishment_session_id`; and exclude active+verified assets plus every provider asset already discovered or visually reviewed in this session.
4. Private Background Management performs deterministic provider discovery, exact-source transport/contact sheets/artifact upload and deterministic persistence only. It never performs ChatGPT-owned visual approval or creative planning.
5. Review exact-source visual evidence. Persist every approve/reject decision as immutable repository evidence under `content/background-sourcing/review-decisions/<request_id>.json` before continuing. Review-decision schema v2 binds the batch to the frozen planner invocation and exact immutable review-evidence index, then records per-provider `decision`, `discovery_category`, `reviewed_category`, `category_match`, reason, source, and approved ingest metadata when applicable. The provider search category is provenance, not truth: an asset may satisfy a deficit only when ChatGPT's visual review confirms that category. Misleading search results are rejected.
6. Treat the immutable review-decision state as authoritative session memory. `media.pexels_discovery` automatically unions all provider IDs already reviewed in the same `replenishment_session_id` with request-side `exclude_provider_asset_ids`; do not depend on ChatGPT perfectly reconstructing exclusions after interruption.
7. After persisting a schema-v2 review decision, **continue the same invocation immediately**; do not stop merely because the visual-review step completed. If the current attempt has one or more approved category matches, create and commit exactly one immutable **schema-v2 readiness manifest** under `content/background-sourcing/readiness/`. It must preserve the same `replenishment_session_id`, `planner_invocation`, `attempt`, and `discovery_request_id`; `review_decision_ids` must exactly match candidate order; every candidate must be the approved candidate metadata from its immutable decision plus its deterministic `review_decision_id`. Validate the manifest against the current schema/decision contract before commit. Never create a schema-v1 manifest for a resumable schema-v3 session.
8. The readiness-manifest commit is the deterministic ingestion hand-off. Background Management must ingest only candidates bound byte-for-byte to immutable approvals, revalidate provider facts, persist the registry, re-run media readiness, and append exactly one immutable post-ingestion event at `content/background-sourcing/replenishment-events/<replenishment_session_id>/aNN-readiness.json`. The event is the authoritative completion receipt for that attempt. Do not infer ingestion success merely from a workflow start, a readiness manifest, or an updated registry.
9. After committing the readiness manifest, use the authorized GitHub connector/API to re-read current repository state for that same session until either the corresponding post-ingestion event is present or a genuine bounded infrastructure wait is established. Do not end the planner merely because the event was not present on the first read. When the event appears, follow its `continuation_phase` mechanically:
   - `READY_TO_RESUME`: immediately resume the **same original planner invocation** at the phase that was waiting for media and continue candidate authorship/checkpoint/commit.
   - `NEED_DISCOVERY`: if `attempt < 5`, create and commit the next schema-v3 targeted discovery request for the same session/invocation, increment the attempt, rotate/broaden canonical search vocabulary as allowed by current media strategy, and continue the loop automatically.
   - `EXHAUSTED`: stop only with `E_MEDIA_REPLENISH_EXHAUSTED` and the exact remaining deficits/attempt/rejection diagnostics.
10. If an attempt has **zero approved candidates**, no readiness manifest or ingestion is required. This is not a terminal planner result. If `attempt < 5`, immediately create the next targeted schema-v3 discovery request for the same session/invocation and continue. Only attempt 5 may transition to `EXHAUSTED`.
11. An individual candidate rejection, an all-rejected batch before attempt 5, completion of visual review, creation of review evidence, creation of a readiness manifest, workflow dispatch/start, or a first missing-event read are **never** valid reasons to terminate the planner invocation.
12. A genuine bounded external/infrastructure wait may report `DEFERRED_REPLENISHMENT` only when the current background-media strategy's defer conditions are actually met. The report must identify the exact session, attempt, expected next immutable artifact/event, and why it cannot yet be obtained. It must not be used as a substitute for performing the connector-native continuation loop.
13. On every resumed execution, reconstruct the phase from immutable repository state before taking action. Never duplicate a discovery request, review decision, readiness manifest, readiness event, or planner invocation. If the expected immutable artifact already exists with matching identity, consume it and continue from the next phase.

The required state machine is therefore:

`REPLENISH -> NEED_DISCOVERY -> WAITING_DISCOVERY -> WAITING_EVIDENCE -> NEEDS_VISUAL_REVIEW -> (NEED_DISCOVERY when all rejected | NEEDS_INGESTION when approvals exist) -> WAITING_INGESTION -> (READY_TO_RESUME | NEED_DISCOVERY | EXHAUSTED)`.

`READY_TO_RESUME` is not a new planning invocation: it returns control to the exact Daily/Ad-hoc invocation that entered `REPLENISH`.

## Connector evidence and checkpoint

Before final pool commit, assemble connector evidence with repository, exact `rules_source_sha`, checkpoint blob identity, current-main drift PASS, media-readiness PASS, uniqueness PASS and evidence only for selected background IDs. Never invent PASS evidence or copy the whole registry merely for checkpointing.

Run the exact-SHA standalone checkpoint:

```bash
python connector_checkpoint.py validate --profile <daily|adhoc> --pool <pool.json> --rules-source-sha <rules_source_sha> --evidence <connector-evidence.json>
```

All expected candidates must PASS and `commit_allowed=true`; committed bytes must match `draft_sha256`. Re-query current `main` immediately before validation/commit and apply the repository drift policy if it moved.

## Ownership and production boundary

ChatGPT/Work owns premise generation/rejection, duplicate reasoning, analytics/editorial judgment, complete story/title/metadata writing, voice/punchline semantics, exact logical background choices/ranges, visual review/fallback reasoning and final rank. Repository code and the standalone checkpoint own deterministic validation. GitHub Actions may perform deterministic media transport/state work and downstream production but must not creatively generate/rank the Daily/Ad-hoc pool.

Only after checkpoint PASS may ChatGPT/Work commit the immutable ranked pool through the authorized GitHub connector/API. Existing private workflows then validate/promote mechanically, create canonical immutable requests and dispatch the public stateless runtime. Developers/CI may separately use repository-native modules from a genuine checkout.
