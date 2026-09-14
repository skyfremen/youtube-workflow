# Background media strategy

## Active library lifecycle

`media-library/backgrounds.json` is the canonical background registry. It stores reusable atomic clips, not Short-specific composites, and may legitimately be below the media-library maintenance thresholds.

Global inventory readiness is a **maintenance signal**, not a Daily/Ad-hoc planner admission gate. New planning does not stop merely because repository-wide readiness is `REPLENISH`, does not create/resume planner-bound replenishment sessions, and does not wait for discovery/readiness events before authoring a pool.

Background discovery, provider transport, visual review, deterministic ingestion, readiness auditing and replenishment-state tooling may continue to exist for separate media-library maintenance. Those tools must not be interpreted as prerequisites for a normal Daily or Ad-hoc planning invocation.

## Selected-background rule for new planning

A new planner invocation cares only about the exact assets selected by its actual production candidates.

For every selected asset, the current hard requirements remain mandatory, including where applicable:

- registered in the active registry;
- active and selectable;
- verified and visually reviewed;
- commercial use allowed;
- watermark free;
- no embedded text;
- trusted provider duration;
- production-suitable rendition;
- quality/retention thresholds;
- valid segment range;
- schema compatibility.

Global minimum asset counts, per-category inventory minimums, global sequence-capacity calculations and reserve-media targets do not invalidate an otherwise hard-valid selected sequence.

## Category model

Current logical categories are normalized by the repository background selector. New planning uses one `background_category` per pool candidate.

Every clip in both the candidate's primary and backup sequences must belong to that same category.

Correct:

```text
background_category = cooking
PRIMARY = cooking A, cooking B, cooking C
BACKUP  = cooking D, cooking E, cooking F
```

Incorrect:

```text
background_category = cooking
PRIMARY = cooking A, cleaning B, city C
```

Different Daily candidates may use different categories, and semantic/editorial diversity remains useful across the batch.

## Preferred category and canonical fallback

ChatGPT/Work chooses the category that best suits the story first.

If the preferred category cannot form hard-valid primary and backup sequences:

```text
preferred suitable category unavailable
→ try another suitable eligible category
→ if still needed, use the canonical fallback category exposed by the exact-SHA connector checkpoint contract
```

There is one canonical fallback configuration; prompts must not duplicate a different fallback constant.

The fallback category is intended to favor broad story compatibility, continuous visual motion, subtitle readability, reliable production renditions and sufficient usable inventory. Fallback never relaxes hard selected-asset validation or same-category requirements.

## New-production visual model

New requests use schema v7 `concatenated_fit_to_short`.

For each candidate ChatGPT freezes:

- one primary ordered sequence;
- one backup ordered sequence;
- 2–3 distinct clips per sequence, with 3 preferred;
- exact logical background IDs;
- exact sequence order;
- exact segment start seconds;
- exact segment duration seconds.

Primary and backup are disjoint. Every chosen segment satisfies the current minimum source-duration rule and each sequence satisfies the current allowed total unique-source-duration range. No clip is intentionally repeated to fill time and normal schema-v7 production does not intentionally loop.

ChatGPT does **not** choose, calculate or freeze playback rate. Runtime normalizes/trims the selected clips, concatenates the frozen sequence once, then derives the overall playback rate from total unique selected source duration and the final actual narration/timeline duration. Runtime still enforces its supported rate bounds and fails closed if the frozen request cannot execute.

## Duration policy

The current repository contract remains authoritative for numeric constants. At this version:

- atomic clips require trusted duration and at least 60 seconds;
- each sequence uses 2–3 clips;
- each sequence freezes 210–300 seconds of total unique source coverage;
- 240 seconds and 3 clips are preferred;
- primary and backup may not share an asset;
- no duplicate clip is permitted within one sequence.

Do not copy numeric constants into additional planner prompts when the machine-readable checkpoint contract can supply them.

## Retention and provider policy

Only active, verified, commercial-use, watermark-free, embedded-text-free, production-rendition-ready, quality/retention-qualified atomic sources are selectable. Preferred high-retention categories include cooking, baking, food preparation, satisfying processes, crafting, cleaning, assembly, POV movement, city/travel motion and explicitly commercially licensed gameplay.

Pexels remains the canonical automatic discovery provider for media-library maintenance. Provider metadata or search category is provenance, not visual truth. ChatGPT/Work visual review is still required before a discovered clip becomes verified/selectable; deterministic background-management tooling rechecks provider/licensing/rendition facts before registry persistence.

## Separate media-library maintenance

The existing discovery/review/readiness tooling may continue to support deliberate library maintenance, including immutable discovery requests/results, review evidence, review decisions, ingestion manifests and readiness events. These artifacts are not deleted and remain useful for maintenance/history.

A media-maintenance operation may still use `media.media_readiness` to identify inventory/category deficits and may refill the registry according to its own bounded workflow. That maintenance workflow must remain separate from normal Daily/Ad-hoc planner execution and must not turn a repository-wide inventory deficit into a planner-terminal result.

GitHub Actions may perform deterministic provider discovery, transport, contact-sheet generation, registry ingestion and technical validation where already authorized. It must never make ChatGPT-owned visual/editorial approval decisions.

## Preview-review evidence for maintenance

When new media is deliberately sourced, `verified_preview=true` means ChatGPT/Work reviewed actual visual evidence for the exact source before approval. Transport success, metadata, duration, title/tags or artifact generation alone are not approval.

The private Background Management review-evidence artifact remains a valid transport mechanism for exact-source contact sheets. Review decisions should continue to bind to immutable source/evidence identities, and deterministic ingestion should continue to revalidate provider facts before an asset becomes selectable.

## Primary/backup runtime failure semantics

Runtime attempts the complete frozen primary sequence. If a required primary segment cannot execute, it may attempt the **entire frozen backup sequence**. It never partially mixes primary and backup or invents another background. If neither frozen sequence executes, the candidate fails closed.

## Historical request behavior

Schema v4/v5/v6 remain understood for immutable recovery. Schema v6 retains its historical one-long-source `fit_to_short` behavior and its historical readiness semantics; it is not used for new planning.

Historical replenishment/discovery/review/readiness artifacts remain immutable history. They must not be destructively migrated, and their existence does not block a new schema-v7 Daily/Ad-hoc planner invocation.

## Evidence and receipts

Schema-v7 production receipts continue to record the chosen slot, ordered segment IDs/ranges, resolved renditions, per-clip hashes, total unique source duration, runtime-derived overall playback rate, concatenated output evidence and explicit no-loop behavior. This refactor changes planner admission/cardinality, not the public runtime request or receipt contract.
