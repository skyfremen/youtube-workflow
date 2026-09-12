# Wacky Dramas — Ad-hoc Single Planner (schema v5 + ChatGPT-direct planning)

This is the canonical Ad-hoc single-Short planner entry point.

Read `docs/ADHOC_PLANNER_V4_BASE.md` in full first, then the current `planning/DAILY_PLANNER_PROMPT.md`. Preserve all existing Ad-hoc identity, exactly-one-Short, immediate-public publication, metadata, recovery, idempotency, safety and architecture rules except where this overlay explicitly supersedes older deterministic-runner, winner-selection, and background-selection ownership behavior.

Repository code is authoritative for the rules. Inspect the current `planning/planning_engine.py`, `planning/planning_config.py`, `analytics/analytics_learning.py`, `validation/validate_content.py`, `common/runtime_contract.py`, `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, registry and workflows before authoring the request.

## Ad-hoc planning ownership — authoritative override

**ChatGPT / Work performs the complete candidate-planning decision path, chooses the one Ad-hoc winner, and chooses the exact primary/backup logical backgrounds.** ChatGPT / Work owns the final editorial choice and logical background asset choice.

For a new Ad-hoc run, ChatGPT itself must:

1. generate the candidate pool;
2. apply hard rejection and duplicate/near-duplicate rules;
3. develop the qualified candidates;
4. apply the current scoring formulas and analytics evidence;
5. compare candidates semantically/editorially;
6. choose exactly one eligible winner;
7. write the complete story and metadata;
8. inspect the current background registry, policy, licensing/suitability metadata, recency/history and choose exact distinct `background_primary_id` / `background_backup_id` values.

Do not call GitHub Actions to execute `planning.raw-filter`, `planning.candidate-evaluation`, `planning.validate-selection`, `final-select`, or `background.select` for a new Ad-hoc plan. `planning_engine.py`, background selector/policy code, and related files are rule/specification/evidence sources for ChatGPT and may remain executable for tests, regression checks, or legacy historical compatibility, but they do not plan or choose logical backgrounds on ChatGPT's behalf.

The canonical Ad-hoc flow is:

```text
ChatGPT reads current repo rules/config/analytics/history/background registry
  -> ChatGPT generates candidates
  -> ChatGPT performs hard filtering
  -> ChatGPT develops qualified candidates
  -> ChatGPT applies scoring/analytics/diversity rules
  -> ChatGPT chooses exactly 1 winner
  -> ChatGPT writes the complete story
  -> ChatGPT chooses exact primary + backup logical background IDs
  -> mechanical background audit of those exact IDs
  -> mechanical treatment allocation for those exact IDs
  -> request.validate / final schema validation
  -> commit exactly one immutable Ad-hoc request
  -> private Ad-hoc dispatcher
  -> public single runtime
  -> YouTube immediately Public
```

A score or ranking is evidence, not authority. Likewise, selector ranking is evidence, not authority. ChatGPT may choose a lower-ranked eligible candidate or different eligible background when its editorial judgment supports the choice, provided all hard rules are satisfied.

## Repository-side bridge boundary

`.github/workflows/planner-execution.yml` plus `planning/execution_bridge.py` may still be used for **mechanical non-editorial operations only** when the connected environment cannot execute them locally:

- `background.audit`
- `background.treatment`
- `request.validate`

The bridge must not expose or execute candidate filtering, candidate evaluation, selection validation, winner selection, or logical background selection for new planning runs.

Bridge input/result commits are mechanical execution evidence, not production requests, and must not use `[daily production]` or `[adhoc production]` markers.

## Preserved Ad-hoc production contract

This path creates exactly one additional Short and uses `.github/workflows/adhoc-production.yml`, which dispatches public `single.yml` only. It must never consume or alter Daily's scheduled slots.

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

New Ad-hoc requests use schema v5.

For the selected story:

1. ChatGPT inspects the current registry and background-selection rules, including licensing, production suitability, retention/topic fit, private successful-receipt recency/history, and primary/backup distinctness.
2. ChatGPT chooses the exact primary and backup logical asset IDs itself.
3. Run `background.audit` against those exact ChatGPT-chosen IDs. The audit may reject them but must never substitute other IDs.
4. If rejected, ChatGPT chooses a different eligible pair and reruns the audit, or fails closed.
5. After audit success, run the canonical private treatment allocator for the same IDs. Treatment allocation may choose the segment and playback rate only; it must not replace either logical asset.
6. Freeze:
   - `background_primary_id`
   - `background_backup_id`
   - `background_primary_treatment`
   - `background_backup_treatment`

Do not hand-author different segment/speed values after the allocator returns. Existing private verified receipts remain the persistent anti-repetition history.

## Request validation and commit

After ChatGPT has written the final complete story, metadata, and selected exact logical backgrounds, validate the final request through the repository's request-validation path. GitHub may reject an invalid story/background/request handoff, but it must not choose or substitute another candidate or logical background.

Then commit exactly one new immutable Ad-hoc request using:

`[adhoc production] YYYY-MM-DD`

The private `.github/workflows/adhoc-request-dispatch.yml` may automatically dispatch the existing private `.github/workflows/adhoc-production.yml`. It does not bypass the private production/recovery authority and does not dispatch the public repo directly.

## Fail closed

Fail closed if ChatGPT cannot confidently apply the current planning or background-selection rules, or if background audit, treatment allocation, request validation, contract compatibility, or exact payload validation fails.

Failing closed must never mean “let deterministic code choose a replacement winner/background.” ChatGPT remains the planner, editorial decision maker, and logical background chooser.
