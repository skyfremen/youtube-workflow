# Background media strategy

## Ownership boundary

The private repository owns logical background planning, the registered logical asset library, licence/provenance metadata, private successful-use history, media readiness/replenishment and all planning policy. The public runtime remains stateless across independent production runs and must not create a cross-run asset, segment, category or playback-treatment ledger.

For newly authored schema-v5 ranked pools, **ChatGPT / Work owns the final logical background and treatment decisions**. It reads current registry/policy/history, chooses primary/backup assets, reasons about audit eligibility and repetition, and freezes one immutable treatment for each slot.

Private code independently validates hard facts. It may reject a candidate but must not choose a different story, background, segment or playback rate.

The public runtime owns physical production work only: rendition resolution, physical cache lookup, download, probing, post-crop quality validation, normalization, application of the frozen treatment, caption-region analysis and rendering.

Schema v4 remains executable only for historical immutable recovery. New Daily and Ad-hoc requests use schema v5.

## Shared media readiness and replenishment

Daily and Ad-hoc use the same private planning-time readiness prerequisite. Neither path may author/promote new production against an inventory that reports `REPLENISH`.

The canonical gate is:

```bash
python -m media.media_readiness audit --allow-not-ready
```

The live thresholds are exposed by `planning/planner_contract.py` and currently require both a minimum total selectable inventory and category minimums across the high-retention pool. These values are repository configuration, not prompt memory.

If readiness is `PASS`, ChatGPT plans only from selectable assets. If readiness is `REPLENISH`, ChatGPT must first discover and visually review licensed Pexels candidates, then create one immutable manifest under `content/background-sourcing/readiness/`. `background-management.yml` uses the official Pexels API to enrich those reviewed logical candidates with physical rendition metadata, validates them, persists the shared registry and requires readiness to become `PASS` before new planning continues.

Pexels enrichment in the private repository is metadata/control-plane work. Production footage download, normalization, treatment and render remain public runtime responsibilities.

## Retired library semantics

`selection_enabled=false` means **historical recovery only**.

A retired asset remains in `media-library/backgrounds.json` so an already-sealed immutable request can still resolve its exact historical logical ID. It is excluded from:

- new Daily selection;
- new Ad-hoc selection;
- retention-first ranking;
- planning-time primary/backup audit;
- emergency-default use for new production.

The one-time library reset therefore retires the old selectable pool instead of physically erasing historical definitions. From the perspective of new planning, the old library is empty; from the perspective of immutable recovery, its provenance and logical identities still exist.

New request validation also requires the shared registry to be readiness `PASS`. Existing immutable request files bypass only that new-planning readiness check and may resolve a retired historical asset. This keeps the reset fail-closed without stranding recovery.

## Retention-first logical selection

The background is supporting motion for a narration-first Short; literal story reenactment is not required. Visual retention, continuous motion and subtitle readability are more important than literal topic match.

Canonical high-retention categories include `cooking`, `baking`, `food_prep`, `satisfying_process`, `crafting`, `cleaning`, `assembly`, `pov_movement`, `city_motion`, and explicitly licensed `licensed_gameplay`.

Weak/static/overused assets rank lower. Assets retired by the library reset are never eligible for new production regardless of their historical score.

`licensed_gameplay` requires explicit commercial-use provenance. Creator footage from YouTube, TikTok, Instagram, Twitch or similar social platforms is not eligible merely because it can be downloaded or transformed.

## Planning-time audit

For every candidate ChatGPT checks the current private registry and policy before freezing a pair. Primary/backup must:

- be distinct registered logical IDs;
- have `selection_enabled` not set to `false`;
- be active and verified;
- allow commercial use;
- be watermark-free and free of embedded text;
- meet the current quality floor;
- have at least one production-suitable rendition after the real 9:16 crop;
- satisfy current caption-readability and safety expectations.

Recency, category variety, retention quality and semantic/story fit are planning judgments. Hard registry/licensing/rendition/readiness facts are independently rechecked by `validation/validate_content.py` during precommit/promotion.

When a normal pair cannot safely satisfy policy, ChatGPT may choose the currently configured emergency default pair from `media/background_selector.py` only if both defaults remain currently selectable. A retired default is not a fallback. There is no arbitrary third-asset runtime fallback.

## Asset, category, segment and playback anti-repetition

Cross-run history comes only from private immutable successful receipts. Failed renders/uploads do not count as successful creative use.

For a Daily 36-candidate pool, ChatGPT should reason across the entire candidate set so high-ranked and reserve candidates do not unnecessarily repeat the same assets, categories, temporal ranges or playback rates. Ad-hoc uses the same receipt-derived history for its five candidates.

`media/background_treatment.py` remains a private **policy/history reference and optional planning aid**. It documents current segment windows, category-aware speed ranges and receipt interpretation. Its deterministic selection helpers are not authoritative for new ranked-pool production. ChatGPT must freeze the final treatment in each candidate request; the promoter only validates it.

The immutable schema-v5 treatment shape is:

```json
{
  "segment_start_seconds": 12.0,
  "segment_duration_seconds": 12.0,
  "playback_rate": 1.4
}
```

`segment_duration_seconds: null` represents full-source treatment and requires `segment_start_seconds: 0`.

When registry duration is unknown or untrusted, ChatGPT must use that full-source representation rather than inventing an offset/window that cannot be mechanically bounded.

Playback rate must remain within the current schema contract and current category/asset policy. Changing speed does not make the same temporal content meaningfully unique.

## Daily and Ad-hoc planning pools

Daily ChatGPT first requires shared media readiness `PASS`, then authors **36** complete ranked candidates. Each candidate already contains final logical primary/backup IDs and both immutable treatments. `daily-production.yml` validates candidates in frozen rank order and promotes the first required valid candidates; it does not allocate treatments.

Ad-hoc uses the exact same media-readiness/replenishment prerequisite, then authors **5** complete ranked candidates. `adhoc-production.yml` promotes the first mechanically valid candidate; it does not allocate a new treatment.

A later recovery always reuses the exact treatment stored in the promoted immutable request. Recovery never chooses a new segment/rate because an earlier run failed.

## Provenance

Externally sourced logical assets retain provider, provider asset ID when available, source page, creator when available, licence, commercial-use decision, verification/acquisition timestamps and official provider rendition metadata.

The Pexels integration uses the official API. Random creator footage from social platforms must not be substituted for reviewed licensed sources.

The runtime records hashes/evidence for the actual downloaded source, normalized master and treated job-local input when applicable. A logical asset may have multiple physical renditions; it should not be modeled as one permanent physical file hash.

## Physical rendition policy

Production target is **1080×1920 at 30 fps**. Physical selection uses the useful image remaining after the real 9:16 crop.

The rule is **smallest sufficient after crop**:

1. discard unsupported or post-crop-insufficient renditions;
2. prefer a suitable native vertical rendition;
3. prefer exact production dimensions when available;
4. prefer FPS closest to 30;
5. among equivalent choices, prefer lower physical/network/decode cost;
6. download only the chosen suitable rendition and fall through to the next suitable rendition on physical failure.

A 1920×1080 landscape source leaves only about 607.5×1080 of useful portrait crop and normally requires excessive enlargement. A 3840×2160 landscape rendition can be valid when its portrait crop remains sufficient. UHD is therefore neither always selected nor categorically forbidden.

Unknown provider originals cannot bypass the same suitability checks.

## Normalization, cache and frozen treatment execution

After download, the public runtime probes the real file and re-validates post-crop suitability. A non-render-ready source is normalized to production geometry/FPS/codec and may be cached physically.

Persistent physical-cache identity is based on logical asset, physical rendition/source and production target—not the creative segment/playback treatment.

For schema v5, the runtime reuses/copies the normalized master into the active job and applies the request's immutable treatment to that job-local input. This keeps the normalized master reusable and avoids repeatedly scaling oversized provider originals.

The runtime records source dimensions/FPS, bytes, download duration, effective crop, upscale factor, normalization decision, hashes, treatment timing, treated-file evidence and cache hit/key where available.

## Compatibility and receipts

The private/public compatibility fingerprint includes the schema-v5 treatment contract and numeric bounds. Public execution retains schema-v4 compatibility only for already-existing immutable recovery requests.

A schema-v5 verified result receipt records the selected logical slot and executed treatment. Finalization fails closed if runtime evidence differs from the immutable request. Those verified receipts become the private history ChatGPT reads during future planning.

## Subtitle safety and fallback

Caption readability remains mandatory across the used treatment. Runtime may apply the bounded caption-protection treatment already defined by rendering policy, but planning should prefer a better background rather than depend on excessive darkening.

Logical fallback is frozen primary then frozen backup only. The public runtime never substitutes an unrelated third logical asset. Physical rendition fallback within the same logical slot is allowed only when it still satisfies the same production suitability rules and executes that slot's frozen treatment.

If the selectable pool is insufficient, **both Daily and Ad-hoc replenish through the same reviewed licensed readiness path before authoring a ranked pool**. Neither planner may silently reuse retired backgrounds merely because historical recovery can still resolve them.

## Fail-closed principle

If shared media readiness is not `PASS`, stop before ranked-pool authoring and replenish. If ChatGPT cannot author a safe background/treatment contract after readiness passes, reject or repair the candidate before committing a ranked pool. If private hard validation later rejects the candidate, promotion moves to the next already-ranked reserve. Validation must never silently repair the candidate.
