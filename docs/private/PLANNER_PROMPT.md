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
7. Ingest only schema-v2 readiness-manifest candidates that bind byte-for-byte to those immutable approvals and retain all existing visual, safety, duration, rendition and caption-readability requirements. Background Management revalidates provider facts, persists the registry and appends a post-ingestion readiness event. Never lower thresholds to obtain PASS.
8. Re-run media readiness. If `PASS`, immediately resume the **same original planner invocation** at the phase that was waiting for media and continue candidate authorship/checkpoint/commit.
9. If still `REPLENISH` and attempt < 5, rotate/broaden the category's canonical search vocabulary, increment the same session attempt and repeat automatically. An individual candidate rejection is never a reason to end the planner invocation.
10. Only after attempt 5 remains unable to satisfy readiness may the planner stop with `E_MEDIA_REPLENISH_EXHAUSTED`, reporting exact remaining deficits, attempts and rejection reasons. A genuine bounded external wait may still report `DEFERRED_REPLENISHMENT` under the background-media strategy.

This loop is event-oriented and resumable: if ChatGPT/Work is interrupted, the next execution inspects immutable discovery/review/readiness state and resumes the compatible unfinished session instead of starting duplicate work.

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
