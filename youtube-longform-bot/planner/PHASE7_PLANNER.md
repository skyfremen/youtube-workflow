# Wacky Insights Phase 7 — ChatGPT Planner Contract

This file is the reusable source of truth for ChatGPT when creating a new long-form plan.

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

Write the planner result to `content/phase7-plan.json` using the existing file as the canonical example. Do not modify Shorts files.
