# Wacky Insights Long-form — Ad-hoc ChatGPT Planning Prompt

Use this file as the entry point for an ad-hoc or scheduled ChatGPT planning run.

## Mission

Create one new Wacky Insights long-form explainer plan for **human review only**.

The channel personality is non-negotiable:

**Every video must combine meaningful educational value with humour.**

The viewer should leave thinking:

> “I actually learned something — and that was funny.”

Do not create a video that is merely funny, merely informative, or merely trivia-driven.

## Read these files first

Read and follow, in this exact order:

1. `youtube-longform-bot/planner/CHANNEL_PERSONALITY.md`
2. `youtube-longform-bot/planner/PHASE7_PLANNER.md`
3. `youtube-longform-bot/assets/design-system.json`
4. `youtube-longform-bot/assets/registry.json`
5. Recent long-form plan/summary files under `youtube-longform-bot/content/` when useful for avoiding repetition

Do not rely on chat memory when the repo instructions or asset registry can answer the question.

## Topic selection

If the user supplied a topic, use it unless it cannot support a useful, accurate educational explanation plus humour.

If no topic was supplied, choose one original, broadly relatable everyday explainer topic with:

- an immediate “why does this happen?” hook
- real explanatory depth
- clear visual storytelling opportunities
- natural humour
- a memorable payoff

Avoid repeating recent topics, central mechanisms, punchlines, visual structures, or the same environment/character combination when better alternatives exist.

## Before writing the script

Define internally and then include in the JSON:

1. **Learning promise:** one sentence describing what the viewer will understand.
2. **Central question:** the mystery being answered.
3. **Educational points:** normally 2–4 meaningful ideas that explain the answer.
4. **Humour strategy:** the comedic devices that fit naturally, including any recurring gag/callback.
5. **Final payoff:** the closing joke/callback plus the clear takeaway.

If the topic does not have at least two meaningful educational points, choose a stronger angle/topic rather than padding with trivia.

## Script requirements

Write a coherent story, not a listicle or school essay.

Prefer this arc:

- hook with a familiar or weird situation
- humorous escalation
- clearly establish the question
- explain the mechanism step by step
- use examples/contrasts/mini-demonstrations
- reveal a surprising implication
- callback to the opening
- finish with both a punchline and a useful takeaway

Narration should sound conversational, intelligent, playful and easy to follow. Use plain English and concrete examples.

Avoid dry lecture language, filler, repeated explanations, jargon without explanation, fake certainty, and generic intros such as “Today we are going to discuss…”.

## Educational standard

The video must teach something real.

Prefer WHY/HOW explanations over isolated facts.

For scientific, psychological, medical, historical, financial, numerical, disputed, or other accuracy-sensitive claims, verify before presenting them strongly. Preserve uncertainty where appropriate. Do not invent causal mechanisms or overstate correlations.

## Humour standard

Humour should appear throughout the story, not just in the last line.

Prefer:

- relatable observations
- visual exaggeration
- absurd comparisons
- object/personification gags
- escalation
- deadpan labels
- callbacks
- visual irony

Avoid mean-spirited humour, overly childish jokes, stale meme dependence, obscure references, or jokes that damage the educational point.

## Visual planning standard

Do not create PowerPoint-like scenes.

Educational graphics should usually live **inside an active environment** as animated overlays, meters, arrows, labels, cause-and-effect motion, visual metaphors or object transformations.

Most scenes should contain active characters/props/environments. The visual should help explain the idea rather than merely decorate narration.

Aim for a meaningful visual change roughly every 1.0–1.5 seconds in MVP content.

## Asset intelligence

For every visual need:

1. Describe the required subject, purpose, context, viewpoint and actions.
2. Search `assets/registry.json` conceptually for a strong fit.
3. Prefer reuse when the fit is genuinely appropriate.
4. Do not reuse a weak asset merely because the category matches.
5. If no strong fit exists, add an `asset_needs[].generation` specification for a **professional reusable asset** following the design system.

Generated assets must be designed for future reuse where practical and must not look like clipart, crude procedural drawing, or generic presentation art.

## Required review artifacts

Generate and commit exactly these review artifacts:

- `youtube-longform-bot/content/phase7-plan.json`
- `youtube-longform-bot/content/phase7-summary.txt`

The JSON must contain:

- complete narration
- storyboard/scenes
- visual beats
- asset needs
- `learning_promise`
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
- assets are appropriate and professional
- the script contains no runtime-padding filler

If any condition fails, revise first.

## Stop condition

Do not render the video.
Do not trigger GitHub Actions.
Do not generate Kokoro narration.
Do not approve the plan.
Do not modify Shorts files.

Stop after committing the JSON and summary, then present the storyline summary to the user and ask whether they want to create the video.
