# Background media strategy

## Active library lifecycle

`media-library/backgrounds.json` is the **only background registry**. Pre-reset background definitions were **destructively removed**; they are not retained in a hidden fallback registry. The current registry stores reusable **atomic clips**, not Short-specific composites, and may validly contain `"assets": []` after a hard reset. Empty or insufficient inventory audits as `REPLENISH` rather than corruption.

Daily and Ad-hoc share one readiness/replenishment path:

```text
audit -> REPLENISH -> ChatGPT reviews licensed Pexels atomic clips
      -> immutable readiness manifest -> Background Management enriches/persists
      -> refresh main -> audit again -> PASS -> planning continues
```

Readiness PASS requires the configured inventory/category minima and proof that two disjoint executable v7 sequences can actually be formed.

## New-production visual model

New requests use schema v7 `concatenated_fit_to_short`. For each candidate ChatGPT freezes a primary and backup ordered sequence of 2-3 distinct atomic clips, exact logical IDs, exact start/duration ranges, and sequence order. Primary and backup are disjoint. Playback rate is never frozen.

Runtime normalizes and trims each selected clip, concatenates the frozen sequence once, then derives `playback_rate = total_unique_sequence_source_seconds / required_background_output_duration` from the exact final timeline. Normal schema-v7 production has `loop_mode=none` and `loop_count=0`.

## Duration policy

Atomic clips require trusted provider duration and at least **60 seconds**. Each sequence freezes **210-300 seconds** total unique source coverage; **240-300 seconds** and 3 clips are preferred. Derived speed must stay within **1.0x-2.5x**. No clip repeats within a sequence and primary/backup may not share an asset.

## Retention and provider policy

Only active, verified, commercial-use, watermark-free, embedded-text-free, production-rendition-ready, quality/retention-qualified atomic sources are selectable. Preferred categories include cooking, baking, food preparation, satisfying processes, crafting, cleaning, assembly, POV movement, city/travel motion and explicitly commercially licensed gameplay.

Pexels remains the canonical automatic provider. ChatGPT visually reviews candidates before `verified_preview=true`; Background Management uses the official Pexels API to verify identity, duration and rendition metadata. Automatic sourcing should prioritize useful 60-120 second clips. A single source no longer needs to be 180 seconds because coverage comes from the frozen multi-clip sequence.

## Primary/backup failure semantics

Runtime attempts the complete frozen primary sequence. If any required primary segment cannot execute, it may attempt the **entire frozen backup sequence**. It never partially mixes primary and backup or invents another fallback. If neither sequence executes, the candidate fails closed.

## Historical request behavior

Schema v4/v5/v6 remain understood for immutable recovery. Schema v6 retains its historical one-long-source `fit_to_short` behavior and 180-second minimum; it is not used for new planning. A historical request whose deleted logical background ID is absent from the active registry fails closed.

## Evidence

Schema-v7 receipts record chosen slot, ordered segment IDs/ranges, resolved renditions, per-clip hashes, total unique source duration, derived overall playback rate, concatenated output evidence and explicit zero loops. Dry-run retains opening card, branding, handle/subscribe UI, captions, word highlighting and semantic punchline emphasis while exercising the no-loop sequence path.
