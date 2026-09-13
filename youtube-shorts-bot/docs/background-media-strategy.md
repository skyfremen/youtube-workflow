# Background media strategy

## Active library lifecycle

`media-library/backgrounds.json` is the **only background registry**. It may validly contain `"assets": []` after a hard reset. Empty or insufficient inventory audits as `REPLENISH`; it is not corruption.

The pre-reset background definitions were destructively removed. There is no legacy background registry, no soft-retirement pool, and no `selection_enabled=false` state. Deleted old logical background IDs are not recoverable through a hidden fallback.

Daily and Ad-hoc share one readiness/replenishment path:

```text
audit -> REPLENISH -> ChatGPT reviews long licensed Pexels sources
      -> immutable readiness manifest -> Background Management enriches/persists
      -> refresh main -> audit again -> PASS -> planning continues
```

The planner invocation owns this continuation. Users do not separately seed the library.

## New-production visual model

New requests use schema v6 `fit_to_short`.

The planner freezes distinct primary/backup logical IDs and one long continuous source range for each slot. The planner does **not** freeze exact playback rate.

The public runtime resolves/normalizes the selected rendition, generates TTS, obtains exact final render duration, then derives `playback_rate = selected_unique_source_range / required_background_output_duration`.

The job-local background is consumed once. Normal schema-v6 production has `loop_mode=none` and `loop_count=0`.

Example: a 300.0s selected range over a 151.4s render derives ~1.9815x with zero intentional loops.

## Duration policy

A new selectable asset requires trusted provider duration and at least the configured continuous-source minimum. Current code uses a 180-second minimum and prefers up to a 300-second continuous range. The live planner contract is authoritative.

A source too short to cover normal production inside allowed rate bounds is excluded/rejected and replenishment supplies a better asset. It is never repaired by looping.

## Retention-first selection

Backgrounds remain narration-first supporting visuals. High-retention categories include cooking, baking, food preparation, satisfying processes, crafting, cleaning, assembly, POV movement, city/travel motion and explicitly commercially licensed gameplay.

Continuous progression is a first-class quality requirement: a strong multi-minute process is preferred over an excellent few-second clip that would repeat many times.

Only active, verified, commercial-use, watermark-free, embedded-text-free, production-rendition-ready, quality/retention-qualified, duration-qualified sources are selectable.

## Pexels

Pexels remains the canonical automatic provider. ChatGPT visually reviews candidates. Background Management uses the official Pexels API to verify identity, duration and physical rendition metadata before persistence. Short clips below the continuous minimum are rejected during ingestion.

Random YouTube/TikTok/Instagram/Twitch creator footage is not a substitute for licensed provider footage.

## Physical rendition and cache

Target remains 1080x1920 at 30 fps using the smallest-sufficient-after-real-9:16-crop policy. Persistent cache identity belongs to the logical/physical normalized source, not a Short-specific speed/range. Fit-to-short output is job-local.

## Anti-repetition

Successful private receipts remain cross-run creative history. New planning avoids unnecessary reuse of the same asset/category and substantially overlapping ranges. Different non-overlapping ranges from a sufficiently long source may be reused later; merely changing speed over the same range is not meaningful diversity.

## Primary/backup and failure semantics

Both frozen slots must independently satisfy the continuous contract. There is no immortal `satisfying-001`/`satisfying-002` emergency pair and no unrelated third runtime fallback. If neither frozen slot can execute, the candidate fails closed.

## Historical request behavior after the hard reset

Schema v4/v5 request structure and execution semantics remain understood for compatibility, but old background definitions are not retained. A historical request whose logical background ID is absent from the current active registry fails closed rather than restoring, importing, or selecting a deleted pre-reset background.

No recovery path may recreate a deleted background library automatically. If a background is needed again, it must enter `backgrounds.json` through the same current reviewed/licensed readiness path as any other active asset.

## Evidence

For v6 the runtime records source/range/output timing, derived playback rate, hashes and explicit no-loop evidence. Receipt finalization requires `fit_to_short`, `loop_mode=none` and `loop_count=0`.

Dry-run remains a visual production test exercising continuous no-loop treatment while retaining opening card, branding, handle/subscribe UI, captions, word highlighting and semantic punchline emphasis.
