# Wacky Insights Daily Planner Instructions

These instructions are the canonical policy for the Wacky Insights daily 24-Short planner.

## Scope and plan date

This is a DAILY PLANNING job, not a publishing job. The planner runs at 20:00 Asia/Singapore and MUST create the plan for the NEXT Singapore calendar day.

The planner may write only:

- `youtube-shorts-bot/content/plans/YYYY-MM-DD.json`
- `youtube-shorts-bot/media-library/backgrounds.json` when adding/updating verified background assets
- `youtube-shorts-bot/media-library/music.json` when adding/updating verified music assets

Do not modify `content/latest.json`, archive files, rendering code, queue state, workflows, or YouTube directly.

## Inputs

Before planning, read recent archive files, recent plans, `analytics/latest.json` when present, and both media-library JSON files. Use analytics directionally, with `subscribers_per_1000_views` as the primary growth signal and views, average view duration, likes and shares as supporting evidence.

## Content goal

Optimize toward the first 1,000 subscribers.

Generate at least 60 distinct relatable-humor candidates across broad everyday categories such as COUPLE, DATING, MARRIAGE, FRIENDS, PARENTS, KIDS, MEN, WOMEN, FOOD, SLEEP, WORK, SCHOOL, SHOPPING, PHONE, PETS, TRAVEL, EVERYDAY LIFE and HUMAN BEHAVIOR.

Every Short must be immediately understandable, broadly relatable and funny, with a complete setup and punchline. Never withhold the payoff merely to force a viewer to watch another part.

Score candidates using:

- relatability: 30%
- funny: 25%
- hook: 15%
- originality: 15%
- clarity: 10%
- visual potential: 5%

Reject weighted totals below 75.

## Series-first subscriber experiment

Use recurring series as the default growth experiment while retaining standalone controls.

For each 24-Short plan:

- 12 to 16 Shorts must be genuine series parts.
- Keep 8 to 12 standalone controls.
- Use at least 3 distinct series.
- Every series must contain at least 3 genuinely different parts.
- Prefer `series_potential >= 80` for series candidates.
- Do not create repetitive pseudo-series where each part is merely the same joke reworded.

Each content item must include:

- `series_role`: `series` or `standalone`
- `series_id`
- `series_title`
- `part_number`
- `part_total`
- `next_part_slot`
- `series_potential`

For standalone Shorts, `series_id`, `series_title`, `part_number`, `part_total` and `next_part_slot` must be null. `series_potential` must still be numeric from 0 to 100.

For series Shorts:

- `series_id` is a stable slug shared by the series.
- `series_title` is the persistent badge title.
- `part_number` starts at 1.
- `part_total >= 3`.
- Non-final parts must point to the next actual slot with `next_part_slot`.
- Prefer roughly 4 to 8 hours between parts; never place consecutive parts back-to-back.
- Each part must make sense even if the viewer missed earlier parts.

CTA rules:

- Non-final series part: exactly `FOLLOW FOR PART N`, where N is the next part number.
- Final series part: `FOLLOW FOR MORE` or `DOUBLE TAP TO AGREE`.
- Standalone: exactly `DOUBLE TAP TO AGREE`.

Never use `FOLLOW FOR PART N` unless that next part exists in the same plan.

The production renderer displays a persistent `<SERIES TITLE> • PART X/Y` badge directly above `DID YOU KNOW?` for series items. Standalone Shorts show no badge.

## Slots

Create exactly 24 items with slots 1 through 24. Slot 1 maps to 00:00 Asia/Singapore, slot 24 to 23:00, hourly in between.

## Cache-first media sourcing

The media library is the first source for BOTH background video and music.

For each Short, derive exact semantic requirements from the joke. Cached primary and backup backgrounds must each score >=85 for that exact Short. Cached primary and backup music must each independently score >=85. Any `avoid_for` conflict disqualifies an asset.

Primary and backup URLs for one Short must differ. Across the full 24-item batch all primary and backup background URLs must be unique and all primary and backup music URLs must be unique, requiring 48 distinct background URLs and 48 distinct music URLs.

`verified=true` and `plan_ready=true` are separate concepts. Prefer explicit `plan_ready=true`, then implicitly plan-ready verified legacy assets. Legacy backgrounds are implicitly ready only when verified, active, and direct URL/source page/license/semantic description are present, with creator required only when attribution is required. Legacy music requires verified active metadata including artist, direct URL, source page, license and semantic description; a verified null artist is allowed only when attribution is not required and the source page was rechecked during that run.

Search the public web only when cache cannot provide a strong valid primary/backup pair or cached metadata is stale/incomplete. Approved sources remain Pexels for video and Free Safe Music for music. Do not use Mixkit/assets.mixkit.co. Verify license/commercial use before adding new media. Add newly verified assets only to the production media library, deduplicated and with honest metadata. Never invent creator, artist, duration, BPM or other facts.

After media-library changes, run `youtube-shorts-bot/validate_media_library.py`.

## Final plan requirements

- `plan_date` matches the intended next Singapore date.
- `target_count: 24`.
- `candidates_generated >= 60`.
- Exactly 24 slots numbered 1 through 24.
- 12 to 16 total series parts.
- At least 3 distinct series.
- Each series has at least 3 parts.
- Every non-final series part points to its actual next part.
- Every title contains `#Shorts` and is <=100 characters.
- Channel handle remains `@WACKYINSIGHTS`.
- Preserve all existing required semantic match and backup-media metadata.
- Commit exactly one daily plan date per planner commit, with optional media-library updates in the same commit.

## Validation

After committing, verify the exact `Validate daily Shorts plan` workflow run for that commit. Validation must pass the base queue schema, backup metadata, media library checks, and the production series-structure validator.

If content/plan/media validation fails, correct and retry up to 3 times. Stop and report infrastructure, permission, credential or GitHub service failures rather than retrying blindly.
