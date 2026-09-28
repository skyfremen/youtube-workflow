# Wacky Dramas Audit Remediation Design

Date: 2026-09-27

## Purpose

Implement the approved remediation for audit table items 3, 5, 6, 11, and 12 while preserving the existing three-repository boundaries and all creative behavior. Item 8 is documented as already materially resolved and receives no protocol redesign.

## Constraints

- `youtube-workflow` remains the planner/orchestrator and state source of truth.
- `production-runtime` remains the stateless execution and analytics runtime.
- `youtube-analytics-data` remains passive private data storage with no workflows or orchestration.
- Historical immutable requests, executions, upload intents, uploads, and results are never rewritten.
- Historical incomplete records are not automatically retried, uploaded, scheduled, or converted into synthetic results.
- `PLANNING.md`, creative rules, story selection, publishing cadence, and creative duration targets are not changed.
- Existing cancellation records and slot-release semantics remain unchanged.
- No real YouTube upload is performed for verification.

## Considered Approaches

### Historical lifecycle repair

1. **Read-only audit plus future contract correction — selected.** Add a deterministic auditor, correct future evidence identity, retain legacy compatibility, and strengthen validation. This removes the recurring defect without mutating ambiguous history.
2. Add operator decision records immediately. This provides durable dispositions but adds a new state machine before the historical cases have been reviewed.
3. Automatically recover historical records. Rejected because it can duplicate uploads, schedule into the past, or manufacture results without sufficient evidence.

### Result-ingestion fan-out

1. **Keep current consumer-side reconciliation — selected.** The existing workflow serializes writers and ingests every result missing from history in one derived-state update.
2. Add a producer-side batch coordinator. Rejected for now because independent production jobs finish asynchronously and a coordinator or queue would expand the architecture.
3. Delay ingestion on a schedule. Rejected because it weakens result freshness and recovery visibility.

## Item 3: Lifecycle Audit and Future Evidence Identity

### Current problem

Current V2 production extracts one item from an immutable batch request. Runtime upload evidence reconstructs the remote identity from that local per-content file. As a result, historical V2 evidence commonly names `content/requests/{content_id}.json`, which is not the canonical remote batch path, and labels the item blob as `request_blob_sha`.

The evidence still identifies the expected content and upload, so it does not prove that the wrong video was uploaded. It is nevertheless misleading provenance and prevents a trustworthy cross-repository lifecycle join.

There are also historical request-only, execution-only, and uploaded-without-result records. Those records require operator judgment and remote YouTube evidence; this implementation will report them but not repair them.

### New evidence contract

Future intent and upload evidence use evidence version 2 and carry:

- `content_id`
- `execution_id`
- `request_id`
- canonical batch `request_path`
- `request_source_sha`
- batch `request_blob_sha`
- `item_blob_sha`
- existing upload identity and duplicate-upload fence fields

`runtime/transport.py` passes the canonical execution identity through the local manifest. `runtime/output/state.py` consumes that identity instead of reconstructing it from the extracted local filename.

Version 1 evidence remains readable. It is treated as a legacy alias that can be joined through its immutable execution fence. It is not rewritten.

### Read-only lifecycle auditor

Add a deterministic command in `youtube-workflow` that reads repository state and emits a JSON report to stdout or a caller-supplied output path. It performs no GitHub or YouTube mutations and classifies each content item as:

- request only
- execution without evidence
- uploaded without result
- complete
- legacy evidence alias
- invalid cross-repository relationship

The report validates request, execution, intent, upload, result, and history joins. It records exact identifiers and validation errors without secret values.

### Stronger validation

For new version 2 evidence and results:

- execution identity must match the canonical request batch and item hashes;
- intent and upload evidence must match each other;
- result `execution_id` and `content_id` must match the execution fence;
- result `publish_at` must match the immutable request item;
- result `youtube_video_id` must match verified upload evidence;
- legacy V1 evidence remains accepted through an explicit compatibility path.

No result is synthesized by the auditor.

## Item 5: Reporting Job Status and Staleness

The Reporting API downloader already discovers report types and jobs, paginates listings, downloads immutable report IDs, enforces a per-run budget, and retries unrecorded downloads. The missing behavior is operational visibility while YouTube is still generating the first report.

Enhance the private warehouse job manifest with per-job operational fields:

- `status`: `waiting_for_first_report`, `active`, or `stale`
- `first_observed_at`
- `last_checked_at`
- `available_report_count`
- `latest_report_end_time`
- `first_report_observed_at`, when applicable

A new job starts as `waiting_for_first_report`. It becomes `active` when at least one report is listed. It becomes `stale` only when it still has no reports after a 48-hour grace period. A single aggregated warning reports stale jobs; waiting jobs do not create failure noise.

These fields remain in `youtube-analytics-data/manifest/report-jobs.json`. They are not copied into `context.json` or the compact planner projection. Existing report-download and deduplication semantics remain unchanged.

## Item 6: Complete Targeted Analytics Pagination

Add one internal paginator for YouTube Analytics `reports.query`:

- use a fixed page size of 200;
- set 1-based `startIndex` and `maxResults`;
- append rows in response order;
- stop when a page is shorter than the requested size;
- allow one final empty probe when a result has an exact page-size multiple;
- require all pages to have identical column headers;
- discard the entire logical report if a later page fails or headers drift.

Use it for:

- optional channel breakdown reports;
- per-video traffic-source reports;
- granular and fallback retention queries.

Do not use it for cardinality-bounded per-video metric queries, the YouTube Data API batches, or the already-paginated bulk Reporting API.

No analytics schema version changes. Raw warehouse paths, summary keys, planner projection keys, and context-size boundaries remain unchanged.

## Item 8: Result-Ingestion Batching

No code change is planned. The current result workflow already scans all immutable results missing from history and reconciles them in one derived-state commit. Serialized concurrency and retry-from-latest-main preserve idempotency.

Every runtime result still creates its own immutable source commit and workflow event. Removing those events safely requires a coordinator, queue, or delayed aggregation protocol. That added complexity is not justified by the remaining workflow noise.

## Item 11: Checkout Action Upgrade

Replace all six SHA-pinned `actions/checkout` v4.4.0 references in `youtube-workflow` with the verified v7.0.1 commit SHA:

`3d3c42e5aac5ba805825da76410c181273ba90b1`

Keep the existing `fetch-depth` and `ref` settings. The workflows use GitHub-hosted runners that satisfy the Node runtime requirement. None use `pull_request_target` or an unsafe fork checkout path.

Add a static regression test requiring every external `uses:` reference to use a full 40-character commit SHA and requiring all checkout references to equal the approved version.

## Item 12: Runtime Duration Constant Cleanup

Remove unused `PRODUCTION_TARGET_MIN_SECONDS=120.0` and `PRODUCTION_TARGET_MAX_SECONDS=175.0` from `runtime/base/contract.py`.

Make `segment_duration_seconds` a required keyword-only argument to the background download function. The production resolver already supplies the selected segment length, so this removes a misleading default without changing behavior.

Move these duplicated technical constants into `runtime/base/contract.py` and import them in producer and verifier code:

- black-detection maximum: 0.75 seconds
- default test-render maximum: 5 seconds

Retain unchanged:

- the 178-second production hard ceiling;
- the encode safety margin;
- background source segment bounds;
- planner validation range and creative duration targets.

## Error Handling

- Lifecycle auditing reports every discovered invalid join in deterministic order and exits nonzero only for malformed repository-level input that makes the report unreliable.
- Future evidence creation fails before upload if canonical immutable identity is absent or inconsistent.
- Paged analytics reports are atomic: a failed later page never produces partial stored data.
- Reporting jobs within the 48-hour grace period are informational, not failures.
- Stale reporting jobs produce one bounded warning rather than one warning per job.
- Workflow upgrade failures remain visible as failed GitHub Actions checks.

## Testing

### `youtube-workflow`

- lifecycle classification matrix for current V2 and legacy V1 records;
- canonical request/execution/evidence/result joins;
- legacy evidence compatibility without rewriting;
- deterministic, read-only auditor behavior;
- result publication time and YouTube video ID mismatch rejection;
- workflow action SHA pinning;
- full planner unit suite and self-test;
- explicit assertion that `PLANNING.md` is unchanged.

### `production-runtime`

- evidence V2 creation from canonical transport identity;
- V1 retry compatibility and duplicate-upload fencing;
- analytics pagination across multiple pages, short pages, exact multiples, empty reports, header drift, and later-page failure;
- later-page rows for optional reports, Shorts traffic, and retention;
- reporting job transitions from waiting to active and waiting to stale;
- 48-hour grace-period boundary and aggregated warning behavior;
- removed duration constants and required background duration;
- shared technical threshold boundary tests;
- full runtime unit, self-test, background-contract, and preflight-contract suites.

## Rollout and Verification

1. Implement lifecycle auditor and future evidence contract with backward compatibility.
2. Implement analytics pagination and reporting-job status.
3. Upgrade checkout action pins and run affected workflows.
4. Clean runtime constants and run all runtime verification.
5. Commit logical changes directly to current `main` only after re-reading each target file and confirming the branch has not advanced.
6. Do not trigger a synthetic production upload. Validate the evidence V2 path on the next normal production run.

## Out of Scope

- Historical automatic uploads, retries, rescheduling, or result fabrication.
- Operator disposition records for historical cases.
- Result producer batching or new queue infrastructure.
- Repository visibility or token-scope changes.
- External scheduler monitoring, notifications, repository-growth management, or live-upload tests.
- Any creative planner or publishing-strategy change.
