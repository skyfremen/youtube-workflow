# Background media strategy

## Ownership boundary

The private repository owns logical background planning, the registered logical asset library, licence/provenance metadata, and persistent creative history derived from immutable verified result receipts. The public runtime must remain stateless across independent production runs and must not create a cross-run asset, segment, category, or playback-treatment ledger.

The immutable request freezes only the logical primary and backup background IDs under the current schema. The public runtime validates those IDs and owns physical work: rendition resolution, physical cache lookup, download, probing, post-crop quality validation, one-time normalization, caption-region analysis, and rendering.

A registered logical asset is not the same thing as a runner-local physical cache entry. A logical asset remains eligible when its physical file is absent from a runner cache.

## Retention-first logical selection

The default ranking order is now visual retention first, topic relevance second. Strong continuous movement and subtitle readability are more important than literal story depiction. A relationship, workplace, family, or dating story may therefore use an unrelated but engaging process background when it is visually stronger.

Canonical high-retention categories are:

- `cooking`
- `baking`
- `food_prep`
- `satisfying_process`
- `crafting`
- `cleaning`
- `assembly`
- `pov_movement`
- `city_motion`
- `licensed_gameplay`

Older assets do not need a destructive migration. `media/background_selector.py` lazily infers a canonical category from existing title, visual-tag, and motion metadata when no explicit retention category exists. Useful existing assets remain available; weak generic assets simply rank below stronger retention footage.

`licensed_gameplay` is deliberately special. It must be explicitly classified and must carry known commercial-use provenance. Creator footage from YouTube, TikTok, Instagram, Twitch, or similar social platforms is not automatically eligible merely because it can technically be downloaded or transformed.

## Anti-repetition

Cross-run recency and usage counts come from private immutable successful result receipts. The selector keeps the existing hard recent-asset avoidance and adds soft penalties for repeated categories and long-term asset use. Daily planning may additionally pass ephemeral `planned_asset_ids` and `planned_categories` while allocating a batch; these are in-memory planning context only and are never persisted in the public runtime.

Category rotation is intentionally soft. A strong clip may beat a weaker different-category clip. Different crops or playback rates do not make the same underlying footage meaningfully unique.

The current request schema carries only primary and backup logical IDs. Therefore persistent segment reservations cannot be transmitted to the stateless runtime without a deliberate request/contract evolution. Do not work around that by creating mutable public state. Until the contract is intentionally extended, segment-level cross-run history remains a future contract change rather than an implicit runtime feature.

## Provenance

Externally sourced logical assets must retain the provider, provider asset ID when available, original source page, creator when available, licence, commercial-use decision, verification/acquisition timestamps, and official provider rendition metadata. The Pexels integration uses the official API and stores physical rendition dimensions, FPS, media type, direct provider media URL, and file size when supplied.

The runtime records hashes for the actual downloaded source and normalized render input in execution evidence. This is preferable to pretending a logical asset has one permanent file hash when the provider exposes multiple physical renditions.

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

## One-time normalization and physical cache

After download, the runtime probes the real file and re-validates post-crop suitability. A source that is not already render-ready H.264 1080×1920/30 is normalized once to the production geometry/FPS/codec. The normalized result is cached using the logical asset, physical rendition, URL, target dimensions, and FPS as cache identity.

A cache hit must reuse the production-ready normalized file without re-downloading or re-normalizing it. The final renderer therefore normally loops production-sized frames rather than repeatedly decoding and scaling an oversized provider source.

The runtime records source dimensions/FPS, downloaded bytes, download duration, effective crop dimensions, upscale factor, normalization decision/duration, normalized bytes/hash, and physical cache hit/key. These metrics are intended to catch regressions such as downloading a 90 MB 4K source when a much smaller production-sufficient rendition exists.

## Subtitle safety and fallback

The registry quality metadata includes caption readability. The runtime also samples the caption-safe region of the selected physical clip and applies the existing bounded soft caption protection when needed. Selection should prefer a better candidate rather than excessively darkening footage.

Logical fallback remains frozen primary then frozen backup; the public runtime must never substitute an unrelated third logical asset. Within one logical asset, physical rendition failure may fall through to the next production-suitable rendition. If registered choices are insufficient during private planning, Daily Production may use the existing reviewed licensed sourcing path. Ad-hoc planning remains cache-only under its current contract.

The existing library is retained. Do not bulk-delete assets merely because they are older, generic, or topic-oriented. Quarantine/remove only for objective corruption, unsupported/invalid media, confirmed licence problems, duplication, or clearly unusable quality.
