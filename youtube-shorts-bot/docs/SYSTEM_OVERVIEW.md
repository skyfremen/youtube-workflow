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
  -> REPLENISH when inventory/category/sequence-pair feasibility is insufficient
  -> review licensed 60-120s Pexels atomic clips and commit immutable sourcing manifest
  -> Background Management verifies/persists atomic registry
  -> refresh main and repeat until PASS
  -> author complete candidates
  -> freeze primary and backup ordered 2-3 clip sequences and exact ranges
  -> do NOT freeze playback rate
  -> freeze final AI rank order

Private planner
  -> 36/36 Daily or 5/5 Ad-hoc planner precommit validation
  -> immutable ranked pool
  -> deterministic promotion in frozen rank order
  -> immutable request
  -> opaque dispatch to public runtime

Public runtime
  -> fetch exact immutable request
  -> resolve/cache/normalize every clip in selected sequence
  -> TTS + exact visible duration
  -> trim and concatenate frozen ranges once
  -> derive one playback rate from total unique source duration / required duration
  -> render with loop_mode=none and loop_count=0
  -> upload/verify YouTube state
  -> persist private immutable evidence/receipt
```

Private code remains the source-of-truth planner/validator/control plane. Public runtime remains a stateless heavy executor. GitHub Actions does not perform creative planning.

## Production output contract

The canonical rendered Short is **1080×1920** at 30 fps. Public execution owns exact video/audio encoding; private planning owns content and immutable production intent.

## Schema and compatibility

**Schema v7 is current** for newly promoted Daily and Ad-hoc requests. It freezes story, narration, publication, `concatenated_fit_to_short`, and two ordered disjoint background sequences. Each sequence has 2-3 distinct atomic clips and exact start/duration ranges. Exact playback rate remains runtime-derived after TTS.

**Schema v6 remains executable** for historical immutable recovery with its one-long-source `fit_to_short` contract. **Schema v5 remains executable** for historical fixed treatment recovery. **Schema v4 remains executable** for older immutable recovery. Historical requests are never rewritten into v7.

The private/public compatibility fingerprint covers current v7 request/sequence semantics while the public runtime retains accepted legacy fingerprints for immutable recovery.

## Active background library

`media-library/backgrounds.json` is the **only background registry**. The hard reset destructively removed the previous definitions; an empty registry is valid and audits as `REPLENISH`.

Selectable atomic clips must be active, verified, commercial-use, watermark/text free, retention/quality qualified, production-rendition ready, and at least 60 seconds long. Readiness requires the configured 32-asset/category inventory **and** proof that two disjoint executable sequences can be formed. Thus a registry of only 60-second clips cannot incorrectly PASS when no 210-second sequence is possible.

Pexels remains the automatic provider. Coverage comes from combining unique reviewed clips rather than requiring one source longer than Pexels normally provides.

## Schema-v7 background execution

Each primary/backup sequence contains 2-3 unique clips and freezes 210-300 seconds of unique source coverage; 240-300 seconds and 3 clips are preferred. Primary and backup share no logical asset.

Runtime attempts the complete frozen primary sequence. If it cannot resolve/execute it, runtime may attempt the complete frozen backup sequence. It never mixes the two, invents a third fallback, loops a clip, restarts a sequence, or freezes a final frame to manufacture coverage.

Successful receipts record the chosen slot, ordered IDs/ranges, physical renditions, hashes, total source duration, derived rate, output duration and explicit zero-loop evidence. Schema-v7 receipts are eligible for the normal analytics-learning pipeline.

## Planning and recovery

Daily and Ad-hoc share the same media readiness and planner validation contract. Existing immutable requests keep their original content identity during retries. Recovery reuses exact request bytes and never creates a replacement request merely because rendering, upload, verification or evidence persistence failed.
