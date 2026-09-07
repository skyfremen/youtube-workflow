# Wacky Insights Daily Planner Instructions

These instructions are the canonical policy for the Wacky Insights daily 24-Short planner.

## Scope and plan date

This is a DAILY PLANNING job, not a publishing job. The planner runs at 20:00 Asia/Singapore and MUST create the plan for the NEXT Singapore calendar day, not the current day.

The planner may write only:

- `youtube-shorts-bot/content/plans/YYYY-MM-DD.json`
- `youtube-shorts-bot/media-library/backgrounds.json` when adding or updating verified background assets
- `youtube-shorts-bot/media-library/music.json` when adding or updating verified music assets

The planner must NOT modify `youtube-shorts-bot/content/latest.json`, archive files, publishing workflows, rendering code, queue state, or YouTube itself. Never upload a video, never use `force_reupload`, and never publish directly.

## Inputs to read first

Before generating ideas, read:

1. Recent files under `youtube-shorts-bot/content/archive/`.
2. Latest existing plan files under `youtube-shorts-bot/content/plans/` when present.
3. `youtube-shorts-bot/analytics/latest.json` when present.
4. `youtube-shorts-bot/media-library/backgrounds.json`.
5. `youtube-shorts-bot/media-library/music.json`.

Use analytics as directional evidence, especially subscribers per 1,000 views, views, average view duration, likes and shares. Do not overfit weak or sparse analytics. Preserve exploration and category diversity.

## Content goal

Optimize toward the first 1,000 subscribers.

Generate at least 60 distinct relatable-humor candidates spanning broad everyday categories such as COUPLE, DATING, MARRIAGE, FRIENDS, PARENTS, KIDS, MEN, WOMEN, FOOD, SLEEP, WORK, SCHOOL, SHOPPING, PHONE, PETS, TRAVEL, EVERYDAY LIFE and HUMAN BEHAVIOR.

Every selected Short must be immediately relatable, easy to understand, and funny. Target roughly 10-15 seconds with a concise setup and punchline/reveal.

Avoid repeating recent topics, scenarios, punchline patterns, mechanisms, categories, background assets and music assets.

Score candidates using:

- relatability: 30%
- funny: 25%
- hook: 15%
- originality: 15%
- clarity: 10%
- visual potential: 5%

Reject candidates with weighted total below 75. Select exactly 24 final Shorts with meaningful diversity.

## Publishing-slot intent

The resulting plan contains slots 1 through 24. The queue publisher maps them to the plan date in Asia/Singapore as follows:

- slot 1 = 00:00
- slot 2 = 01:00
- continue hourly
- slot 24 = 23:00

The planner must not attempt to schedule YouTube itself; it only creates the validated plan.

## Cache-first media sourcing

The media library is the first source for BOTH background video and music.

For every Short, derive a structured semantic requirement from the actual joke, including scenario, actions, setting, people count/context, time context, visual tone, humor mechanism, mood, energy, required visual cues and incompatible/avoid conditions.

Search active cached assets using tags plus semantic descriptions. Do not select an asset merely because its broad category matches.

A cached background is eligible only if the planner calculates a background match score >= 85 for that exact Short. A cached music track is eligible only if the planner calculates a music match score >= 85 for that exact Short.

Recommended background scoring:

- exact scenario: 35%
- action match: 25%
- setting/people context: 15%
- visual requirements: 15%
- tone/context: 10%

Recommended music scoring:

- humor mechanism: 30%
- mood: 30%
- energy/intensity: 15%
- scenario suitability: 15%
- conflict/avoid check: 10%

Any explicit `avoid_for` conflict disqualifies the asset regardless of score.

## Plan-ready assets and variety

`verified` and `plan_ready` mean different things:

- `verified=true` means the source/license is verified.
- `plan_ready=true` means the asset is verified, active, and all metadata required for immediate use in a valid plan is already known.
- For legacy cache entries where `plan_ready` is missing, the planner MUST derive readiness from the verified metadata instead of automatically rejecting the asset. A legacy asset is implicitly plan-ready only when it is `verified=true`, `status="active"`, has non-empty direct URL, source page, license and semantic description, and has no missing attribution identity that is actually required by the license.

For backgrounds, explicit or implicit plan readiness requires a non-empty direct URL, source page, license and semantic description. `creator` is required only when `attribution_required=true`; otherwise a verified `creator=null` does not block planning.

For music, explicit or implicit plan readiness requires a non-empty artist, direct URL, source page, license and semantic description. If a provider/license genuinely does not expose an artist and attribution is not required, a verified null artist may be accepted only when the source page itself has been rechecked during that run; never invent an artist.

Prefer explicitly `plan_ready=true` assets, then implicitly plan-ready legacy assets, then never-used assets, least recently used assets, lower usage count, and stronger semantic match. Do not sacrifice semantic fit for novelty or plan readiness.

A verified asset that is not explicitly or implicitly plan-ready may still be used, but the planner must revisit the source page and fill the missing required metadata before placing it in the daily plan. Never invent missing metadata.

Primary and backup assets for the same Short must be different URLs and independently score >=85.

Across the entire 24-Short plan, ALL primary and backup background URLs must be unique. ALL primary and backup music URLs must also be unique. A backup used for one Short cannot be a primary or backup for another Short in the same batch. This means the plan requires 48 distinct video URLs and 48 distinct music URLs.

## Fresh web sourcing

Search the public web fresh only when the media cache cannot provide a sufficiently strong primary or backup match, when the best cache match is not plan-ready and required metadata cannot be verified, or when cached assets are stale/inactive/dead.

Use reputable copyright-safe sources. Current approved sources include Pexels for video and Free Safe Music for music. Do not use Mixkit/assets.mixkit.co. Do not use vintage/classical/ragtime/Wikimedia recordings merely because they are public domain.

Verify the source/license before adding an asset. For music, verify monetized/commercial use and Content ID safety where the provider states it. For video, verify that the source permits free/commercial creator use.

For primary media, prefer exact direct-download URLs that resolve to the expected media type. Backup media uses the repository's lazy runtime preflight/failover behavior.

## Growing the media library

Whenever a daily planner web search discovers a NEW verified source asset that is usable for Wacky Insights, add it to the appropriate media-library JSON during the same planning run.

Rules:

- Deduplicate by `id`, canonical source page and direct URL.
- Never overwrite a different asset with the same title.
- Populate the semantic schema as completely as evidence allows.
- Never invent creator, duration, orientation, BPM or other metadata. Use `null` when not verified.
- Set `verified=true` only after source/license verification.
- Set `last_verified_at` to the verification timestamp.
- Set `status="active"` only when the asset is currently usable.
- Set `plan_ready=true` when the asset meets the explicit readiness rules above; otherwise set it to `false`. Legacy entries without the field may be treated as implicitly ready only under the legacy derivation rule above.
- New assets start with `usage_count=0` and null usage fields unless selected in the same plan.
- If selected, update `usage_count`, `last_used_at` and `last_used_short_id`.
- If a URL/license check fails, mark the asset `status="inactive"` or `verified=false`; do not select it.
- Do not add web-search results that were not actually verified.
- After changing either media JSON, ensure it passes `youtube-shorts-bot/validate_media_library.py`.

The library may grow without an item cap.

## Schema expectations

Background entries should preserve the existing expanded schema including id, type, title, description, direct/source URLs, source, creator, license/commercial flags, semantic tags/actions/settings/context, visual metadata, semantic description, verification metadata, `plan_ready` when newly added or updated, usage metadata and status.

Music entries should preserve the existing expanded schema including id, type, title, artist, direct/source URLs, source, license/commercial/monetization/Content-ID flags, semantic mood/suitability fields, energy/tempo/intensity/comedy style, vocal flags, semantic description, verification metadata, `plan_ready` when newly added or updated, usage metadata and status.

Do NOT store a permanent per-Short `match_score` in the media library. Match score must be recalculated against each new Short.

## Final plan requirements

Create exactly 24 final items with slots 1 through 24 and `target_count: 24`. `candidates_generated` must be at least 60. Preserve all fields required by the repository's current daily-plan validators, including semantic match fields for primary and backup background/music assets.

Channel handle: `@WACKYINSIGHTS`.

CTA: `DOUBLE TAP TO AGREE`.

Every title must contain `#Shorts` and be <=100 characters.

Commit exactly one daily plan file for the intended NEXT-DAY plan date per planner commit. The same commit may also include media-library additions or usage updates. Do not change multiple plan dates in one planner commit.

## Validation

After committing, verify the exact `Validate daily Shorts plan` GitHub Actions run for that commit. The validation workflow resolves the plan date from the exact changed plan file, not from wall-clock date.

If validation fails due to content/plan/media metadata, correct and retry up to 3 times. Stop and report rather than repeatedly retrying infrastructure, permission, credential, or GitHub service failures.
