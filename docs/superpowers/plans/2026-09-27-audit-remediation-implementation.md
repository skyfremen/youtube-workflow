# Wacky Dramas Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct future lifecycle evidence, add a read-only lifecycle auditor, complete targeted analytics collection, expose Reporting API job freshness, update workflow checkout pins, and remove stale runtime duration constants without changing creative or publishing behavior.

**Architecture:** `youtube-workflow` gains read-only lifecycle auditing and stronger result joins; `production-runtime` carries canonical batch and item identity through upload evidence and owns analytics completeness and runtime cleanup. `youtube-analytics-data` receives only additional manifest fields through the existing analytics writer and remains workflow-free. Result batching is already adequate and receives no code change.

**Tech Stack:** Python 3.12, `unittest`, GitHub Actions YAML, GitHub Contents API, YouTube Data/Analytics/Reporting APIs.

**Spec:** `docs/superpowers/specs/2026-09-27-audit-remediation-design.md`

## Global Constraints

- Preserve `youtube-workflow` as planner/orchestrator, `production-runtime` as stateless execution, and `youtube-analytics-data` as passive storage.
- Never rewrite historical immutable requests, executions, evidence, uploads, results, or analytics data.
- Never automatically retry historical uploads, schedule into the past, or synthesize results.
- Do not modify `PLANNING.md`, creative rules, story selection, publishing cadence, or creative duration targets.
- Preserve existing cancellation-record behavior and publication-slot allocation.
- Do not trigger a real YouTube upload for verification.
- Use test-first development and logical commits directly against fresh current `main` ancestry.

## Review Focus

- A rerun encountering historical evidence V1 must validate its legacy alias and must not create evidence V2 over the existing file; covered in Task 2.
- A lifecycle audit with malformed or duplicate immutable files must report deterministic invalid joins without mutating state; covered in Task 3.
- A paginated Analytics response that changes headers or fails on page 2 must return no partial logical dataset; covered in Task 5.
- A Reporting job observed just before and exactly at the 48-hour boundary must transition predictably without warning spam; covered in Task 4.
- A checkout upgrade must preserve every existing `fetch-depth`, `ref`, permission, trigger, and concurrency setting; covered in Task 6.

---

### Task 1: Carry Canonical Batch and Item Identity Through Runtime

**Files:**
- Modify: `production-runtime/runtime/transport.py`
- Modify: `production-runtime/runtime/core.py`
- Modify: `production-runtime/runtime/engine/pipeline.py`
- Modify: `production-runtime/runtime/tests/test_transport.py`
- Create: `production-runtime/runtime/tests/test_execution_identity.py`

**Interfaces:**
- Consumes: execution V2 fields `request_id`, `request_path`, `request_source_sha`, `request_blob_sha`, and `item_blob_sha`.
- Produces: execution manifest V2 and `request_sources[local_request]` with the same five canonical fields plus `content_id` and `execution_id`; child processes receive it as `REQUEST_IDENTITY_JSON`.

- [ ] **Step 1: Write failing transport tests**

Add tests asserting that `fetch_execution()` emits `manifest_version == 2`, preserves canonical batch `request_blob_sha`, stores local `item_blob_sha` separately, and includes the exact request/execution IDs and canonical request path.

- [ ] **Step 2: Run the transport tests and confirm RED**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_transport -v`

Expected: FAIL because the current manifest is version 1 and labels the item blob as `request_blob_sha`.

- [ ] **Step 3: Implement manifest V2 in `fetch_execution()`**

Keep `fetch_execution(execution_id, source_sha, output)` unchanged externally. Emit `manifest_version: 2` and a source mapping containing `execution_id`, `content_id`, `request_id`, `request_path`, `request_source_sha`, batch `request_blob_sha`, and `item_blob_sha`.

- [ ] **Step 4: Write failing coordinator tests**

In `test_execution_identity.py`, assert that `core.run()` accepts only manifest V2, that `ProductionPipeline._env()` uses `item_blob_sha` for local-file integrity, and that `REQUEST_IDENTITY_JSON` contains the complete canonical mapping.

- [ ] **Step 5: Run the coordinator tests and confirm RED**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_execution_identity -v`

Expected: FAIL because the coordinator only accepts manifest V1 and exports only two legacy variables.

- [ ] **Step 6: Implement coordinator propagation**

Update `core.run(manifest_path)` and `ProductionPipeline._env(request)` to accept manifest V2, export `SOURCE_COMMIT_SHA=request_source_sha`, retain `SOURCE_REQUEST_BLOB_SHA=item_blob_sha` for local integrity, and export canonical JSON as `REQUEST_IDENTITY_JSON`.

- [ ] **Step 7: Verify Task 1 GREEN**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_transport runtime.tests.test_execution_identity -v`

Expected: all tests PASS.

- [ ] **Step 8: Commit Task 1**

```bash
git add runtime/transport.py runtime/core.py runtime/engine/pipeline.py runtime/tests/test_transport.py runtime/tests/test_execution_identity.py
git commit -m "fix: preserve canonical production evidence identity [COMPLEX-001]"
```

### Task 2: Write Evidence V2 With Legacy V1 Compatibility

**Files:**
- Modify: `production-runtime/runtime/output/state.py`
- Modify: `production-runtime/runtime/output/transfer.py`
- Modify: `production-runtime/runtime/output/verify.py`
- Modify: `production-runtime/runtime/output/result.py`
- Create: `production-runtime/runtime/tests/test_evidence_identity.py`

**Interfaces:**
- Consumes: Task 1 `REQUEST_IDENTITY_JSON` mapping.
- Produces: `identity_for(path, data) -> dict` with canonical V2 identity; `check_identity(evidence, identity) -> None` accepting exact V2 evidence or the documented V1 legacy alias.

- [ ] **Step 1: Write failing identity and compatibility tests**

Test that `identity_for()` rejects missing/malformed canonical JSON, validates the local item against `item_blob_sha`, and returns the canonical batch path/blob. Test that `check_identity()` accepts an existing evidence V1 alias only when its content ID, source SHA, item blob, and legacy per-content path derive exactly from the canonical identity. Test all mismatches fail with `RecoveryBlocked`.

- [ ] **Step 2: Run the evidence tests and confirm RED**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_evidence_identity -v`

Expected: FAIL because current identity reconstruction cannot express canonical batch and item identity.

- [ ] **Step 3: Implement V2 identity and legacy comparison**

Update `identity_for(path, data)` to parse and validate `REQUEST_IDENTITY_JSON`. Update `check_identity()` to branch explicitly on `evidence_version`: exact canonical fields for V2; exact derived alias rules for V1. Reject unknown evidence versions.

- [ ] **Step 4: Write failing intent/upload/result regression tests**

Assert newly created intent and upload records use `evidence_version: 2` and preserve all canonical fields. Assert an existing matching V1 upload causes a no-upload rerun and remains unchanged. Assert mismatched legacy evidence blocks before `videos.insert`.

- [ ] **Step 5: Run the transfer tests and confirm RED**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_evidence_identity -v`

Expected: new-record assertions FAIL while legacy safety assertions identify the current mismatch.

- [ ] **Step 6: Implement evidence V2 writers**

Change intent and `upload_record()` payloads to `evidence_version: 2`. Keep immutable paths unchanged. Ensure `verify.py` and `result.py` consume the shared compatibility validator and never rewrite an existing V1 record.

- [ ] **Step 7: Verify Task 2 GREEN and duplicate-upload fencing**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_evidence_identity -v && PYTHONPATH=runtime python runtime/self_test.py`

Expected: tests PASS and self-test reports `SELF_TEST_PASS`.

- [ ] **Step 8: Commit Task 2**

```bash
git add runtime/output/state.py runtime/output/transfer.py runtime/output/verify.py runtime/output/result.py runtime/tests/test_evidence_identity.py
git commit -m "fix: version upload evidence without rewriting history [COMPLEX-001]"
```

### Task 3: Add Read-Only Lifecycle Audit and Strong Result Joins

**Files:**
- Create: `youtube-workflow/lifecycle.py`
- Modify: `youtube-workflow/pipeline.py`
- Create: `youtube-workflow/tests/test_lifecycle.py`
- Modify: `youtube-workflow/tests/test_pipeline.py`

**Interfaces:**
- Consumes: repository root containing requests, executions, execution evidence, results, and history.
- Produces: `audit_lifecycle(root: Path) -> dict`; `validate_result_relationships(root: Path, result: dict, execution: dict, item: dict) -> None`; CLI `python pipeline.py audit-lifecycle [--output PATH]`.

- [ ] **Step 1: Write the failing lifecycle classification matrix**

Create fixtures for request-only, execution-without-evidence, uploaded-without-result, complete V2, valid legacy V1 alias, duplicate content IDs, malformed evidence, and broken joins. Assert deterministic sorting, counts, exact IDs, and that fixture bytes and mtimes are unchanged after `audit_lifecycle()`.

- [ ] **Step 2: Run the lifecycle tests and confirm RED**

Run: `PYTHONPATH=. python -m unittest tests.test_lifecycle -v`

Expected: FAIL because `lifecycle.py` does not exist.

- [ ] **Step 3: Implement the read-only auditor**

Implement `audit_lifecycle(root: Path) -> dict` with no network calls and no writes. Include schema version, generated classification counts, per-content status, and bounded validation errors; do not include secrets or creative story text.

- [ ] **Step 4: Add and test the CLI**

Add `audit-lifecycle` to `pipeline.py` with optional `--output`; stdout is the default. Test stdout JSON and explicit output-file behavior, and assert no repository state path is modified.

- [ ] **Step 5: Write failing result-join tests**

In `test_pipeline.py`, assert ingestion rejects a result whose `publish_at` differs from its request item or whose `youtube_video_id` differs from upload evidence. Assert complete V2 and documented legacy V1 evidence pass.

- [ ] **Step 6: Run result-join tests and confirm RED**

Run: `PYTHONPATH=. python -m unittest tests.test_pipeline -v`

Expected: mismatch tests FAIL because current ingestion does not check request publication time or upload evidence.

- [ ] **Step 7: Implement `validate_result_relationships()` and call it from `ingest()`**

Validate execution/content/request joins, exact publication time, upload video ID, and V2 or legacy V1 evidence identity. Missing or inconsistent upload evidence must block ingestion; it must not synthesize or modify any record.

- [ ] **Step 8: Verify Task 3 GREEN**

Run: `PYTHONPATH=. python -m unittest tests.test_lifecycle tests.test_pipeline -v && python pipeline.py audit-lifecycle > /tmp/wacky-lifecycle-audit.json && python -m json.tool /tmp/wacky-lifecycle-audit.json >/dev/null`

Expected: tests PASS and current-repository audit produces valid JSON without modifying tracked files.

- [ ] **Step 9: Commit Task 3**

```bash
git add lifecycle.py pipeline.py tests/test_lifecycle.py tests/test_pipeline.py
git commit -m "feat: audit lifecycle state without mutating history [COMPLEX-001 IMPROVEMENT-001]"
```

### Task 4: Track Reporting Job Waiting, Active, and Stale States

**Files:**
- Modify: `production-runtime/runtime/analytics_reporting.py`
- Modify: `production-runtime/runtime/tests/test_analytics_reporting.py`

**Interfaces:**
- Consumes: existing `jobs_manifest`, listed job reports, and UTC `collected_at`.
- Produces: `jobs_manifest["job_status"][report_type_id]` with `status`, `first_observed_at`, `last_checked_at`, `available_report_count`, `latest_report_end_time`, and optional `first_report_observed_at`.

- [ ] **Step 1: Write failing job-state tests**

Test new job/no reports => `waiting_for_first_report`; report present => `active`; 47:59:59 empty => waiting; exactly 48 hours empty => `stale`; multiple stale jobs => one bounded aggregate warning. Test an API listing failure does not overwrite the previous known status.

- [ ] **Step 2: Run Reporting tests and confirm RED**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_analytics_reporting -v`

Expected: FAIL because no `job_status` state exists.

- [ ] **Step 3: Implement status transitions**

Add `update_job_status(report_type_id: str, job: dict, reports: list[dict], statuses: dict, collected_at: datetime) -> dict`. Use valid `createTime` as the earliest observation when available, otherwise retain `first_observed_at`, otherwise use the current timestamp. Mark stale at age `>= 48 hours` with zero reports.

- [ ] **Step 4: Add one bounded stale warning**

After all jobs are checked, append one warning containing the stale count and at most ten report type IDs plus an omitted count. Do not warn for waiting jobs.

- [ ] **Step 5: Verify Task 4 GREEN**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_analytics_reporting -v`

Expected: all Reporting tests PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add runtime/analytics_reporting.py runtime/tests/test_analytics_reporting.py
git commit -m "feat: expose Reporting API generation status [ANALYTICS-002]"
```

### Task 5: Paginate Targeted YouTube Analytics Reports Atomically

**Files:**
- Modify: `production-runtime/runtime/analytics.py`
- Modify: `production-runtime/runtime/tests/test_analytics_v3.py`
- Modify: `production-runtime/runtime/tests/test_analytics_retention.py`

**Interfaces:**
- Consumes: `analytics_report(params: dict, token: str) -> dict`.
- Produces: `analytics_report_all(params: dict, token: str, report_fn=analytics_report, page_size: int = 200) -> dict` with complete ordered rows and stable headers.

- [ ] **Step 1: Write failing paginator unit tests**

Test two pages, short-page termination, an exact-full page followed by an empty probe, omitted rows on the first response, constant `maxResults=200`, 1-based `startIndex` progression by actual row count, header drift rejection, overfull-page rejection, and page-2 exception with no returned partial result.

- [ ] **Step 2: Run paginator tests and confirm RED**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_analytics_v3 -v`

Expected: FAIL because `analytics_report_all()` does not exist.

- [ ] **Step 3: Implement `analytics_report_all()`**

Copy caller parameters, override paging fields per request, preserve the first response metadata and header representation, append raw row arrays, and return only after complete termination. Raise on header drift, an overfull page, or any later-page error.

- [ ] **Step 4: Write failing integration tests for optional reports and traffic sources**

Put geography/device rows and a SHORTS traffic row only on page 2. Assert they appear in existing output keys. Assert page-2 failure omits only that optional dataset and records the existing safe warning.

- [ ] **Step 5: Route applicable queries through the paginator**

Use `analytics_report_all()` in `collect_optional_analytics_reports()` and `collect_per_video_traffic_sources()`. Keep cardinality-bounded per-video metric queries unchanged.

- [ ] **Step 6: Write failing retention paging tests**

Assert `run()` injects the paginator into retention collection, preserves more than 200 curve rows, applies paging to the core-metric fallback, and writes no curve/complete checkpoint when page 2 fails.

- [ ] **Step 7: Route retention through the paginator**

In `run()`, inject `lambda params: analytics_report_all(params, token)` into `collect_retention()`. Do not import `analytics.py` from `analytics_retention.py`.

- [ ] **Step 8: Verify Task 5 GREEN and schema stability**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_analytics_v3 runtime.tests.test_analytics_retention -v`

Expected: tests PASS; analytics version remains 3 and existing summary/projection key assertions remain unchanged.

- [ ] **Step 9: Commit Task 5**

```bash
git add runtime/analytics.py runtime/tests/test_analytics_v3.py runtime/tests/test_analytics_retention.py
git commit -m "fix: paginate targeted YouTube Analytics reports [ANALYTICS-006 IMPROVEMENT-002]"
```

### Task 6: Upgrade and Pin Checkout v7.0.1

**Files:**
- Modify: `youtube-workflow/.github/workflows/backgrounds.yml`
- Modify: `youtube-workflow/.github/workflows/context.yml`
- Modify: `youtube-workflow/.github/workflows/dispatch.yml`
- Modify: `youtube-workflow/.github/workflows/finalize-draft.yml`
- Modify: `youtube-workflow/.github/workflows/rerender.yml`
- Modify: `youtube-workflow/.github/workflows/result.yml`
- Create: `youtube-workflow/tests/test_workflows.py`

**Interfaces:**
- Produces: every checkout use pinned to `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`.

- [ ] **Step 1: Write failing workflow pin tests**

Assert exactly six checkout references exist, every external `uses:` reference contains a full 40-hex SHA, and every checkout reference equals the approved v7.0.1 SHA. Capture each workflow's current `fetch-depth`, `ref`, triggers, permissions, and concurrency blocks and assert the upgrade does not change them.

- [ ] **Step 2: Run workflow tests and confirm RED**

Run: `PYTHONPATH=. python -m unittest tests.test_workflows -v`

Expected: FAIL because all six references still use the approved v4.4.0 SHA.

- [ ] **Step 3: Replace only checkout SHA and version comments**

Make no other workflow changes.

- [ ] **Step 4: Verify workflow tests and YAML parsing**

Run: `PYTHONPATH=. python -m unittest tests.test_workflows -v`

If `actionlint` is available, also run: `actionlint .github/workflows/*.yml`

Expected: tests PASS and actionlint reports no errors.

- [ ] **Step 5: Commit Task 6**

```bash
git add .github/workflows tests/test_workflows.py
git commit -m "build: pin workflows to checkout v7.0.1 [WORKFLOW-004 IMPROVEMENT-004]"
```

### Task 7: Remove Stale Runtime Duration Constants

**Files:**
- Modify: `production-runtime/runtime/base/contract.py`
- Modify: `production-runtime/runtime/resources/media.py`
- Modify: `production-runtime/runtime/transform/compose.py`
- Modify: `production-runtime/runtime/transform/verify.py`
- Create: `production-runtime/runtime/tests/test_runtime_contract.py`

**Interfaces:**
- Produces: shared `BLACKDETECT_MAX_ALLOWED_SECONDS = 0.75` and `DEFAULT_TEST_RENDER_MAX_SECONDS = 5.0` in `base.contract`; required keyword-only `segment_duration_seconds` in `resources.media.download()`.

- [ ] **Step 1: Write failing contract/static tests**

Assert the two old production target constants are absent; compose and verify import the shared thresholds; omitting `segment_duration_seconds` raises `TypeError`; and the production caller supplies it explicitly.

- [ ] **Step 2: Run contract tests and confirm RED**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_runtime_contract -v`

Expected: FAIL because stale and duplicated values remain and the download argument still has a default.

- [ ] **Step 3: Centralize technical constants and require duration**

Remove only the unused 120/175 target constants. Move the black-detection and test-render defaults to `base.contract`, import them in compose/verify, and make `segment_duration_seconds` keyword-only without a default. Retain `PRODUCTION_MAX_SECONDS=178.0`, encode safety, and background bounds exactly.

- [ ] **Step 4: Add boundary assertions**

Test black detection `<0.75` passes and `>=0.75` fails, default test render remains 5 seconds, compose retains its 1–15-second test range, verifier retains its `+0.55` tolerance, and the 178-second production ceiling is unchanged.

- [ ] **Step 5: Verify Task 7 GREEN**

Run: `PYTHONPATH=runtime python -m unittest runtime.tests.test_runtime_contract -v`

Expected: all tests PASS.

- [ ] **Step 6: Commit Task 7**

```bash
git add runtime/base/contract.py runtime/resources/media.py runtime/transform/compose.py runtime/transform/verify.py runtime/tests/test_runtime_contract.py
git commit -m "refactor: remove stale runtime duration constants [IMPROVEMENT-008]"
```

### Task 8: Full Verification, Current-Main Integration, and Handoff

**Files:**
- Verify all files changed by Tasks 1–7.
- Do not modify `youtube-workflow/PLANNING.md`.
- Do not modify `youtube-analytics-data` directly.

**Interfaces:**
- Consumes: all prior task commits.
- Produces: verified commits on the current `main` branches and a lifecycle audit report for review, without production mutations.

- [ ] **Step 1: Re-read current remote heads and changed files**

Fetch both `main` branches. Confirm no conflicting changes landed after each task's base. Rebase or recreate commits without force-pushing if either branch advanced.

- [ ] **Step 2: Run the complete planner verification**

Run:

```bash
git diff --check
PYTHONPATH=. python -m unittest discover -s tests -v
python pipeline.py self-test
python pipeline.py audit-lifecycle > /tmp/wacky-lifecycle-audit.json
python -m json.tool /tmp/wacky-lifecycle-audit.json >/dev/null
git diff --exit-code -- PLANNING.md
```

Expected: all tests PASS, self-test passes, audit JSON validates, and `PLANNING.md` has no diff.

- [ ] **Step 3: Run the complete runtime verification**

Run:

```bash
git diff --check
PYTHONPATH=runtime python -m unittest discover -s runtime/tests -v
PYTHONPATH=runtime python runtime/self_test.py
PYTHONPATH=runtime python runtime/background_contract_test.py
PYTHONPATH=runtime python runtime/preflight_contract_test.py
```

Expected: all unit tests and contract suites PASS.

- [ ] **Step 4: Review item 8 without changing it**

Confirm `result.yml` still serializes reconciliation, scans all results missing from history, and retries from latest `main`. Record item 8 as resolved by existing behavior; do not add a coordinator or scheduled aggregator.

- [ ] **Step 5: Push logical commits without rewriting history**

Update current `main` only by fast-forward. Never use force push. Keep planner and runtime commits separate.

- [ ] **Step 6: Verify GitHub Actions**

Confirm planner unit/context checks and runtime Verify V2 pass for their exact commit SHAs. Do not dispatch Production. The next normal production run provides live evidence-V2 validation.

- [ ] **Step 7: Report results**

Provide commit SHAs, files changed, test counts, workflow run links, lifecycle classification counts, Reporting status behavior, and explicit confirmation that creative files and publishing strategy were untouched.
