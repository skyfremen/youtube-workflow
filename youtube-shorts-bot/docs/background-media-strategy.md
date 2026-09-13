# Background media strategy

## Active library lifecycle

`media-library/backgrounds.json` is the **only background registry**. Pre-reset background definitions were **destructively removed**; they are not retained in a hidden fallback registry. The current registry stores reusable **atomic clips**, not Short-specific composites, and may validly contain `"assets": []` after a hard reset. Empty or insufficient inventory audits as `REPLENISH` rather than corruption.

Daily and Ad-hoc share one readiness/replenishment path:

```text
audit -> REPLENISH -> immutable schema-v2 discovery request
      -> Background Management/Pexels API filters duration + rendition eligibility
      -> Background Management reads exact Pexels preview media
      -> FFmpeg generates small representative JPEG contact sheets
      -> private GitHub artifact + immutable review-evidence index
      -> ChatGPT/Work downloads that exact artifact through the GitHub connection
      -> ChatGPT inspects the JPEG pixels and assigns approval + semantic metadata
      -> immutable review-decision state
      -> approved candidates -> immutable readiness manifest
      -> Background Management re-enriches/persists
      -> refresh main -> audit again
      -> PASS -> same original planner invocation continues
      -> still REPLENISH and attempt < 5 -> next targeted discovery attempt
```

Provider discovery is deliberately split from editorial review. `media.pexels_discovery` may use the GitHub-held `PEXELS_API_KEY` to fetch exact provider metadata and discard clips below the live atomic-duration minimum or without a production-suitable rendition. For review transport it records the smallest useful exact provider rendition, while production suitability remains independently required. Background Management may perform **transport-only** media work: read/download those exact URLs, derive JPEG contact sheets, upload a private artifact and persist an immutable artifact index. It must not set `verified_preview=true`, invent semantic tags/scores, approve/reject a source, or write reviewed assets directly to the registry. ChatGPT/Work remains the sole visual/editorial approval owner.

A discovery request is immutable under `content/background-sourcing/discovery-requests/`. Background Management writes the matching provider result under `content/background-sourcing/discovery-results/` and one or more immutable transport indexes under `content/background-sourcing/review-evidence/<request_id>-run-<run_id>.json`. Each index records the exact Background Management run and artifact identity, digest, evidence-manifest hash and provider IDs with contact sheets. Multiple run-scoped indexes allow safe evidence regeneration after artifact expiry without editing history.

### Schema-v2 replenishment request

New automatic replenishment attempts use discovery request schema v2. In addition to the existing plan date/request ID/candidate budget, each request freezes:

- `target_categories` containing only currently deficient categories;
- `exclude_provider_asset_ids`;
- one stable `replenishment_session_id`;
- `attempt` from 1 through 5.

The replenishment session ID is durable recovery state for the original Daily/Ad-hoc planner invocation. The same session ID is reused across retries and after recoverable interruption. Query order rotates by attempt so later attempts start with different canonical search vocabulary.

Legacy schema-v1 discovery requests remain readable for immutable history but must not be used for new automatic retries.

### Immutable review decisions

After actual visual review, ChatGPT/Work writes one immutable review-decision JSON under `content/background-sourcing/review-decisions/<request_id>.json`. Review-decision schema v1 contains:

- `replenishment_session_id`;
- `request_id`;
- `attempt`;
- per-provider `decision`;
- original `discovery_category`;
- `reviewed_category` when confidently classifiable;
- `category_match`;
- stable `reason_code`.

An approved candidate must visually match its discovery category. Search query/category metadata is provenance only and never sufficient to establish semantic category. A semantically mismatched clip is rejected for that attempt even if it might be useful elsewhere.

For schema-v2 discovery, `media.pexels_discovery` automatically reads immutable review-decision state for the same `replenishment_session_id` and excludes every provider asset already reviewed in that session. Request-side `exclude_provider_asset_ids` is still retained as explicit evidence and defense in depth, but recovery correctness no longer depends on ChatGPT reconstructing the exclusion list perfectly after interruption.

Readiness PASS requires the configured inventory/category minima and proof that two disjoint executable v7 sequences can actually be formed.

### Bounded continuation and terminal semantics

`REPLENISH` and individual candidate rejection are recoverable states. They are not final planner results.

After each reviewed/ingested attempt, re-resolve `main`, rerun readiness, and:

- on `PASS`, resume the same original Daily/Ad-hoc planner invocation immediately;
- on `REPLENISH` with `attempt < 5`, create the next targeted immutable attempt automatically;
- after attempt 5, fail closed with `E_MEDIA_REPLENISH_EXHAUSTED` and report exact remaining deficits, attempts and rejection diagnostics.

`DEFERRED_REPLENISHMENT` is reserved for a genuine bounded infrastructure wait expiration. It is not the correct response merely because a visual candidate was rejected.

Never reduce quality, duration, licensing, rendition, watermark/text, semantic-review, or caption-readability thresholds to force readiness.

## Preview-review evidence

`verified_preview=true` means ChatGPT/Work reviewed **actual visual evidence for the exact Pexels source** before proposing it. GitHub transport success alone is never approval.

The preferred transport is the **private Background Management review-evidence artifact**. For each new discovery result, Background Management runs `media.preview_review_materializer --contact-sheets-only` against exact Pexels preview URLs and creates compact JPEG contact sheets. It uploads lightweight review evidence, not source video, as `background-review-evidence-<request_id>-<run_id>` with a short retention window, then commits `content/background-sourcing/review-evidence/<request_id>-run-<run_id>.json` containing exact workflow-run/artifact identity and evidence hashes.

Planner review order:

1. Read the immutable discovery result and newest matching run-scoped review-evidence index whose artifact is still available.
2. Through the authorized GitHub connection, list artifacts for the indexed `workflow_run_id`, require the indexed artifact ID/name/digest to match, and download that exact ZIP. GitHub connector delivery into ChatGPT/Work local storage is the canonical binary transfer bridge.
3. Extract the ZIP locally. Verify `evidence-manifest.json` against the index SHA-256 and confirm provider IDs/source URLs correspond to the immutable discovery result.
4. Inspect the actual `*/contact-sheet.jpg` pixels (and exact `*/preview.jpg` when useful). ChatGPT/Work alone decides approval, semantic tags, motion/readability judgment and scores.
5. Persist the immutable review-decision document before continuing.
6. Reject candidate-specific missing/unsuitable evidence and continue through reserves. Never convert transport success directly into `verified_preview=true`.
7. If readiness is still short after reserves, continue with the next targeted attempt instead of ending the planner invocation.

The workflow excludes provider IDs that are already active+verified in the registry from repeated artifact generation; this is transport optimization only. Future discovery uses a smaller exact provider rendition for contact-sheet generation while independently requiring a production-quality rendition for eventual production.

If an artifact is unavailable/expired, a new run-scoped artifact/index may be generated for the same immutable discovery result. Native exact-source provider inspection and ChatGPT-local exact download remain valid fallbacks, including `media.preview_review_materializer --input-dir` when another trustworthy transport stages exact bytes.

GitHub Actions may download/read exact provider media and derive contact sheets because that is **transport-only** processing. GitHub Actions must never set `verified_preview`, assign semantic metadata, approve/reject a source, create a readiness manifest, or otherwise perform ChatGPT-owned editorial judgment. Metadata, title, tags, duration, or artifact creation alone are not enough to approve a clip.

`EVIDENCE_ACCESS_BLOCKED` is valid only after available indexed private artifacts and every other trustworthy exact-source transport are unusable for the candidates still needed for readiness. A successful required Background Management evidence run with a missing/mismatched index or artifact is `REVIEW_EVIDENCE_TRANSPORT_FAILED`, an infrastructure/contract failure, not a creative rejection. If the matching evidence run is still legitimately pending beyond the shared bounded continuation window, use `DEFERRED_REPLENISHMENT`.

Background Management remains the hard technical admission boundary after ChatGPT review: it re-fetches official Pexels metadata/renditions and validates the reviewed readiness manifest before any asset becomes selectable.

## New-production visual model

New requests use schema v7 `concatenated_fit_to_short`. For each candidate ChatGPT freezes a primary and backup ordered sequence of 2-3 distinct atomic clips, exact logical IDs, exact start/duration ranges, and sequence order. Primary and backup are disjoint. Playback rate is never frozen.

Runtime normalizes and trims each selected clip, concatenates the frozen sequence once, then derives `playback_rate = total_unique_sequence_source_seconds / required_background_output_duration` from the exact final timeline. Normal schema-v7 production has `loop_mode=none` and `loop_count=0`.

## Duration policy

Atomic clips require trusted provider duration and at least **60 seconds**. Each sequence freezes **210-300 seconds** total unique source coverage; **240-300 seconds** and 3 clips are preferred. Derived speed must stay within **1.0x-2.5x**. No clip repeats within a sequence and primary/backup may not share an asset.

## Retention and provider policy

Only active, verified, commercial-use, watermark-free, embedded-text-free, production-rendition-ready, quality/retention-qualified atomic sources are selectable. Preferred categories include cooking, baking, food preparation, satisfying processes, crafting, cleaning, assembly, POV movement, city/travel motion and explicitly commercially licensed gameplay.

Pexels remains the canonical automatic provider. Deterministic provider discovery first removes clips that fail trusted duration/rendition eligibility. ChatGPT then visually screens the remaining exact sources before `verified_preview=true` using the preview-evidence contract above; Background Management rechecks the official Pexels API before registry persistence. Automatic sourcing should prioritize useful 60-120 second clips. A single source no longer needs to be 180 seconds because coverage comes from the frozen multi-clip sequence.

## Primary/backup failure semantics

Runtime attempts the complete frozen primary sequence. If any required primary segment cannot execute, it may attempt the **entire frozen backup sequence**. It never partially mixes primary and backup or invents another fallback. If neither sequence executes, the candidate fails closed.

## Historical request behavior

Schema v4/v5/v6 remain understood for immutable recovery. Schema v6 retains its historical one-long-source `fit_to_short` behavior and 180-second minimum; it is not used for new planning. A historical request whose deleted logical background ID is absent from the active registry fails closed.

## Evidence

Schema-v7 receipts record chosen slot, ordered segment IDs/ranges, resolved renditions, per-clip hashes, total unique source duration, derived overall playback rate, concatenated output evidence and explicit zero loops. Dry-run retains opening card, branding, handle/subscribe UI, captions, word highlighting and semantic punchline emphasis while exercising the no-loop sequence path.
