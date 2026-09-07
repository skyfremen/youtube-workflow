# Wacky Insights Series Shorts Planner Instructions

This file is the canonical policy for the isolated `youtube-shorts-series-bot` experiment. It is intentionally separate from `youtube-shorts-bot` and MUST NOT modify, publish from, or write state into the existing production Shorts bot.

## Isolation

All reads/writes for this experiment stay under `youtube-shorts-series-bot/` unless explicitly stated otherwise.

The planner may write only:

- `youtube-shorts-series-bot/content/plans/YYYY-MM-DD.json`
- `youtube-shorts-series-bot/media-library/backgrounds.json` when adding/updating verified background assets
- `youtube-shorts-series-bot/media-library/music.json` when adding/updating verified music assets

Do not modify `youtube-shorts-bot/`, its plans, archives, workflows, queue state, analytics or YouTube publishing state. Existing production workflows continue to target only `youtube-shorts-bot`.

## Goal

Optimize toward subscriber growth, especially subscribers per 1,000 views, while preserving relatability, humor and watchability.

Generate at least 60 distinct relatable-humor candidates and select exactly 24 Shorts. Use broad categories such as COUPLE, DATING, MARRIAGE, FRIENDS, PARENTS, KIDS, MEN, WOMEN, FOOD, SLEEP, WORK, SCHOOL, SHOPPING, PHONE, PETS, TRAVEL, EVERYDAY LIFE and HUMAN BEHAVIOR.

Every Short must still contain a complete joke. Never withhold the punchline merely to force a viewer to watch the next part.

## Series-first experiment

Target 12 to 16 of the 24 Shorts as genuine multi-part series content and keep the remaining 8 to 12 as standalone controls.

A series is eligible only when the core premise naturally supports at least 3 genuinely different episodes. Good examples include:

- Things couples never agree on
- Things every office worker understands
- Things parents always say
- Things people do when their phone hits 1%
- Things that happen every time you travel

Do not create a series when Part 2 would merely repeat the same joke with slightly different wording.

Each series item must include these fields inside `content`:

- `series_id`: stable slug shared by every part in the same series
- `series_title`: human-readable recurring series name
- `part_number`: integer starting at 1
- `part_total`: integer >= 3
- `next_part_slot`: slot number of the next part, or null for the final part
- `series_role`: `series` or `standalone`

Standalone Shorts must use:

- `series_id: null`
- `series_title: null`
- `part_number: null`
- `part_total: null`
- `next_part_slot: null`
- `series_role: "standalone"`

## CTA rules

For a non-final series part, CTA must be exactly:

`FOLLOW FOR PART N`

where N is the next part number. Example: Part 1 uses `FOLLOW FOR PART 2`; Part 2 uses `FOLLOW FOR PART 3`.

For the final part of a series, CTA must be one of:

- `FOLLOW FOR MORE`
- `DOUBLE TAP TO AGREE`

For standalone Shorts, CTA remains:

`DOUBLE TAP TO AGREE`

Never use `FOLLOW FOR PART N` unless that next part exists in the same 24-item plan and `next_part_slot` points to it.

## Series spacing

Do not place consecutive parts back-to-back. Prefer roughly 4 to 8 hours between parts so viewers have a reason to return later in the day.

Each part must independently make sense to a viewer who did not see the earlier part. Mention the series premise naturally in the setup/title when needed.

## Candidate scoring

Keep the normal quality score:

- relatability: 30%
- funny: 25%
- hook: 15%
- originality: 15%
- clarity: 10%
- visual potential: 5%

Reject weighted total below 75.

Additionally score `series_potential` from 0 to 100 for candidate grouping. Prefer series candidates >=80. Series potential considers:

- ability to support at least 3 distinct episodes
- recognisable recurring premise
- natural curiosity for another part
- low risk of repetitive punchlines
- broad subscriber appeal

`series_potential` is experimental metadata and does not replace the normal quality total.

## Analytics use

Read `youtube-shorts-series-bot/analytics/latest.json` when present. Compare subscriber conversion between:

- series parts using `FOLLOW FOR PART N`
- final series parts
- standalone controls using `DOUBLE TAP TO AGREE`

Prioritise `subscribers_per_1000_views` as the primary experiment metric, with views, average view duration, likes and shares as supporting signals. Do not overfit sparse samples.

## Inputs

Before planning, read:

1. Recent files under `youtube-shorts-series-bot/content/archive/`
2. Latest plans under `youtube-shorts-series-bot/content/plans/`
3. `youtube-shorts-series-bot/analytics/latest.json` when present
4. `youtube-shorts-series-bot/media-library/backgrounds.json`
5. `youtube-shorts-series-bot/media-library/music.json`

Avoid repeating recent topics, scenarios, punchline patterns, series premises, background assets and music assets.

## Slots

Create exactly 24 items with slots 1 through 24. Slot 1 maps to 00:00 Asia/Singapore, slot 2 to 01:00, through slot 24 at 23:00.

The planner itself does not upload or schedule YouTube videos.

## Cache-first media sourcing

Use the copied media cache first for both background video and music. Every primary and backup background/music choice must independently match the exact joke at >=85.

Primary and backup URLs for the same Short must differ. Across all 24 Shorts, all primary and backup background URLs must be unique and all primary and backup music URLs must be unique, requiring 48 distinct background URLs and 48 distinct music URLs.

Any explicit `avoid_for` conflict disqualifies an asset regardless of score.

Use the existing verified/plan-ready rules from the copied media library. Background creator is mandatory only when attribution is required. Do not invent missing metadata.

Search fresh only when the cache cannot provide a sufficiently strong verified primary or backup. Current approved sources remain Pexels for video and Free Safe Music for music. Do not use Mixkit/assets.mixkit.co.

When new verified media is discovered, add it only to the isolated media-library JSON files under `youtube-shorts-series-bot/`.

## Final plan requirements

- `plan_date` matches the target date
- `target_count: 24`
- `candidates_generated >= 60`
- exactly 24 slots numbered 1 through 24
- 12 to 16 series parts total
- at least 3 distinct series
- each series contains at least 3 parts
- each non-final part has a valid next part in the same plan
- all titles include `#Shorts` and are <=100 characters
- channel handle remains `@WACKYINSIGHTS`
- preserve all existing media metadata and semantic match fields required by the copied validators

## Validation and safety

Use only the validators inside `youtube-shorts-series-bot` for this experiment. Do not trigger the existing `Validate daily Shorts plan` or `Publish daily Shorts queue` production workflows for this folder.

No automatic publishing workflow is enabled for `youtube-shorts-series-bot` yet. This is deliberate so the experiment remains isolated until its plan/output has been reviewed.
