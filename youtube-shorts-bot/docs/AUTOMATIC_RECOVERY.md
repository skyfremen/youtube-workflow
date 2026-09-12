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

`.github/workflows/automatic-recovery.yml` provides four control-loop paths:

1. **Retryable diagnostic push** — re-evaluates immediately when runtime diagnostics arrive in private state.
2. **Daily/Ad-hoc workflow completion failure** — re-evaluates after an unsuccessful private production workflow completes, catching dispatch/control-plane failures quickly.
3. **30-minute reconciliation backstop** — cron runs at minutes 17 and 47 each hour to catch lost dispatches, cancelled/disappeared runners, missing callbacks, stale executions, and other failures that could not announce themselves.
4. **Manual workflow dispatch** — defaults to `plan`, which only prints the reconciliation decision; `execute` writes/dispatches recovery work.

## Default policy

The defaults are intentionally conservative and configurable by workflow environment variables:

- dispatch accepted/prepared but no matching public `START` evidence: **25-minute no-start grace**;
- started/running execution liveness grace: **240 minutes**;
- fresh-generation schedule buffer: **10 minutes**, matching the public scheduled-slot guard;
- maximum automatic attempts: **3**;
- retry backoff after retryable diagnostics: **0, 120, 240 minutes**.

The two grace concepts are deliberately separate. A dispatch that never starts is eligible for same-batch redispatch after the short 25-minute grace. Once an exact `START` record exists, subsequent progress evidence refreshes liveness and the 240-minute started-execution grace prevents recovery from racing a legitimately slow public run. The 240-minute grace exceeds the current Daily public workflow's 20-minute prepare + 180-minute production + 20-minute aggregate job budgets.

A first retryable diagnostic may recover immediately. Later automatic attempts back off. If retryability is missing/unknown, automatic recovery fails closed rather than guessing.

## Dispatch and progress evidence

Private dispatch writes a create-only prepared intent before calling the public workflow. Public execution must validate that exact intent and write a matching `START` record containing the batch, dispatch, source, contract, runtime commit, workflow run and attempt identities.

The public runtime also writes append-only progress records at meaningful execution stages. Recovery uses the most recent exact execution/progress timestamp when deciding whether a started run is still healthy. A successful GitHub dispatch API response by itself is therefore not treated as proof that public code actually ran. On a GitHub partial rerun (attempt > 1) where prepare was not rerun, the progress layer may create the missing current-attempt START only from exactly one prior matching START plus the still-matching immutable dispatch intent; attempt 1 cannot use this repair path.

## Deterministic recovery identity

Automatic recovery batch IDs are deterministic over the sorted tuple:

`(content_id, original source_commit_sha, automatic_attempt)`

Repeated watchdog executions therefore resolve to the same logical batch for the same attempt. GitHub workflow concurrency suppresses overlapping private controllers, while the durable upload intent remains the authoritative protection against duplicate YouTube insertion.

No-start retry is a separate same-batch operation: it retains the exact original batch/source/contract identity and creates a new dispatch identity rather than manufacturing a replacement production request.

## Publish-window safety

If the immutable scheduled slot is past or inside the 10-minute generation buffer **and no durable intent/upload evidence exists**, automatic fresh generation stops and records terminal state.

If durable intent/upload evidence already exists, recovery is still allowed after the scheduled time because the operation may only need to rediscover, verify, and finalize the existing upload. It must not create a replacement upload.

## Terminal state

Automatic terminal decisions are append-only under:

`content/recovery/terminal/<content_id>.json`

They record the reason, attempt count, latest batch/error evidence, publish time, and policy. Manual recovery remains available for operator reconciliation. A later valid receipt still takes precedence over a terminal marker.

## Cost and scope

The scheduled controller performs only private-state reconciliation; it does not render media or call YouTube. Expensive public runtime work is dispatched only for unresolved individual items, capped at 24 per recovery batch. A 23/24 successful daily batch therefore recovers only the one unresolved content ID.
