# Wacky Insights Long-form — Ad-hoc ChatGPT Planning Prompt

Use this file as the entry point for an ad-hoc or scheduled ChatGPT planning run.

## Mission

Create one new Wacky Insights long-form explainer plan for **human review only**.

The channel promise is non-negotiable:

**Every video must combine meaningful educational value with humour.**

Target reaction:

> “I actually learned something — and that was funny.”

The active visual system is **`wacky_insights_v2`**.

The visual direction is also non-negotiable:

- original professional editorial 2D explainer art
- scene-first, not slide-first
- environment-led storytelling
- rounded readable characters and reusable props
- integrated educational graphics rather than detached presentation boards
- purposeful motion
- seamless but visually distinct scene transitions
- no blink-like cuts between nearly identical shots

## Read these files first

Read and follow, in this exact order:

1. `youtube-longform-bot/planner/CHANNEL_PERSONALITY.md`
2. `youtube-longform-bot/planner/PHASE7_PLANNER.md`
3. `youtube-longform-bot/assets/design-system.json`
4. `youtube-longform-bot/assets/registry.json`
5. recent long-form plan/summary files under `youtube-longform-bot/content/` when useful for avoiding repetition

Do not rely on chat memory when the repo instructions or asset registry can answer the question.

## Topic selection

If the user supplied a topic, use it unless it cannot support a useful, accurate educational explanation plus humour.

If no topic was supplied, choose one original, broadly relatable everyday explainer topic with:

- an immediate “why/how does this happen?” hook
- real explanatory depth
- clear visual storytelling opportunities
- natural humour
- a memorable payoff

Avoid repeating recent topics, central mechanisms, punchlines, visual structures, shot grammar, or the same environment/character combination when better alternatives exist.

## Before writing the script

Define and include in the JSON:

1. `style_id`: `wacky_insights_v2`
2. **Learning promise** — one sentence describing what the viewer will understand.
3. **Central question** — the mystery being answered.
4. **Educational points** — normally 2–4 meaningful ideas that explain the answer.
5. **Humour strategy** — devices that fit naturally, including any recurring gag/callback.
6. **Final payoff** — closing joke/callback plus clear takeaway.
7. **Shot/transition strategy** — how scenes remain seamless while true scene cuts are visually distinct.

If the topic does not have at least two meaningful educational points, choose a stronger angle/topic rather than padding with trivia.

## Script requirements

Write a coherent story, not a listicle or school essay.

Prefer this arc:

- hook with a familiar or weird situation
- humorous escalation
- establish the question
- explain the mechanism step by step
- use examples/contrasts/mini-demonstrations
- reveal a surprising implication
- callback to the opening
- finish with both a punchline and a useful takeaway

Narration should sound conversational, intelligent, playful and easy to follow. Use plain English and concrete examples.

Avoid dry lecture language, filler, repeated explanations, jargon without explanation, fake certainty, and generic intros such as “Today we are going to discuss…”.

## Educational standard

The video must teach something real. Prefer WHY/HOW explanations over isolated facts.

For scientific, psychological, medical, historical, financial, numerical, disputed, or other accuracy-sensitive claims, verify before presenting them strongly. Preserve uncertainty where appropriate. Do not invent causal mechanisms or overstate correlations.

## Humour standard

Humour should appear throughout the story, not just in the last line.

Prefer relatable observations, visual exaggeration, absurd comparisons, object/personification gags, escalation, deadpan labels, callbacks, reactions and visual irony.

Avoid mean-spirited humour, overly childish jokes, stale meme dependence, obscure references, or jokes that damage the educational point.

## Visual planning standard

Do not create PowerPoint-like scenes.

Educational graphics should usually live **inside an active environment** as animated overlays, meters, arrows, labels, cause-and-effect motion, screens, boards, visual metaphors or object transformations.

Most scenes should contain active characters, props and environments. The visual should help explain the idea rather than merely decorate narration.

Aim for a meaningful visual change roughly every 1.0–1.5 seconds in MVP content.

## Scene transition standard — HARD RULE

Transitions must feel seamless, but a true scene change must look intentionally different.

If the next shot has nearly the same background, framing and focal action as the previous shot, it should usually remain part of the same scene.

Use same-scene continuity techniques instead:

- camera push/pan/follow
- reframe
- close-up
- insert/object shot
- reaction shot
- new focal object
- prop-state change
- overlay beat
- character movement

If a new scene keeps the same environment, change at least two of: framing, camera angle, focal subject, subject grouping, prop state, action emphasis, story emphasis.

Avoid cuts that look like the video blinked.

Prefer meaningful cuts to clearly different environments, strong reframes, match-action cuts, insert cuts, reaction cuts, object wipes and motivated camera changes.

## Asset intelligence

For every visual need:

1. Describe subject, purpose, context, viewpoint and required actions/states.
2. Search `assets/registry.json` conceptually for a strong fit.
3. Prefer reuse only when genuinely appropriate.
4. Do not force weak v1 assets into a v2 scene merely because the category matches.
5. If no strong fit exists, add an `asset_needs[].generation` specification for a **professional reusable `wacky_insights_v2` asset**.

Generated assets must be reusable, contextually appropriate, professionally art-directed and clearly readable. They must not look like clipart, crude procedural drawings, childish doodles or generic presentation art.

## Required review artifacts

Generate and commit exactly these review artifacts:

- `youtube-longform-bot/content/phase7-plan.json`
- `youtube-longform-bot/content/phase7-summary.txt`

The JSON must contain:

- `style_id: wacky_insights_v2`
- complete narration
- storyboard/scenes
- per-scene `shot` metadata
- visual beats
- asset needs
- `learning_promise`
- `central_question`
- `educational_points`
- `channel_personality` metadata
- `humour_strategy`
- approval block

The approval block must be:

```json
"approval": {
  "status": "review_required",
  "approved_by": null,
  "approved_at": null
}
```

## Human-readable summary

The plain-text summary must make it easy for the user to decide whether to produce the video.

Include:

- working title
- approximate intended duration
- learning promise
- one-paragraph story overview
- scene-by-scene storyline in plain English
- main educational points
- humour approach / recurring gag
- final punchline/payoff
- scene/location variety at a glance
- existing assets expected to be reused
- new assets expected to be generated
- final line exactly:

`STATUS: AWAITING APPROVAL — no video has been rendered.`

The summary should focus on the story and what the viewer will learn, not implementation details.

## Final self-check before committing

Do not commit until all are true:

- the viewer will learn at least two meaningful things
- the educational mechanism is understandable and supportable
- humour is integrated throughout
- there is a strong hook
- there is a clear payoff/callback
- visuals actively explain the topic
- scenes do not resemble PowerPoint slides
- scene transitions do not create blink-like cuts
- repeated environments are treated as continuity or strongly reframed
- shot scale and framing vary enough to feel visually alive
- assets are appropriate, reusable and professional
- the script contains no runtime-padding filler

If any condition fails, revise first.

## Stop condition

Do not render the video.
Do not trigger GitHub Actions.
Do not generate Kokoro narration.
Do not approve the plan.
Do not modify Shorts files.

Stop after committing the JSON and summary, then present the storyline summary to the user and ask whether they want to create the video.
