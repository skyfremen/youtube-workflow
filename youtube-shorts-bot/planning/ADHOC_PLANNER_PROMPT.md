# Wacky Dramas — Ad-hoc Single Planner (schema v5 + ChatGPT editorial selection overlay)

This is the canonical Ad-hoc single-Short planner entry point.

Read `docs/ADHOC_PLANNER_V4_BASE.md` in full first, then the current `planning/DAILY_PLANNER_PROMPT.md`. Preserve all existing Ad-hoc identity, exactly-one-Short, immediate-public publication, metadata, recovery, idempotency, safety and architecture rules except where this overlay explicitly supersedes winner-selection and schema-v4/background-treatment behavior.

Repository code is authoritative for deterministic calculations and validation. Inspect the current `planning/planning_runner.py`, `planning/planning_engine.py`, `validation/validate_content.py`, `common/runtime_contract.py`, `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, registry and workflows before authoring the request.

## Ad-hoc editorial ownership — authoritative override

**ChatGPT / Work owns the final editorial choice of the one Ad-hoc winner.**

`planning_engine.py` and `planning_runner.py` support ChatGPT with deterministic hard rejection, scoring, analytics normalization, duplicate/near-duplicate checks, eligibility, diversity-policy validation and request validation. They do **not** choose the authoritative Ad-hoc winner for new planning runs.

The statement in the older base prompt that the first item from `result.selected` is the authoritative winner is superseded by this overlay.

The legacy `planning.final-select` / `final-select` operation remains available only for historical recovery compatibility. Do not use it to pick a new Ad-hoc winner.

The canonical new Ad-hoc flow is:

```text
ChatGPT generates candidates
  -> planning.raw-filter
  -> ChatGPT develops qualified semifinalists
  -> planning.candidate-evaluation
  -> deterministic scores/checks/ranking evidence returned
  -> ChatGPT chooses exactly 1 eligible winner
  -> planning.validate-selection with selection_limit=1
  -> deterministic validation of ChatGPT's chosen ID
  -> ChatGPT writes the complete story
  -> background selection/audit/treatment
  -> request.validate
  -> commit exactly one immutable Ad-hoc request
  -> private Ad-hoc dispatcher
  -> public single runtime
  -> YouTube immediately Public
```

ChatGPT may choose a lower-ranked eligible candidate over a higher-ranked one when its semantic/editorial judgment supports that choice. A deterministic score or rank is evidence, not authority. ChatGPT may never choose a candidate that failed hard filtering or candidate evaluation.

If `planning.validate-selection` rejects the chosen ID, ChatGPT must choose again or stop. The deterministic validator must never silently substitute another winner.

## Repository-side execution bridge

When ChatGPT / Work has a real local checkout, execute the canonical Python entry points directly.

When the connected environment can read/write GitHub state but cannot execute the private checkout locally, use `.github/workflows/planner-execution.yml` plus `planning/execution_bridge.py`. Do not reproduce deterministic arithmetic manually.

Create a JSON envelope under:

`content/planner-execution/inputs/<execution_id>.json`

with schema version 1 and a supported operation.

For new Ad-hoc planning, the planning operations are:

- `planning.raw-filter`
- `planning.candidate-evaluation`
- `planning.validate-selection`

`planning.final-select` is legacy recovery compatibility only.

Other supported deterministic operations remain:

- `background.select`
- `background.audit`
- `background.treatment`
- `request.validate`

Consume the actual committed result under `content/planner-execution/results/<execution_id>.json` before continuing. Never infer success from workflow start alone and never hand-author substitute results.

Bridge input/result commits are execution evidence, not production requests and must not use `[daily production]` or `[adhoc production]` markers.

## Selection validation contract

For the final Ad-hoc editorial decision, call `planning.validate-selection` with:

- `evaluated_candidates`: the exact candidate objects returned by `planning.candidate-evaluation`;
- `selected_candidate_ids`: an array containing exactly the one ID chosen by ChatGPT;
- `selection_limit`: `1`;
- `plan_date`: the current Singapore Ad-hoc run date.

Only if validation succeeds may the chosen candidate proceed.

## Preserved Ad-hoc production contract

This path creates exactly one additional Short and uses `.github/workflows/adhoc-production.yml`, which dispatches public `single.yml` only. It must never consume or alter Daily's 24 scheduled slots.

The immutable publication object remains:

```json
{
  "mode": "immediate",
  "timezone": "Asia/Singapore",
  "publish_at": null
}
```

The upload body must resolve to `privacyStatus: public` with no future `publishAt`.

## Schema-v5 and visual allocation

New Ad-hoc requests use schema v5. Select distinct primary/backup logical backgrounds through the canonical retention-first selector, run the mechanical audit, then run the canonical private treatment allocator.

Freeze:

- `background_primary_id`
- `background_backup_id`
- `background_primary_treatment`
- `background_backup_treatment`

Do not hand-author different segment/speed values after the allocator returns. Existing private verified receipts remain the persistent anti-repetition history.

## Request validation and commit

After ChatGPT has written the final complete story and metadata for its chosen winner, run `request.validate` through the bridge or the direct repository implementation. Validate schema, content identity, deterministic planning evidence, backgrounds/treatments, runtime contract and exact immediate-public upload body.

Then commit exactly one new immutable Ad-hoc request using:

`[adhoc production] YYYY-MM-DD`

The private `.github/workflows/adhoc-request-dispatch.yml` may automatically dispatch the existing private `.github/workflows/adhoc-production.yml`. It does not bypass the private production/recovery authority and does not dispatch the public repo directly.

## Fail closed

Fail closed if raw filtering, candidate evaluation, ChatGPT selection validation, background selection/audit/treatment, request validation, contract compatibility or exact payload validation fails.

Failing closed must never mean “let deterministic code choose a replacement winner.” ChatGPT must revise its selection or stop.
