# Automatic production recovery

Automatic recovery is a **private control-plane responsibility**. The private repository decides which immutable requests are incomplete; the public runtime continues to execute only opaque batches and remains stateless between runs.

## Authoritative state

Recovery decisions use `content/results/<content_id>.json` as the authoritative per-item success receipt. Batch workflow status is useful evidence, but it is not proof that an item needs another upload. A valid receipt always wins.

The public runtime's existing durable upload state remains the exactly-once fence:

- `content/recovery/<content_id>/intent.json` is created before YouTube insertion.
- `content/recovery/<content_id>/upload.json` records the exact video when insertion or marker reconciliation succeeds.
- once an intent exists, absence of an observable video is never permission to insert another copy.
- recovery first tries to restore/reconcile the existing upload and then verifies/finalizes the immutable receipt.

## Controller

`recovery/controller.py` scans immutable requests and classifies each eligible item as one of:

- `completed` — a valid immutable verified receipt exists.
- `active` — the most recent execution is still inside the recovery grace period.
- `pending` — a retryable failure exists but its retry backoff has not elapsed.
- `recoverable` — the item is stale or has retryable/durable evidence that should be reconciled.
- `terminal` — automatic retry is unsafe or the bounded attempt limit is exhausted.

Automatic recovery is intentionally limited to the repository's **current request schema** (`SCHEMA_VERSION`). Historical request schemas remain `manual_only` even when the runtime still supports them for operator recovery. This prevents old acceptance/migration artifacts from being resurrected by a newly enabled watchdog while preserving manual recovery for those immutable requests.

The controller never renders, uploads, or edits an immutable request. When recovery is safe it writes the same recovery-manifest contract already consumed by `production-runtime`.

## Triggers

`.github/workflows/automatic-recovery.yml` provides three control-loop paths:

1. **Retryable diagnostic push** — re-evaluates immediately when runtime diagnostics arrive in private state.
2. **Daily Production workflow failure** — re-evaluates the failed source commit immediately, catching private dispatch failures before the normal stale grace period.
3. **Two-hour reconciliation backstop** — catches lost dispatches, cancelled/disappeared runners, missing callbacks, and other failures that could not announce themselves.

A manual `workflow_dispatch` remains available. Its default mode is `plan`, which only prints the reconciliation decision. `execute` writes/dispatches recovery work.

## Default policy

The defaults are intentionally conservative and configurable by workflow environment variables:

- active/stale grace: **210 minutes**, slightly beyond the public runtime's 180-minute job timeout;
- fresh-generation schedule buffer: **10 minutes**, matching the public scheduled-slot guard;
- maximum automatic attempts: **3**;
- retry backoff after retryable diagnostics: **0, 120, 240 minutes**.

A first retryable diagnostic may recover immediately. Later automatic attempts back off. Silent dispatch/runner loss is reconsidered only after the active grace period.

If retryability is missing/unknown, automatic recovery fails closed rather than guessing.

## Deterministic recovery identity

Automatic recovery batch IDs are deterministic over the sorted tuple:

`(content_id, original source_commit_sha, automatic_attempt)`

Repeated watchdog executions therefore resolve to the same logical batch for the same attempt. GitHub workflow concurrency suppresses overlapping private controllers, while the durable upload intent remains the authoritative protection against duplicate YouTube insertion.

## Publish-window safety

If the immutable scheduled slot is past or inside the 10-minute generation buffer **and no durable intent/upload evidence exists**, automatic fresh generation stops and records terminal state.

If durable intent/upload evidence already exists, recovery is still allowed after the scheduled time because the operation may only need to rediscover, verify, and finalize the existing upload. It must not create a replacement upload.

## Terminal state

Automatic terminal decisions are append-only under:

`content/recovery/terminal/<content_id>.json`

They record the reason, attempt count, latest batch/error evidence, publish time, and policy. Manual recovery remains available for operator reconciliation. A later valid receipt still takes precedence over a terminal marker.

## Cost and scope

The scheduled controller performs only private-state reconciliation; it does not render media or call YouTube. Expensive public runtime work is dispatched only for unresolved individual items, capped at 24 per recovery batch. A 23/24 successful daily batch therefore recovers only the one unresolved content ID.
