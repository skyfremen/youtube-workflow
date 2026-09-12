# Wacky Dramas YouTube Workflow

This private repository is the canonical **Wacky Dramas** source of truth. It owns planning rules, immutable ranked planning pools, promoted immutable requests, recovery/result state, media-registry maintenance, analytics processing, and private orchestration. Stateless production execution and the runtime-image build live in the separate public `production-runtime` repository.

## Canonical architecture

Private modules under `youtube-shorts-bot/` are limited to planning, analytics, state validation, media-registry maintenance, ranked-pool promotion, and the small shared request/upload contract needed to create and validate immutable production requests. Rendering, TTS, alignment, upload orchestration, publication verification, receipt finalization, runtime dependencies, and container-image construction execute only from public runtime code.

The normal production path is ranked-pool driven and append-only:

1. **ChatGPT / Work** reads the current repository rules, analytics, history and verified background registry, performs the creative/editorial planning, chooses/audits logical backgrounds, authors frozen treatments, and freezes the candidate rank order.
2. Daily planning commits one immutable **36-candidate** pool; Ad-hoc planning commits one immutable **5-candidate** pool. These are planning candidates, not production requests.
3. `daily-production.yml` / `adhoc-production.yml` perform global fail-first checks and mechanically validate candidates in the exact frozen AI rank order. They do not re-rank, repair, creatively substitute, or choose backgrounds/treatments.
4. Daily promotes the first **24 valid** candidates and materializes one canonical planning audit plus exactly 24 immutable schema-v5 production requests. Ad-hoc promotes the **first valid** candidate and materializes exactly one immutable schema-v5 immediate-public request.
5. The promoted request(s) are validated again before the private workflow sends one opaque `batch_id`, exact `source_sha`, compatibility fingerprint and dispatch correlation to the public runtime.
6. The public runtime fetches only the allowed private files at that exact source revision and validates them before expensive work.
7. Physical background rendition resolution, normalization, Kokoro narration, Wav2Vec2 alignment, captions, rendering at **1080×1920 / 30 fps**, upload and publication verification execute publicly and statelessly.
8. Upload recovery is checked before insertion. A durable upload intent is an irreversible retry fence.
9. Scheduled Daily requests upload private with the immutable YouTube `publishAt`; Ad-hoc requests upload immediately Public with no future `publishAt`.
10. The public runtime writes verified evidence/state back only to this private repository; private analytics processing consumes stored observations and receipts.

There is no `planner-execution.yml` bridge. ChatGPT owns the planning-time background audit/treatment decisions directly; private code independently validates the hard contract before dispatch.

Canonical durable paths include:

- `youtube-shorts-bot/content/planning-pools/daily/YYYY-MM-DD.json` — immutable 36-candidate Daily ranked planning pool.
- `youtube-shorts-bot/content/planning-pools/adhoc/ap-<stable-id>.json` — immutable 5-candidate Ad-hoc ranked planning pool.
- `youtube-shorts-bot/content/planning/YYYY-MM-DD.json` — immutable canonical Daily production audit created by promotion.
- `youtube-shorts-bot/content/requests/<content_id>.json` — immutable promoted production request.
- `youtube-shorts-bot/content/recovery/<content_id>/intent.json` — create-only upload intent.
- `youtube-shorts-bot/content/recovery/<content_id>/upload.json` — create-only durable upload evidence.
- `youtube-shorts-bot/content/results/<content_id>.json` — immutable verified success receipt.
- `youtube-shorts-bot/content/background-sourcing/YYYY-MM-DD.json` — optional immutable sourcing manifest when applicable.

Never edit or delete an existing JSON in the immutable planning-pool/planning/request/recovery/result paths during ordinary operation.

## Planning ownership

ChatGPT / Work owns creative and semantic decisions for new planning runs, including:

- story candidate generation, hard editorial rejection and near-duplicate reasoning;
- scoring/analytics interpretation, diversity reasoning and final rank order;
- complete scripts, titles, metadata, voice choices and punchline semantics;
- exact primary/backup logical background choice;
- planning-time background eligibility/audit reasoning and emergency-default decision;
- segment start/duration and playback-rate treatment values.

Private deterministic code is a fail-closed **validator and promotion gate**, not the creative planner. It enforces hard request/schema/background/treatment/publication invariants and skips invalid candidates according to the already-frozen ChatGPT rank.

For normal Daily, the contract is:

```text
ChatGPT: 36 complete ranked candidates
        ↓
daily-production.yml: first 24 valid
        ↓
exactly 24 immutable production requests
        ↓
public run.yml
```

For Ad-hoc:

```text
ChatGPT: 5 complete ranked candidates
        ↓
adhoc-production.yml: first valid
        ↓
exactly 1 immutable production request
        ↓
public single.yml
```

## Active private workflows

The supported private workflow set is deliberately small:

| Workflow | Purpose |
| --- | --- |
| `daily-production.yml` | Watches immutable Daily ranked pools, performs fail-first validation/promotion (36 → first 24 valid), materializes canonical production state, validates it again, then performs one opaque public `run.yml` dispatch. Also supports manual recovery by existing content IDs. |
| `adhoc-production.yml` | Watches immutable Ad-hoc ranked pools, validates/promotes the first valid candidate (5 → 1), materializes and revalidates one immediate-public request, then dispatches public `single.yml`. Also supports manual execution of an existing immutable content ID. |
| `analytics-collection.yml` | Processes/enriches raw observations written by the public runtime and updates the private learning snapshot/model. |
| `automatic-recovery.yml` | Reconciles no-start, failed, stale or partially incomplete promoted production and dispatches safe recovery work without replanning. |
| `background-management.yml` | Maintains official Pexels rendition metadata in the verified private background registry. |
| `dry-run.yml` | Private planning, ranked-pool, analytics, state-integrity, media-registry, architecture-boundary, contract-parity and linked public-runtime validation. |

The public `production-runtime` repository owns `base.yml`, `dry-run.yml`, `observe.yml`, `run.yml`, and `single.yml`.

## Publication and recovery invariants

- One promoted story maps to one immutable `content_id`.
- Ranked planning pools themselves are also protected append-only state.
- The current channel identity is **Wacky Dramas / @WACKYDRAMAS** and production ownership is pinned to the expected YouTube channel ID in code.
- **Schema v5** is the current production request format; schema v4 remains accepted for existing immutable recovery compatibility.
- Scheduled Daily uploads enter YouTube as private and carry the exact immutable `publishAt`.
- Ad-hoc uploads use immediate mode, `privacyStatus: public`, and no future `publishAt`.
- The deterministic recovery marker is stored in non-viewer-facing YouTube tags, not in the description.
- If a durable intent exists, a missing/temporarily unobservable video is never permission to upload again.
- Result receipts are created only after exact YouTube state, request identity, render, background/treatment, and provenance verification.
- Recovery operates on already-promoted immutable requests. It does not revisit or re-rank unused planning-pool reserves after production begins.

See `youtube-shorts-bot/docs/RECOVERY.md` for operator recovery details and `youtube-shorts-bot/docs/SYSTEM_OVERVIEW.md` for the planning/analytics design.

## Development and verification

The private validation baseline is encoded in `.github/workflows/dry-run.yml`. It compiles private Python, runs planning/state/contract/ranked-pool tests, validates the media registry, exercises planning acceptance, verifies private/public contract parity, checks the private execution boundary, and dispatches/verifies the linked public runtime Dry Run.

A production upload is **not** required to validate repository cleanup or ordinary code changes. Do not use public YouTube publishing as a cleanup test.

## Repository scope

Retired Wacky Insights planner/queue/series/music/publishing architecture, the former `youtube-story-bot` prototype, the former private runtime-image build, the retired `planner-execution.yml` bridge, and retired duplicate Ad-hoc routing workflows are not part of the supported tree. Do not restore them. Historical or experimental branches with unique unmerged work must be reviewed before deletion rather than treated as disposable solely because of age or naming.
