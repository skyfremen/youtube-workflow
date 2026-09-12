# Wacky Dramas — Ad-hoc Single Planner (schema v5 overlay)

This is the canonical Ad-hoc single-Short planner entry point.

Read `docs/ADHOC_PLANNER_V4_BASE.md` **in full** first, then read the current `planning/DAILY_PLANNER_PROMPT.md`. Preserve all existing Ad-hoc identity, exactly-one-Short, immediate-public publication, deterministic planning, metadata, recovery, idempotency, safety and architecture rules except where this overlay supersedes schema-v4/background-treatment statements.

Repository code is authoritative. Inspect the current `validation/validate_content.py`, `common/runtime_contract.py`, `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, registry and workflows before authoring the request.

## Preserved Ad-hoc execution contract

This path creates exactly one additional Short and must use `.github/workflows/adhoc-production.yml`, which dispatches the public runtime `single.yml` path only. It must never consume or alter Daily's 24 scheduled slots. The content commit identity remains `[adhoc production] YYYY-MM-DD` according to the existing idempotency rules.

The immutable publication object remains immediate-public:

```json
{
  "mode": "immediate",
  "timezone": "Asia/Singapore",
  "publish_at": null
}
```

The public upload contract therefore resolves to `privacyStatus: public` with no future `publishAt`.

## Repository-side execution bridge

When ChatGPT / Work has a real local checkout of this private repository, execute the canonical Python entry points directly as documented below.

When the connected environment can read/write GitHub state but cannot execute the checked-out private repository locally, **do not fail merely because local process execution is unavailable and do not reproduce deterministic arithmetic manually**. Use the private repository-side bridge instead.

The bridge is `.github/workflows/planner-execution.yml` plus `planning/execution_bridge.py`. It executes from an actual checkout of current `main`, preserving the same fail-closed deterministic implementation and source-SHA provenance.

For each required repository-side operation:

1. Create exactly one new JSON envelope under:
   `content/planner-execution/inputs/<execution_id>.json`
2. `execution_id` must match `pe-[A-Za-z0-9-]{8,96}` and equal the filename stem.
3. The envelope is:

```json
{
  "schema_version": 1,
  "execution_id": "pe-...",
  "operation": "planning.raw-filter",
  "payload": {}
}
```

Supported canonical operations are:

- `planning.raw-filter` — payload is the exact `planning_runner.py` raw-filter input.
- `planning.final-select` — payload is the exact `planning_runner.py` final-select input.
- `background.select` — payload contains `requirements` and optional `planned_asset_ids` / `planned_categories`; this executes the canonical retention-first private selector against the current registry and successful receipts.
- `background.audit` — payload contains `primary_id`, `backup_id`, and optional `requirements`; this executes the canonical mechanical safety audit for the selected pair.
- `background.treatment` — payload contains `primary_id`, `backup_id`, and optional `planned_treatments`.
- `request.validate` — payload contains the complete proposed immutable `request`; this runs schema validation, canonical runtime-contract fingerprinting and exact `build_upload_body(..., require_future=False)` validation.

The workflow writes the result to:
`content/planner-execution/results/<execution_id>.json`.

Consume the **actual committed result** before continuing. Never infer success from workflow start alone. Never hand-author a substitute result if the workflow fails or the result file is absent.

Bridge input/result commits are execution evidence, not production requests, Daily plans, background-sourcing manifests or upload state. They must not use `[daily production]` or `[adhoc production]` commit markers.

## Schema-v5 override

New Ad-hoc requests use **schema v5**, not schema v4.

After selecting distinct primary/backup logical backgrounds through the same retention-first policy used by Daily, run the same private canonical treatment allocator:

```bash
PYTHONPATH=youtube-shorts-bot python youtube-shorts-bot/media/background_treatment.py \
  --primary-id <PRIMARY_ID> \
  --backup-id <BACKUP_ID>
```

When local checkout execution is unavailable, use the repository-side `background.select`, `background.audit`, and `background.treatment` operations above and consume their actual committed results.

Consume the allocator's actual returned values and freeze these four visual fields:

- `background_primary_id`
- `background_backup_id`
- `background_primary_treatment`
- `background_backup_treatment`

Do not hand-author a different segment or playback rate after running the allocator.

## Persistent history

Ad-hoc uses the same private immutable success history as Daily. Current immediate-public verified receipts count toward future asset, category, segment and playback anti-repetition.

There is no 24-item same-day scratch list for a single Ad-hoc request, but existing private receipts must still be read. Do not create public mutable state to remember Ad-hoc usage.

If the selected long asset has alternative temporal ranges, the allocator should avoid recently used ranges according to current code. Older/short/unknown-duration assets remain backward compatible through the allocator's safe full-source behavior.

Playback treatment remains category/asset aware and globally bounded. A different speed alone must never be treated as sufficient uniqueness when the same temporal content is otherwise repeated.

## Execution boundary

The private Ad-hoc planner freezes logical IDs and treatments only. The public runtime still owns physical rendition selection, local cache lookup, download, probe, normalization, FFmpeg treatment, rendering, upload and exact verification.

The frozen treatment is applied only after the physical source has been normalized to the production-sized job-local input, so Ad-hoc does not defeat smallest-sufficient-after-crop selection or normalized-cache reuse.

Immediate-public semantics remain unchanged: exactly one Short, `publication.mode = "immediate"`, no future `publishAt`, and no interaction with Daily's 24 hourly slots.

## Commit and automatic private dispatch

After exact request validation succeeds, commit exactly one new immutable Ad-hoc request using:

`[adhoc production] YYYY-MM-DD`

The private `.github/workflows/adhoc-request-dispatch.yml` watches only newly added Ad-hoc request files, verifies the immediate-public request identity, and dispatches the existing private `.github/workflows/adhoc-production.yml` with that `content_id`.

This helper exists only to bridge environments that can create the canonical request commit but cannot directly invoke GitHub `workflow_dispatch`. It does **not** bypass `adhoc-production.yml`, does not dispatch the public repository itself, and does not alter recovery/idempotency ownership.

If the environment can directly invoke the private `adhoc-production.yml`, that remains valid for explicit recovery of an existing immutable Ad-hoc content ID.

## Fail closed

Do not create a new v4 request. If planner execution, background selection/audit, treatment allocation, schema-v5 validation, contract compatibility, exact payload validation or any required deterministic step fails, fail closed rather than substituting guessed values.

All rules in `docs/ADHOC_PLANNER_V4_BASE.md` remain in force unless explicitly superseded by this overlay.
