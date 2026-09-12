# Background media strategy

## Ownership boundary

The private repository owns logical background planning, the registered logical asset library, licence/provenance metadata, and persistent creative history derived from immutable verified result receipts. The public runtime remains stateless across independent production runs and must not create a cross-run asset, segment, category, or playback-treatment ledger.

Schema v5 freezes the logical primary/backup IDs **and one immutable treatment for each slot**. The public runtime validates that frozen decision and owns physical work: rendition resolution, physical cache lookup, download, probing, post-crop quality validation, one-time normalization, application of the frozen treatment, caption-region analysis, and rendering.

A registered logical asset is not the same thing as a runner-local physical cache entry. A logical asset remains eligible when its physical file is absent from a runner cache. The normalized physical cache is an execution optimization, never persistent creative history.

Schema v4 remains readable only for staged migration and recovery of already-created requests. New Daily and Ad-hoc requests use schema v5.

## Retention-first logical selection

The default ranking order is visual retention first, topic relevance second. Strong continuous movement and subtitle readability are more important than literal story depiction. A relationship, workplace, family, or dating story may therefore use an unrelated but engaging process background when it is visually stronger.

Canonical high-retention categories are `cooking`, `baking`, `food_prep`, `satisfying_process`, `crafting`, `cleaning`, `assembly`, `pov_movement`, `city_motion`, and `licensed_gameplay`.

Older assets do not need a destructive migration. `media/background_selector.py` lazily infers a canonical category from existing title, visual-tag, and motion metadata when no explicit retention category exists. Useful existing assets remain available; weak generic assets simply rank below stronger retention footage.

`licensed_gameplay` must carry known commercial-use provenance. Creator footage from YouTube, TikTok, Instagram, Twitch, or similar social platforms is not automatically eligible merely because it can technically be downloaded or transformed.

## Asset, category, segment and playback anti-repetition

Cross-run recency and usage counts come from private immutable successful result receipts. Current immediate-public Ad-hoc receipts and scheduled Daily receipts participate in the same history.

Daily planning may pass ephemeral `planned_asset_ids`, `planned_categories`, and `planned_treatments` while allocating the current batch. This scratch state exists only during private planning and is not committed as public mutable state.

Logical asset selection happens first. `media/background_treatment.py` then reserves a deterministic treatment for each frozen primary/backup asset using private historical receipts plus the current Daily scratch list.

For sufficiently long assets, the treatment allocator divides the source into useful temporal candidates and penalizes recently used or already-planned overlapping ranges. Short or older assets without trustworthy duration metadata remain compatible through full-source treatment.

Playback rate is category/asset aware and globally constrained by the schema contract. It is a treatment, not a uniqueness loophole: changing speed does not make the same temporal content meaningfully new. The allocator rotates among safe rates only after segment/asset diversity rules are respected.

The immutable schema-v5 treatment shape is:

```json
{
  "segment_start_seconds": 12.0,
  "segment_duration_seconds": 12.0,
  "playback_rate": 1.4
}
```

`segment_duration_seconds: null` represents a full-source treatment and therefore requires a zero start offset.

## Daily and Ad-hoc treatment history

Daily Production coordinates up to 24 winners privately. For each winner it selects logical primary/backup assets, invokes the canonical treatment allocator, freezes both treatments into the request, and appends both reservations to the in-progress `planned_treatments` list before moving to the next winner.

Ad-hoc Production uses the same historical receipt rules for its one Short but has no 24-item scratch sequence. Its verified immediate-public receipt becomes private history for future Daily or Ad-hoc planning.

No public cross-run usage ledger, segment database, playback database, or committed mutable runtime state is permitted.

## Provenance

Externally sourced logical assets must retain the provider, provider asset ID when available, original source page, creator when available, licence, commercial-use decision, verification/acquisition timestamps, and official provider rendition metadata. The Pexels integration uses the official API and stores physical rendition dimensions, FPS, media type, direct provider media URL, and file size when supplied.

The runtime records hashes for the actual downloaded source, normalized master, and treated job-local render input in execution evidence where applicable. This is preferable to pretending a logical asset has one permanent file hash when the provider exposes multiple physical renditions.

## Physical rendition policy

The fixed production target is 1080×1920 at 30 fps. Physical selection is based on the useful image that remains after the real 9:16 crop, not on source dimensions alone.

The governing rule is **smallest sufficient after crop**:

1. discard unsupported or post-crop-insufficient renditions;
2. prefer a suitable native vertical rendition;
3. prefer exact production dimensions when available;
4. prefer FPS closest to 30 fps;
5. among equivalent geometry/FPS choices, prefer lower physical cost/file size when reliable;
6. download only the chosen suitable rendition and fall through to the next suitable rendition on physical failure.

A 1920×1080 landscape source leaves only about 607.5×1080 of useful portrait crop. Producing 1080×1920 from it requires roughly 1.78× enlargement, so it is correctly rejected by the current bounded-upscale policy. A 3840×2160 landscape source may legitimately be selected when no smaller rendition survives the portrait crop. UHD is therefore neither always selected nor categorically prohibited.

Unknown provider originals cannot bypass this policy. A generic/original URL is eligible only when its known metadata independently satisfies the same production suitability rules.

## One-time normalization, treatment and physical cache

After download, the runtime probes the real file and re-validates post-crop suitability. A source that is not already render-ready H.264 1080×1920/30 is normalized once to the production geometry/FPS/codec. The normalized result is cached using logical asset, physical rendition, URL, target dimensions and FPS as cache identity.

A cache hit reuses the production-ready normalized file without re-downloading or re-normalizing it. Segment/speed treatment is deliberately **not** part of this persistent physical-cache identity.

For schema v5, the runtime copies/reuses the normalized asset into the active job and then applies the immutable treatment to that job-local production-sized input. Treatment therefore does not make the renderer repeatedly scale an oversized provider original and does not contaminate the reusable normalized master.

The final renderer continues to consume production-sized 1080×1920/30 frames. Treatment may trim the selected temporal range and adjust timestamps/playback speed, but it must not reintroduce unnecessary scale/crop work.

The runtime records source dimensions/FPS, downloaded bytes, download duration, effective crop dimensions, upscale factor, normalization decision/duration, normalized bytes/hash, treatment timing and treated bytes/hash, plus physical cache hit/key where available. These metrics are intended to catch regressions such as downloading a 90 MB 4K source when a much smaller production-sufficient rendition exists.

## Compatibility and immutable receipts

The private/public compatibility fingerprint includes schema-v5 treatment fields and treatment bounds. Public rollout explicitly retains the exact previous v4 fingerprint so public v5 can be deployed before private v5 without interrupting already-dispatched/legacy v4 work.

A schema-v5 completion receipt records the selected logical asset and the treatment that was actually executed. Finalization fails closed if runtime treatment evidence differs from the frozen request slot. Those immutable receipts become the private source for future segment/playback anti-repetition.

## Subtitle safety and fallback

The registry quality metadata includes caption readability. The runtime samples the caption-safe region of the treated physical clip and applies the existing bounded soft caption protection when needed. Selection should prefer a better candidate rather than excessively darkening footage.

Logical fallback remains frozen primary then frozen backup; the public runtime must never substitute an unrelated third logical asset. Each logical slot carries its own immutable treatment. Within one logical asset, physical rendition failure may fall through to the next production-suitable rendition before the selected slot's treatment is applied.

If registered choices are insufficient during private Daily planning, use the existing reviewed licensed sourcing path. Ad-hoc remains governed by its existing cache/sourcing contract as implemented by the current planner/runtime.

The existing library is retained. Do not bulk-delete assets merely because they are older, generic, or topic-oriented. Quarantine/remove only for objective corruption, unsupported/invalid media, confirmed licence problems, duplication, or clearly unusable quality.
