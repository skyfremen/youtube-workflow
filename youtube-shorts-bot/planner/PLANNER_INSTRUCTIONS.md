# Wacky Insights Daily Planner Instructions

These instructions are the canonical policy for the Wacky Insights daily 20-Short planner.

## Scope

This is a DAILY PLANNING job, not a publishing job.

The planner may write only:

- `youtube-shorts-bot/content/plans/YYYY-MM-DD.json`
- `youtube-shorts-bot/media-library/backgrounds.json` when adding or updating verified background assets
- `youtube-shorts-bot/media-library/music.json` when adding or updating verified music assets

The planner must NOT modify `youtube-shorts-bot/content/latest.json`, archive files, publishing workflows, rendering code, queue state, or YouTube itself. Never upload a video, never use `force_reupload`, and never publish directly.

Use the current Asia/Singapore calendar date as the plan date.

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

Generate at least 50 distinct relatable-humor candidates spanning broad everyday categories such as COUPLE, DATING, MARRIAGE, FRIENDS, PARENTS, KIDS, MEN, WOMEN, FOOD, SLEEP, WORK, SCHOOL, SHOPPING, PHONE, PETS, TRAVEL, EVERYDAY LIFE and HUMAN BEHAVIOR.

Every selected Short must be immediately relatable, easy to understand, and funny. Target roughly 10-15 seconds with a concise setup and punchline/reveal.

Avoid repeating recent topics, scenarios, punchline patterns, mechanisms, categories, background assets and music assets.

Score candidates using:

- relatability: 30%
- funny: 25%
- hook: 15%
- originality: 15%
- clarity: 10%
- visual potential: 5%

Reject candidates with weighted total below 75. Select exactly 20 final Shorts with meaningful diversity.

## Cache-first media sourcing

The media library is the first source for BOTH background video and music.

### Step 1 - Search the cache first

For every Short, derive a structured semantic requirement from the actual joke, including as applicable:

- scenario
- actions
- setting
- people count/context
- time context
- visual tone
- humor mechanism
- mood
- energy
- required visual cues
- incompatible/avoid conditions

Search active cached assets using tags plus semantic descriptions. Do not select an asset merely because its broad category matches.

A cached background is eligible only if the planner calculates a background match score >= 85 for that exact Short.

A cached music track is eligible only if the planner calculates a music match score >= 85 for that exact Short.

Recommended background scoring dimensions:

- exact scenario: 35%
- action match: 25%
- setting/people context: 15%
- visual requirements: 15%
- tone/context: 10%

Recommended music scoring dimensions:

- humor mechanism: 30%
- mood: 30%
- energy/intensity: 15%
- scenario suitability: 15%
- conflict/avoid check: 10%

Any explicit `avoid_for` conflict disqualifies the asset regardless of score.

### Step 2 - Prefer plan-ready assets, then variety

`verified` and `plan_ready` mean different things:

- `verified=true` means the source/license is verified.
- `plan_ready=true` means the asset is verified, active, and all metadata required for immediate use in a valid plan is already known.
- A missing `plan_ready` field MUST be treated as `false`.

For backgrounds, `plan_ready=true` requires at minimum a non-empty creator, direct URL, source page, license and semantic description.

For music, `plan_ready=true` requires at minimum a non-empty artist, direct URL, source page, license and semantic description.

Prefer `plan_ready=true` assets because they can be reused without revisiting the source page. A `verified=true` but `plan_ready=false` asset may still be used, but the planner must revisit the source page and fill the missing required metadata before placing it in the daily plan. Never invent missing metadata.

Among eligible assets scoring >= 85, prefer:

1. plan-ready assets,
2. never-used assets,
3. least recently used assets,
4. lower usage count,
5. stronger semantic match.

Do not sacrifice semantic fit for novelty or plan readiness. Exact content match remains the highest priority.

Primary and backup assets for the same Short must be different URLs and independently score >= 85.

Across the entire 20-Short plan, ALL primary and backup background URLs must be unique. ALL primary and backup music URLs must also be unique. A backup used for one Short cannot be a primary or backup for another Short in the same batch.

### Step 3 - Search the public web only when needed

Search the public web fresh only when the media cache cannot provide a sufficiently strong primary or backup match, when the best cache match is not plan-ready and required metadata cannot be verified, or when cached assets are stale/inactive/dead.

Use reputable copyright-safe sources. Current approved sources include Pexels for video and Free Safe Music for music. Do not use Mixkit/assets.mixkit.co. Do not use vintage/classical/ragtime/Wikimedia recordings merely because they are public domain.

Verify the source/license before adding an asset. For music, verify monetized/commercial use and Content ID safety where the provider states it. For video, verify that the source permits free/commercial creator use.

For primary media, prefer exact direct-download URLs that resolve to the expected media type. Backup media may use the existing lazy validation behavior where supported by the repository validators.

## Growing the media library every day

Whenever a daily planner web search discovers a NEW verified source asset that is usable for Wacky Insights, add it to the appropriate media-library JSON during the same planning run.

Rules for additions and updates:

- Deduplicate by `id`, canonical source page and direct URL.
- Never overwrite a different asset with the same title.
- Populate the expanded semantic schema as completely as evidence allows.
- Never invent creator, duration, orientation, BPM or other metadata. Use `null` when not verified.
- Set `verified=true` only after source/license verification.
- Set `last_verified_at` to the verification timestamp.
- Set `status="active"` only when the asset is currently usable.
- Set `plan_ready=true` only when the asset has all metadata needed for immediate daily-plan use; otherwise set it to `false`.
- New assets start with `usage_count=0` and null usage fields unless selected in the same plan.
- If selected in the same plan, increment `usage_count` and update `last_used_at` and `last_used_short_id`.
- If an existing cached asset is selected, update its usage metadata.
- If a URL/license check fails, mark the asset `status="inactive"` or `verified=false`; do not select it.
- Do not add web-search results that were not actually verified.
- After changing either media JSON, ensure it passes `youtube-shorts-bot/validate_media_library.py`.

The library is allowed to grow beyond the initial seed. There is no item cap.

## Background schema expectations

Each background entry should contain, where known:

- `id`
- `type`
- `title`
- `description`
- `direct_url`
- `source_page`
- `source`
- `creator`
- `license`
- `commercial_use`
- `attribution_required`
- `scene_tags`
- `categories`
- `actions`
- `setting`
- `people_count`
- `people_context`
- `time_context`
- `visual_tone`
- `camera_style`
- `usable_for_hooks`
- `avoid_for`
- `semantic_description`
- `orientation`
- `duration_seconds`
- `verified`
- `last_verified_at`
- `plan_ready`
- `usage_count`
- `last_used_at`
- `last_used_short_id`
- `status`

## Music schema expectations

Each music entry should contain, where known:

- `id`
- `type`
- `title`
- `artist`
- `direct_url`
- `source_page`
- `source`
- `license`
- `commercial_use`
- `monetization_allowed`
- `attribution_required`
- `content_id_safe`
- `mood_tags`
- `suitable_for`
- `suitable_for_mechanisms`
- `suitable_for_scenes`
- `energy`
- `tempo`
- `intensity`
- `comedy_style`
- `instrumental`
- `has_vocals`
- `avoid_for`
- `semantic_description`
- `duration_seconds`
- `verified`
- `last_verified_at`
- `plan_ready`
- `usage_count`
- `last_used_at`
- `last_used_short_id`
- `status`

Do NOT store a permanent per-Short `match_score` in the media library. Match score must be recalculated against each new Short.

## Final plan requirements

Create exactly 20 final items. Preserve all fields required by the repository's current daily-plan validators, including semantic match fields for primary and backup background/music assets.

Channel handle: `@WACKYINSIGHTS`.

CTA: `DOUBLE TAP TO AGREE`.

Every title must contain `#Shorts` and be <= 100 characters.

Commit exactly one daily plan file for the intended plan date per planner commit. The same commit may also include media-library additions or usage updates. Do not change multiple plan dates in one planner commit.

## Validation

After committing, verify the exact `Validate daily Shorts plan` GitHub Actions run for that commit. The validation workflow resolves the plan date from the exact changed plan file, not from the wall-clock date.

If validation fails due to content/plan/media metadata, correct and retry up to 3 times. Stop and report rather than repeatedly retrying infrastructure, permission, credential, or GitHub service failures.
