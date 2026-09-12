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

## Schema-v5 override

New Ad-hoc requests use **schema v5**, not schema v4.

After selecting distinct primary/backup logical backgrounds through the same retention-first policy used by Daily, run the same private canonical treatment allocator:

```bash
PYTHONPATH=youtube-shorts-bot python youtube-shorts-bot/media/background_treatment.py \
  --primary-id <PRIMARY_ID> \
  --backup-id <BACKUP_ID>
```

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

## Fail closed

Do not create a new v4 request. If treatment allocation, schema-v5 validation, contract compatibility, exact payload validation or any required deterministic planner step fails, fail closed rather than substituting guessed values.

All rules in `docs/ADHOC_PLANNER_V4_BASE.md` remain in force unless explicitly superseded by this overlay.
