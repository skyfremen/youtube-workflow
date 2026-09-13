# Background media strategy

## Active library lifecycle

`media-library/backgrounds.json` is the **only background registry**. Pre-reset background definitions were **destructively removed**; they are not retained in a hidden fallback registry. The current registry stores reusable **atomic clips**, not Short-specific composites, and may validly contain `"assets": []` after a hard reset. Empty or insufficient inventory audits as `REPLENISH` rather than corruption.

Daily and Ad-hoc share one readiness/replenishment path:

```text
audit -> REPLENISH -> immutable discovery request
      -> Background Management/Pexels API filters duration + rendition eligibility
      -> immutable discovery result with exact-source preview URLs
      -> ChatGPT/Work downloads/opens those exact sources locally
      -> representative frames and/or short motion evidence are inspected by ChatGPT
      -> ChatGPT assigns approval + semantic metadata
      -> immutable readiness manifest -> Background Management re-enriches/persists
      -> refresh main -> audit again -> PASS -> planning continues
```

Provider discovery is deliberately split from editorial review. `media.pexels_discovery` may use the GitHub-held `PEXELS_API_KEY` to fetch exact provider metadata and discard clips below the live atomic-duration minimum or without a production-suitable rendition. It must not set `verified_preview=true`, invent semantic tags/scores, or write to the active registry. ChatGPT/Work remains the owner of visual/editorial approval.

A discovery request is an immutable JSON object under `content/background-sourcing/discovery-requests/` containing exactly `schema_version`, `plan_date`, `request_id`, and `max_candidates`. Background Management writes the matching immutable provider result under `content/background-sourcing/discovery-results/`. The result contains trusted duration/rendition eligibility plus exact-source preview image/video URLs for review; it is not an admission decision.

Readiness PASS requires the configured inventory/category minima and proof that two disjoint executable v7 sequences can actually be formed.

## Preview-review evidence

`verified_preview=true` means ChatGPT/Work reviewed **actual visual evidence for the exact Pexels source** before proposing it. Full-length or end-to-end video playback is **not required**.

Acceptable evidence includes the strongest exact-source visual surface available in the current execution environment, such as:

- the exact provider page's visual preview;
- the exact `preview_image_url` from the immutable discovery result;
- representative preview frames extracted from the exact immutable `preview_video_url`;
- a short local preview clip from that exact source;
- web/browser/image-search evidence that is unambiguously tied to the same Pexels provider asset ID;
- an optional public/runtime evidence artifact only when it is available and independently tied to the same immutable request/source identity.

Evidence retrieval is **tool-adaptive**, but the canonical planner-time path is local to ChatGPT/Work rather than a required GitHub Actions evidence workflow. Once the immutable discovery result exists, ChatGPT/Work should use the exact recorded preview URLs directly. If its native visual tools can inspect the exact source, use them. If it can download the exact discovered media into local working storage, use the downloaded bytes and local media tooling to derive representative frames/contact sheets or a short motion sample and inspect those pixels.

When local Python has outbound HTTPS and FFmpeg/media tooling, `media.preview_review_materializer` is the canonical repository helper:

```bash
PYTHONPATH=youtube-shorts-bot python -m media.preview_review_materializer \
  --discovery-result <discovery-result.json> \
  --output-dir <temporary-review-evidence-dir> \
  --include-motion-evidence
```

When local Python networking is unavailable but another exact download/file-transfer surface exists, stage the exact immutable preview bytes using the provider-ID layout below, then rerun the same helper with `--input-dir`:

```text
<temporary-input-dir>/<provider_asset_id>/preview.jpg
<temporary-input-dir>/<provider_asset_id>/preview.mp4
```

`preview.jpeg`, `preview.png`, `preview.webp`, `preview.mov`, and `preview.webm` are also accepted. The staged file must come from that candidate's exact immutable `preview_image_url` or `preview_video_url`; a visually similar substitute is never acceptable.

```bash
PYTHONPATH=youtube-shorts-bot python -m media.preview_review_materializer \
  --discovery-result <discovery-result.json> \
  --input-dir <temporary-input-dir> \
  --output-dir <temporary-review-evidence-dir> \
  --include-motion-evidence
```

The helper prefers staged exact local bytes when present and records the immutable Pexels preview URL as source identity. For local video it derives the same representative contact sheet and motion sample using FFmpeg. This explicitly separates **transport** from **review**: another tool may move exact bytes into local storage, but only ChatGPT/Work may inspect the resulting pixels/motion and approve them.

When local Python networking is unavailable but another exact download surface exists, that is still a valid canonical path: download the exact immutable `preview_video_url` or `preview_image_url`, preserve the exact-source identity, then inspect/extract representative evidence locally with available tooling. Local Python outbound HTTPS is **not** a correctness dependency.

A public/runtime review-evidence workflow may remain as an optional transport fallback. It must never be required for planner continuation, and its absence, startup failure, expired artifact, or terminal failure is not a blocker when native or local exact-source review works. GitHub Actions must never set `verified_preview`, assign semantic metadata, approve/reject a source, create a readiness manifest, or otherwise perform ChatGPT-owned editorial judgment.

Metadata, title, tags or duration alone are **not** enough to set `verified_preview=true`.

The planner uses the preview only for semantic/visual screening: reject obvious watermarks, embedded text, unsafe material, static or weak footage, misleading metadata, or footage that is plainly unsuitable behind captions. If one visual transport cannot access a candidate, try the next available exact-source transport. If a generic file-download/file-transfer primitive can retrieve the exact immutable preview, the planner must stage it and run the `--input-dir` path before declaring evidence inaccessible. If no actual visual evidence for that candidate remains accessible, reject that candidate and continue discovery/reserve sourcing. **Do not fail the whole replenishment attempt merely because local Python has no network, one provider URL is inaccessible, a public fallback failed, or full-length playback is unavailable.** If every trustworthy exact-source visual channel is unavailable for the discovery set, stop before readiness-manifest creation and report `EVIDENCE_ACCESS_BLOCKED`.

Once the matching immutable discovery result exists, provider discovery is complete for that attempt. The same planner invocation should proceed directly to visual review and readiness-manifest creation whenever an exact-source visual channel is available. `DEFERRED_REPLENISHMENT` is valid only while a **required** Background Management discovery or readiness-ingestion run is legitimately queued/in-progress after the bounded continuation window; it is not valid merely because local Python lacks networking/media tools, because an optional public evidence workflow failed, or because one candidate's evidence failed.

Background Management remains the hard technical admission boundary. It uses the official Pexels API to verify provider identity, trusted duration and production rendition metadata, then applies registry validation before the asset becomes selectable. A planner preview review never substitutes for those downstream checks.

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
