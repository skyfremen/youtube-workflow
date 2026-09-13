# Wacky Dramas System Overview

## Purpose

The canonical Shorts system uses a competitive planning funnel: generate broadly, reject weak or duplicate ideas cheaply, fully author a ranked reserve pool, mechanically validate frozen AI-authored candidates, promote only the highest-ranked valid winners, then feed comparable public performance back into future planning.

The business objective remains aggressive subscriber and qualified-view growth, including **1,000 subscribers** and **10 million qualified public Shorts views within a rolling 90-day window**.

A normal Daily plan publishes exactly **24 Shorts**, one per hour in **Asia/Singapore**. ChatGPT authors **36** complete ranked candidates. Ad-hoc planning authors **5** complete ranked candidates and promotes the first mechanically valid one.

## Architecture

```text
ChatGPT / Work
  -> inspect current private repo rules/config/analytics/history
  -> run live planner contract + shared media-readiness audit
  -> if background readiness is REPLENISH:
       -> discover/review licensed long continuous Pexels footage
       -> commit immutable replenishment manifest
       -> Background Management enriches and persists active registry
       -> refresh current main and rerun readiness until PASS
  -> generate/reject/score complete creative candidates
  -> choose exact primary/backup logical backgrounds
  -> freeze one long continuous range for each background slot
  -> do NOT freeze playback rate
  -> freeze final AI rank order

Daily:
  -> shared planner_precommit requires 36/36 valid
  -> commit immutable ranked-pool attempt
  -> private mechanical promotion of first target_count valid candidates
  -> dispatch public run.yml

Ad-hoc:
  -> shared planner_precommit requires 5/5 valid
  -> commit immutable ranked-pool attempt
  -> private mechanical promotion of first valid candidate
  -> dispatch public single-item execution

Public runtime:
  -> fetch exact promoted private state
  -> resolve/cache/normalize physical background rendition
  -> synthesize TTS and determine actual complete visible timeline
  -> derive playback rate = selected unique source duration / required background duration
  -> prepare one continuous fit-to-short background
  -> consume prepared background once; normal loop count = 0
  -> compose card + branding + captions + audio
  -> upload according to immutable publication mode
  -> verify exact YouTube state
  -> persist private immutable evidence/receipt
```

Private code remains the source-of-truth planner/validator/control plane. Public runtime remains a stateless heavy executor. GitHub Actions does not perform creative planning.

## Production output contract

The canonical rendered Short is **1080×1920** at 30 fps. The public runtime owns the exact video/audio encoding and verifies the final output before publication; private planning owns content and immutable production intent rather than rendering implementation.

## Schema and compatibility

**Schema v6 is current** for newly promoted Daily and Ad-hoc requests. It freezes story, narration, publication, logical primary/backup backgrounds and one continuous temporal range for each slot. Exact background playback rate is intentionally absent from the immutable request because it depends on actual post-TTS production timing.

**Schema v5 remains executable for historical immutable recovery** using its original fixed segment/playback semantics when its referenced logical background still exists in the current active registry. **Schema v4 remains executable** for older historical immutable recovery under the same fail-closed background-resolution rule. Deleted pre-reset background definitions are not preserved in a legacy registry and are never silently restored.

The private/public compatibility fingerprint covers current request and treatment semantics. Public execution validates source revision and compatibility before expensive work.

## Active background library

`media-library/backgrounds.json` is the **only background registry**. The hard reset destructively removed all previous background definitions rather than moving them into a legacy file. The valid post-reset state is an empty active registry.

```text
old background library
  -> DELETE definitions
backgrounds.json = empty
  -> readiness REPLENISH
next Daily or Ad-hoc planner invocation
  -> automatically source/review licensed long footage
  -> immutable replenishment manifest
  -> deterministic Pexels enrichment + validation
  -> backgrounds.json populated
  -> readiness PASS
  -> ranked-pool authorship continues
```

There is no legacy background registry, no `selection_enabled=false` retirement pool, and no immortal `satisfying-001` / `satisfying-002` emergency-default dependency. A historical request that references a deleted background fails closed rather than resurrecting it.

Readiness remains retention-first and diversity-aware, but a selectable new background must also have trustworthy duration and enough unique footage for continuous fit-to-short operation within configured runtime playback bounds.

## Continuous background execution

Old current-production behavior was approximately:

```text
short source/range
  -> planner-frozen speed
  -> FFmpeg infinite-loop input
  -> same few seconds repeat for full Short
```

New schema-v6 production is:

```text
long licensed source
  -> planner freezes useful continuous range
  -> TTS determines actual complete visible timeline
  -> runtime derives exact speed
  -> trim + speed one continuous range
  -> duration coverage validation
  -> compositor consumes prepared background once
  -> intentional normal loops = 0
```

Insufficient unique footage fails closed. Runtime does not repeat, freeze the last frame, restart the opening or substitute an unrelated third logical asset.

Persistent cache identity is based on the logical/physical normalized source rather than one Short's creative speed treatment. Range selection and derived rate are job-local outputs.

## Background ownership

Planner owns:

- logical primary and backup;
- selected continuous range for each;
- creative/category and retention suitability;
- crop/readability suitability;
- anti-repetition reasoning across successful private receipts;
- duration suitability.

Runtime owns:

- exact post-TTS required background duration;
- derived playback rate;
- physical rendition resolution/cache/normalization;
- deterministic trim/speed execution;
- fail-closed duration coverage validation;
- zero-loop execution evidence.

The background remains narration-first and retention-first rather than literal story reenactment. Preferred categories include cooking, baking, food preparation, satisfying processes, crafting, cleaning, assembly, POV movement, city/travel movement and explicitly licensed gameplay.

## Ranked planning and recovery

For new ranked pools, ChatGPT / Work owns final editorial rank. Deterministic code validates but never creatively repairs, reranks or substitutes backgrounds.

Daily pool size remains 36 with target 24. Ad-hoc pool size remains 5 with target 1. Promotion validates committed candidates again as defense in depth. If a candidate later fails current deterministic validation, promotion moves to the next candidate in frozen order; it does not repair the failed candidate.

Existing historical immutable requests are never mutated. Schema v4/v5 parsing and execution semantics remain available, but deleted old background assets do not: recovery resolves through the current active `backgrounds.json` only and fails closed when a referenced background is absent.
