# Background media strategy

## Active library lifecycle

`media-library/backgrounds.json` is the **only background registry**. Pre-reset background definitions were **destructively removed**; they are not retained in a hidden fallback registry. The current registry stores reusable **atomic clips**, not Short-specific composites, and may validly contain `"assets": []` after a hard reset. Empty or insufficient inventory audits as `REPLENISH` rather than corruption.

Daily and Ad-hoc share one readiness/replenishment path:

```text
audit -> REPLENISH -> immutable discovery request
      -> Background Management/Pexels API filters duration + rendition eligibility
      -> immutable discovery result with exact-source preview evidence URLs
      -> ChatGPT reviews actual visual evidence and assigns semantic metadata
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
- representative preview frames from the exact source;
- a short preview clip from the exact source;
- web/browser/image-search evidence that is unambiguously tied to the same Pexels provider asset ID.

Evidence retrieval is **tool-adaptive**. Native ChatGPT/Work web, browser and image-capable surfaces are canonical visual-review paths when available. The credential-free `media.preview_review_materializer` is an optional fallback for execution runtimes that actually provide outbound HTTPS; local Python networking is not a correctness dependency and must never be assumed. When search rather than a direct URL is used, the planner must prove the evidence belongs to the exact `provider_asset_id` or exact source page and must reject lookalike or substituted footage.

Metadata, title, tags or duration alone are **not** enough to set `verified_preview=true`.

The planner uses the preview only for semantic/visual screening: reject obvious watermarks, embedded text, unsafe material, static or weak footage, misleading metadata, or footage that is plainly unsuitable behind captions. If one visual transport cannot access a candidate, try the next available exact-source transport. If no actual visual evidence for that candidate remains accessible, reject that candidate and continue discovery/reserve sourcing. **Do not fail the whole replenishment attempt merely because local Python has no network, one provider URL is inaccessible, or full-length playback is unavailable.** If every trustworthy exact-source visual channel is unavailable for the discovery set, stop before readiness-manifest creation and report `EVIDENCE_ACCESS_BLOCKED`; this is distinct from `DEFERRED_REPLENISHMENT`, which is reserved for a genuinely pending Background Management workflow after the bounded continuation wait.

Once the matching immutable discovery result exists, provider discovery is complete for that attempt. The same planner invocation should proceed directly to visual review and readiness-manifest creation whenever an exact-source visual channel is available; it must not wait for a second planner invocation merely to perform review.

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
