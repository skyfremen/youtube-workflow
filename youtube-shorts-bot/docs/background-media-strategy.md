# Background media strategy

## Active library lifecycle

`media-library/backgrounds.json` is the **only background registry**. It stores reusable **atomic clips**, not Short-specific composites. It may validly contain `"assets": []` after a hard reset. Empty or insufficient inventory audits as `REPLENISH`; it is not corruption.

Daily and Ad-hoc share one readiness/replenishment path:

```text
audit -> REPLENISH -> ChatGPT reviews licensed Pexels atomic clips
      -> immutable readiness manifest -> Background Management enriches/persists
      -> refresh main -> audit again -> PASS -> planning continues
```

The planner invocation owns this continuation. Users do not separately seed the library.

## New-production visual model

New requests use schema v7 `concatenated_fit_to_short`.

For **each candidate**, ChatGPT freezes:

- one primary ordered sequence of 2-3 distinct atomic clips;
- one backup ordered sequence of 2-3 distinct atomic clips;
- exact logical background IDs;
- exact start/duration range for every clip;
- the exact sequence order.

Primary and backup sequences must be disjoint. The planner never freezes playback rate and the runtime never creatively reorders or substitutes clips.

The public runtime resolves and normalizes all clips in the chosen frozen sequence, trims the frozen ranges, concatenates them **once**, generates/uses the exact final render duration, then derives:

`playback_rate = total_unique_sequence_source_seconds / required_background_output_duration`

The combined sequence is consumed once. Normal schema-v7 production has `loop_mode=none` and `loop_count=0`.

## Duration policy

Atomic clips require trusted provider duration and at least **60 seconds**. The registry remains atomic so the same reviewed clip can be used in different future immutable sequence plans without storing composite variants.

Each primary/backup sequence must contain 2-3 clips and freeze **210-300 seconds** of total unique source coverage; **240-300 seconds** and 3 clips are preferred. The runtime-derived overall speed must remain within **1.0x-2.5x**.

No clip may repeat within a sequence. Primary and backup sequences may not share an asset. Insufficient coverage is never repaired by looping.

## Retention-first selection

Backgrounds remain narration-first supporting visuals. High-retention categories include cooking, baking, food preparation, satisfying processes, crafting, cleaning, assembly, POV movement, city/travel motion and explicitly commercially licensed gameplay.

Prefer visually coherent progressions such as cooking + baking + food preparation or crafting + satisfying process + cleaning. Avoid jarring category changes unless the planner has an explicit editorial reason.

Only active, verified, commercial-use, watermark-free, embedded-text-free, production-rendition-ready, quality/retention-qualified, duration-qualified atomic sources are selectable.

## Pexels

Pexels remains the canonical automatic provider. ChatGPT visually reviews candidates before `verified_preview=true`. Background Management uses the official Pexels API to verify identity, duration and physical rendition metadata before persistence.

Automatic sourcing should prioritize 60-120 second satisfying clips. A source shorter than the atomic minimum is rejected. A source does **not** need to be 180 seconds long because coverage is provided by the frozen multi-clip sequence.

Random YouTube/TikTok/Instagram/Twitch creator footage is not a substitute for licensed provider footage.

## Physical rendition and cache

Target remains 1080x1920 at 30 fps using the smallest-sufficient-after-real-9:16-crop policy. Persistent cache identity belongs to each logical/physical normalized atomic source, not a Short-specific sequence/speed/range. Concatenated fit-to-short output is job-local.

## Anti-repetition

Successful private receipts remain cross-run creative history. New planning avoids unnecessary reuse of the same assets, categories, exact sequences and substantially overlapping temporal ranges. Reordering the same clips is not meaningful diversity by itself.

## Primary/backup and failure semantics

Both frozen sequences must independently satisfy the complete sequence contract. Runtime attempts the frozen primary sequence. If any required primary clip cannot be resolved/executed, it may attempt the **entire frozen backup sequence**. It must never partially mix primary and backup or invent a third fallback.

If neither frozen sequence can execute, the candidate fails closed.

## Historical request behavior

Schema v4/v5/v6 structures and execution semantics remain understood for immutable recovery. Schema v6 retains the historical one-long-source `fit_to_short` behavior and its 180-second minimum; it is not used for new planning.

Deleted pre-reset background definitions are not restored through hidden fallback state. A historical request whose logical ID is absent from the current active registry fails closed.

## Evidence

For v7 the runtime records the chosen slot, ordered segment IDs/ranges, resolved physical renditions, per-clip hashes, total unique source duration, derived overall playback rate, concatenated output hash and explicit zero-loop evidence.

Receipt finalization requires `concatenated_fit_to_short`, `loop_mode=none`, `loop_count=0`, and exact equality between the immutable selected sequence and execution evidence.

Dry-run remains a visual production test retaining opening card, branding, handle/subscribe UI, captions, word highlighting and semantic punchline emphasis while using the no-loop sequence treatment.
