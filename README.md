# Wacky Dramas YouTube Workflow

This private repository is the canonical **Wacky Dramas** source of truth. It owns AI-planning policy, ranked candidate pools, immutable production requests, recovery/result state, media-registry maintenance, analytics processing, and lightweight private orchestration. The public `production-runtime` repository owns stateless heavy execution: media resolution, TTS, alignment, rendering, upload, verification, observation, and the runtime image.

## Canonical architecture

ChatGPT / Work is the creative planner. Private GitHub Actions are mechanical fail-closed gates.

### Daily

```text
ChatGPT
  -> exactly 36 complete ranked candidates
  -> one immutable candidate-pool commit
  -> daily-production.yml
       -> global compatibility/registry preflight
       -> strict validation of all 36
       -> first 24 valid by frozen AI rank for normal next-day
       -> materialize exactly 24 immutable schema-v5 requests + one final planning audit
       -> final validation
       -> opaque dispatch to public run.yml
  -> public stateless runtime
  -> YouTube
```

For same-day catch-up, the pool still contains 36 ranked candidates but the mechanical production target is the remaining safely future hourly slots. Production never lowers validation gates to fill a quota.

### Ad-hoc

```text
ChatGPT
  -> exactly 5 complete ranked candidates
  -> one immutable Ad-hoc candidate-pool commit
  -> adhoc-production.yml
       -> global compatibility/registry preflight
       -> strict validation of all 5
       -> first valid candidate by frozen AI rank
       -> materialize exactly one immutable schema-v5 request
       -> final validation
       -> one-item private execution state
       -> opaque dispatch to public single.yml
  -> immediate Public YouTube upload
```

There is no planner-execution workflow or repository-side creative selection bridge. AI owns story/background/treatment decisions; private code validates their hard production contract and promotes strictly by the already-frozen rank.

## Background and treatment ownership

ChatGPT reads the verified media registry, policy, private successful-receipt history, and current background/treatment logic as planning evidence. It freezes distinct primary/backup logical IDs and both segment/playback treatment objects before the candidate-pool commit.

Private `validation/validate_content.py` is the production safety gate. In addition to schema/publication checks, strict validation verifies registered background existence, active/verified/commercial-use state, license/source evidence, watermark/text safety, hard quality floor, production-suitable rendition, treatment bounds, and treatment fit within asset duration. It rejects invalid AI output; it does not creatively repair or substitute it.

The public runtime receives only final immutable requests and executes their frozen contract. Rendering remains 1080×1920 / 30 fps / H.264 High + AAC-LC with Kokoro narration, Wav2Vec2-aligned captions, active-word focus, and planner-authored semantic punchline emphasis.

## Durable private paths

- `youtube-shorts-bot/content/candidate-pools/daily/YYYY-MM-DD.json` — immutable 36-candidate Daily planning pool.
- `youtube-shorts-bot/content/candidate-pools/adhoc/ap-<id>.json` — immutable 5-candidate Ad-hoc planning pool.
- `youtube-shorts-bot/content/planning/YYYY-MM-DD.json` — mechanically promoted final Daily planning audit.
- `youtube-shorts-bot/content/requests/<content_id>.json` — immutable promoted production request.
- `youtube-shorts-bot/content/recovery/<content_id>/intent.json` — create-only upload intent.
- `youtube-shorts-bot/content/recovery/<content_id>/upload.json` — create-only durable upload evidence.
- `youtube-shorts-bot/content/recovery/batches/<batch_id>.json` — immutable recovery/single execution batch state.
- `youtube-shorts-bot/content/results/<content_id>.json` — immutable verified success receipt.
- `youtube-shorts-bot/content/background-sourcing/YYYY-MM-DD.json` — optional historical/compatible sourcing manifest.

Never edit or delete existing production JSON in these immutable paths during ordinary operation.

## Active private workflows

| Workflow | Purpose |
| --- | --- |
| `daily-production.yml` | Promotes a ranked Daily pool into the first valid target set, creates final immutable production state, then dispatches public `run.yml`; manual recovery remains supported. |
| `adhoc-production.yml` | Promotes a ranked five-candidate Ad-hoc pool into one valid immutable request and dispatches public `single.yml`; manual execution of an existing request remains supported. |
| `automatic-recovery.yml` | Reconciles failed/no-start/stale/partial production and safely redispatches unresolved work. |
| `analytics-collection.yml` | Processes/enriches raw public observations into the private analytics snapshot/model. |
| `background-management.yml` | Maintains verified Pexels rendition metadata in the private background registry. |
| `dry-run.yml` | Private planning/state/contract/topology regression gate and linked public Dry Run. |

The former `planner-execution.yml` and `adhoc-request-dispatch.yml` are retired and must not be restored.

The public `production-runtime` repository owns `base.yml`, `dry-run.yml`, `observe.yml`, `run.yml`, and `single.yml`.

## Publication and recovery invariants

- One promoted story maps to one immutable `content_id`.
- Wacky Dramas / `@WACKYDRAMAS` is the canonical channel identity.
- **Schema v5 is the current production request format. Schema v4 remains executable only for existing immutable recovery/migration state.**
- Normal Daily production materializes exactly 24 final requests with unique hourly `Asia/Singapore` publication slots.
- Ad-hoc production materializes exactly one final request with `mode=immediate` and `publish_at=null`.
- Public dispatch remains opaque: `batch_id`, exact `source_sha`, compatibility `contract_hash`, and `dispatch_id` only.
- The public runtime fetches the exact promoted immutable state; reserve candidates never cross the public boundary.
- Durable upload intent remains the duplicate-publication fence. Absence of a visible video is never permission to insert again once intent exists.
- Result receipts are written only after exact request/render/background/publication verification.

See `youtube-shorts-bot/docs/RECOVERY.md` for recovery details and `youtube-shorts-bot/docs/SYSTEM_OVERVIEW.md` for the full planning/analytics design.

## Development and verification

`.github/workflows/dry-run.yml` compiles private Python, runs planning/state/contract/topology tests, validates the media registry, exercises planning acceptance, checks private/public contract parity, confirms the private side has no TTS/render/upload side effects, and dispatches the linked public Dry Run.

A production upload is **not** required to validate ordinary code or architecture changes.

## Repository scope

Retired Wacky Insights planner/queue/series/music/publishing architecture, former private runtime/image-build copies, planner-execution bridge code, and obsolete dispatch-router workflows are not part of the supported tree. Do not restore them merely because older prompts or documentation mention them.
