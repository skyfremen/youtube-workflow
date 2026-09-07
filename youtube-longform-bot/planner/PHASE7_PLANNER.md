# Wacky Insights Phase 7 — ChatGPT Planner Contract

This file is the reusable source of truth for ChatGPT when creating a new long-form plan.

## Operating model

ChatGPT is the planning/intelligence layer. GitHub Actions is the deterministic production layer.

For an ad-hoc planning request, ChatGPT must:

1. Read this file.
2. Read `assets/design-system.json`.
3. Read `assets/registry.json` and prefer reusable existing assets.
4. Read the most recent long-form planning files when useful to avoid repetitive topics, story structures and visual patterns.
5. Generate the script + storyboard JSON.
6. Generate a plain-text storyline summary for human review.
7. Commit both files to the repository.
8. STOP. Do not trigger the render workflow until the user explicitly approves the story.

There is intentionally no scheduled automation in Phase 7 yet.

## Review gate

Every generated `content/phase7-plan.json` must contain:

```json
"approval": {
  "status": "review_required",
  "approved_by": null,
  "approved_at": null
}
```

The planning step must never self-approve a plan.

When the user explicitly says to create/render the video, ChatGPT may change the status to `approved`, set `approved_by` to `user`, add an ISO-8601 approval timestamp, and then trigger the GitHub workflow if workflow-dispatch tooling is available. If dispatch is unavailable, leave the approved plan ready for the user to run manually.

The GitHub workflow must refuse to render a plan whose approval status is not `approved`.

## Human-readable summary

Together with `content/phase7-plan.json`, write:

`content/phase7-summary.txt`

The summary is for quick human review and must be understandable without reading JSON. Include:

- Working title
- Approximate intended length
- One-paragraph story overview
- Scene-by-scene storyline in plain English
- Main punchline/payoff
- Existing assets expected to be reused
- New assets expected to be needed/generated
- A final line: `STATUS: AWAITING APPROVAL — no video has been rendered.`

Do not include implementation details or raw JSON in the summary.

## Goal

Given a topic, produce an original relatable-humor explainer script and storyboard JSON that can be rendered by the long-form pipeline.

## Required planning order

1. Write the narration as a coherent story with a hook, explanation, visual contrast or escalation, and punchline/payoff.
2. Break the narration into environment-led scenes.
3. For every visual beat, describe the visual need before choosing an asset.
4. Search `assets/registry.json` conceptually first and prefer a strong reusable match.
5. If no asset is semantically strong enough, add an `asset_needs[].generation` specification for a professional reusable SVG asset.
6. Generated assets must use `assets/design-system.json` and must be general enough for future videos.
7. Keep infographic information as overlays inside active scenes whenever possible.
8. Use relative `at_pct` beat positions. Kokoro narration is the master clock; exact seconds are generated later.

## Hard visual rules

- Never design scenes as PowerPoint slides.
- Avoid title + cards, presentation grids, static comparison panels, and paragraph blocks.
- Prefer characters, environments, props, reactions, object state changes, camera motion, labels attached to action, and short infographic overlays.
- Captions: maximum 7 words.
- Aim for a visible change approximately every 1.0–1.5 seconds.
- Maintain Wacky Insights character proportions, palette, lighting, stroke treatment and soft-depth vector style.

## Asset matching

Each asset need must contain:

- `need_id`
- `category`: character, environment, prop, or infographic
- specific `description`
- at least 3 semantic `tags`
- `generation` only when no strong existing match should be used

The workflow resolves these against `assets/registry.json`. The current match threshold is controlled by `planner.asset_match_threshold`.

## Generated asset requirements

A generation specification must contain:

- stable reusable `asset_id`
- approved `template` or future professional generator type
- descriptive reusable `description`
- semantic `tags`
- `reusable: true`

Generated assets are not persisted merely because they were created. The workflow validates them and successfully renders the video first. Only then are new assets committed into the permanent registry.

## Storyboard requirements

- narration-first timing
- 24 fps for MVP tests
- minimum 5 scenes for Phase 7 validation
- minimum 4 visual beats per scene
- environment + character in every current Phase 7 scene
- `visuals` contains positioned reusable assets
- `overlays` contains only short action-connected labels
- `beats[].at_pct` is between 0 and 1 and chronological

## Output

Write both:

- `content/phase7-plan.json`
- `content/phase7-summary.txt`

Do not modify Shorts files. Do not trigger a render during the planning/review step.