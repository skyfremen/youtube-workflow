# Wacky Dramas YouTube Workflow

This private repository is the canonical **Wacky Dramas** source of truth. It owns planning rules, immutable ranked planning pools, promoted immutable requests, recovery/result state, media-registry maintenance, analytics processing, and private orchestration. Stateless production execution and the runtime-image build live in the separate public `production-runtime` repository.

## Canonical architecture

Private modules under `youtube-shorts-bot/` are limited to planning, analytics, state validation, media-registry maintenance, ranked-pool promotion, and the small shared request/upload contract needed to create and validate immutable production requests. Rendering, TTS, alignment, upload orchestration, publication verification, receipt finalization, runtime dependencies, and container-image construction execute only from public runtime code.

The normal production path is ranked-pool driven and append-only:

1. **ChatGPT / Work** reads current repository rules, analytics, history and the verified background registry, performs creative/editorial planning, chooses/audits logical backgrounds, authors frozen treatments, and freezes candidate rank order.
2. Daily planning commits an immutable **36-candidate attempt pool**; Ad-hoc planning commits an immutable **5-candidate** pool. These are planning candidates, not production requests.
3. `daily-production.yml` / `adhoc-production.yml` perform a private promotion preflight and mechanically validate candidates in the frozen AI rank order. They do not re-rank, repair, creatively substitute, or choose backgrounds/treatments.
4. Daily promotes the first required valid candidates (24 for normal next-day) and locally materializes one canonical planning audit plus immutable schema-v5 requests. Ad-hoc locally materializes the first valid immediate-public request.
5. Promotion state is committed **locally**, rebased onto latest `main`, and fully revalidated before it is pushed. A concurrent change after validation makes the push fail non-fast-forward rather than publishing unvalidated immutable state.
6. Scheduled Ad-hoc uniqueness is repository-enforced after rebase: only one canonical scheduled 01:00 Ad-hoc request may exist per Singapore date. Manual/on-demand pools use a separate mode.
7. The validated request(s) then produce one opaque `batch_id`, exact `source_sha`, compatibility fingerprint and dispatch correlation for the public runtime.
8. The public runtime fetches only allowed private files at that exact revision and validates them before expensive work.
9. Physical background rendition resolution, normalization, Kokoro narration, Wav2Vec2 alignment, captions, rendering at **1080×1920 / 30 fps**, upload and publication verification execute publicly and statelessly.
10. Upload recovery is checked before insertion. A durable upload intent is an irreversible retry fence.
11. Scheduled Daily requests upload private with immutable YouTube `publishAt`; Ad-hoc requests upload immediately Public with no future `publishAt`.
12. Public execution writes verified evidence/state back only to this private repository; private analytics consumes stored observations and receipts.

There is no `planner-execution.yml` bridge. ChatGPT owns planning-time background audit/treatment decisions directly; private code independently validates the hard contract before dispatch.

## Durable planning and production paths

- `youtube-shorts-bot/content/planning-pools/daily/YYYY-MM-DD/dp-<attempt-id>.json` — immutable 36-candidate Daily planning attempt. Failed attempts remain append-only; a corrected attempt uses a new ID while no canonical plan exists.
- `youtube-shorts-bot/content/planning-pools/adhoc/ap-<stable-id>.json` — immutable 5-candidate Ad-hoc planning attempt with explicit `scheduled_daily` or `manual_on_demand` mode and `singapore_date`.
- `youtube-shorts-bot/content/planning/YYYY-MM-DD.json` — immutable canonical Daily production audit created only after successful promotion.
- `youtube-shorts-bot/content/requests/<content_id>.json` — immutable promoted production request.
- `youtube-shorts-bot/content/recovery/<content_id>/intent.json` — create-only upload intent.
- `youtube-shorts-bot/content/recovery/<content_id>/upload.json` — create-only durable upload evidence.
- `youtube-shorts-bot/content/results/<content_id>.json` — immutable verified success receipt.
- `youtube-shorts-bot/content/background-sourcing/YYYY-MM-DD.json` — optional immutable reviewed sourcing manifest when applicable.

Never edit or delete existing JSON in append-only planning-pool/planning/request/recovery/result paths during ordinary operation.

## Planning ownership

ChatGPT / Work owns creative and semantic decisions for new planning runs, including story candidate generation, hard editorial rejection/near-duplicate reasoning, scoring/analytics interpretation, diversity reasoning and final rank, complete scripts/titles/metadata, voice/punchline semantics, exact primary/backup logical backgrounds, audit/fallback reasoning, and segment/playback treatments.

Private deterministic code is a fail-closed **validator and promotion gate**, not the creative planner. It enforces hard schema/background/treatment/publication/idempotency invariants and skips invalid candidates only according to frozen ChatGPT rank.

For normal Daily:

```text
ChatGPT: 36 complete ranked candidates
        ↓
immutable Daily attempt pool
        ↓
daily-production.yml: first 24 valid
        ↓
local canonical commit → rebase → final validation → push
        ↓
exactly 24 immutable production requests
        ↓
public run.yml
```

For Ad-hoc:

```text
ChatGPT: 5 complete ranked candidates
        ↓
immutable Ad-hoc pool
        ↓
adhoc-production.yml: first valid
        ↓
local request commit → rebase → final validation/idempotency → push
        ↓
exactly 1 immutable production request
        ↓
public single.yml
```

## Active private workflows

| Workflow | Purpose |
| --- | --- |
| `daily-production.yml` | Watches Daily ranked-pool attempts, performs private validation/promotion (36 → first target valid), materializes locally, rebases and validates before push, then performs one opaque public `run.yml` dispatch. Also supports manual recovery by existing content IDs. |
| `adhoc-production.yml` | Watches Ad-hoc ranked pools, validates/promotes first valid (5 → 1), rebases, revalidates schema/registry/immediate-public and scheduled-date uniqueness before push, then dispatches public `single.yml`. Also supports manual execution of an existing content ID. |
| `analytics-collection.yml` | Processes/enriches raw observations written by the public runtime and updates the private learning snapshot/model. |
| `automatic-recovery.yml` | Reconciles no-start, failed, stale or partially incomplete promoted production and dispatches safe recovery work without replanning. |
| `background-management.yml` | Maintains official Pexels rendition metadata in the verified private background registry. |
| `dry-run.yml` | Private planning, ranked-pool, analytics, state-integrity, media-registry, architecture-boundary, contract-parity and linked public-runtime validation. |

The public `production-runtime` repository owns `base.yml`, `dry-run.yml`, `observe.yml`, `run.yml`, and `single.yml`.

## Publication and recovery invariants

- One promoted story maps to one immutable `content_id`.
- Ranked pool attempts are append-only. A failed Daily attempt may be replaced only by a **new immutable attempt** while no canonical plan exists.
- Only one canonical Daily plan may exist for a plan date.
- Only one canonical `scheduled_daily` Ad-hoc request may exist for a Singapore date; `manual_on_demand` is explicitly separate.
- Current channel identity is **Wacky Dramas / @WACKYDRAMAS**.
- **Schema v5** is current production format; schema v4 remains accepted only for existing immutable recovery compatibility.
- Scheduled Daily candidate publication enters the pool as the exact template `{mode: scheduled, timezone: Asia/Singapore, publish_at: null}`. Promotion may set only `publish_at`; it does not silently repair publication mode/timezone.
- Same-day catch-up slots are checked by ChatGPT before commit and rechecked mechanically at promotion so slots remain at least 30 minutes in the future.
- Treatment numeric values must be finite. Unknown/untrusted source duration permits only full-source treatment (`start=0`, `duration=null`).
- Scheduled Daily uploads enter YouTube as private and carry exact immutable `publishAt`.
- Ad-hoc uploads use immediate mode, `privacyStatus: public`, and no future `publishAt`.
- The deterministic recovery marker is stored in non-viewer-facing YouTube tags, not the description.
- If a durable intent exists, a missing/temporarily unobservable video is never permission to upload again.
- Result receipts are created only after exact YouTube state, request identity, render, background/treatment and provenance verification.
- Recovery operates on already-promoted immutable requests. It never re-ranks unused reserve candidates after production begins.

See `youtube-shorts-bot/docs/RECOVERY.md` for operator recovery and `youtube-shorts-bot/docs/SYSTEM_OVERVIEW.md` for the complete planning/analytics design.

## Development and verification

The private validation baseline is encoded in `.github/workflows/dry-run.yml`. It compiles private Python, runs planning/state/contract/ranked-pool tests, validates the media registry, exercises planning acceptance, verifies private/public contract parity, checks private execution boundaries, and dispatches/verifies the linked public runtime Dry Run.

A production upload is **not** required for repository cleanup or ordinary code validation.

## Repository scope

Retired Wacky Insights planner/queue/series/music/publishing architecture, the former `youtube-story-bot` prototype, private runtime-image build, `planner-execution.yml` bridge, duplicate Ad-hoc routing workflows, and V4 planner base prompts are not part of the supported tree. Do not restore them.
