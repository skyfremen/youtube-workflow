# Wacky Insights Phase 7 — ChatGPT Planner Contract

This file is the reusable source of truth for ChatGPT when creating a new Wacky Insights long-form plan.

## Channel personality is mandatory

Before planning anything, read and obey:

1. `planner/CHANNEL_PERSONALITY.md`
2. `assets/design-system.json`
3. `assets/registry.json`
4. recent long-form plan/summary files when useful for avoiding repetition

The channel promise is **educational value + humour**. Every video must teach something meaningful while remaining relatable, witty and visually entertaining.

A plan is off-brand if it is:

- funny but shallow
- educational but dry
- trivia-heavy without a coherent explanation
- a sequence of presentation slides
- visually static while narration does all the work

The desired viewer reaction is: **“I actually learned something — and that was funny.”**

## Operating model

ChatGPT is the planning/intelligence layer. GitHub Actions is the deterministic production layer.

For a planning request, ChatGPT must:

1. Read the required instruction files above.
2. Understand the topic and define a one-sentence learning promise.
3. Identify the central question/mystery.
4. Decide the core explanatory mechanism and 2–4 meaningful supporting insights.
5. Write a coherent narration with a hook, escalation, explanation, examples/contrasts, payoff and takeaway.
6. Break the narration into environment-led scenes.
7. Describe every visual need before selecting assets.
8. Reuse strong matching assets from `assets/registry.json` where suitable.
9. When no strong asset exists, define a professional reusable generation spec.
10. Produce `content/phase7-plan.json`.
11. Produce `content/phase7-summary.txt` for human review.
12. Commit both review artifacts.
13. STOP. Do not trigger rendering until the user explicitly approves.

## Topic selection

When no topic is supplied, choose one broadly relatable topic that supports BOTH explanation and humour.

Strong topic families include:

- everyday psychology
- habits and human behaviour
- relationships and social behaviour
- sleep and tiredness
- food behaviour
- phones and technology
- work and school habits
- money behaviour at a general non-advisory level
- memory and attention
- travel behaviour
- household routines
- awkward social situations
- common body/brain experiences that can be explained safely and accurately
- surprising everyday science

Prefer topics where the viewer immediately recognises the situation and naturally asks “why?”

Avoid topics that are only obscure trivia, depend on shock value, or have little room for visual storytelling.

## Educational-value requirements

Every plan must include a clear `learning_promise` in the JSON.

The script should normally contain:

- one central question or mystery
- 2–4 meaningful explanatory ideas
- at least one concrete everyday example
- at least one visual analogy, comparison, demonstration, or cause-and-effect sequence
- a clear takeaway near the end

The explanation should answer WHY or HOW, not merely state facts.

### Accuracy

Do not invent mechanisms or present guesses as facts.

When a claim is scientific, medical, psychological, historical, financial, numerical, disputed, or otherwise accuracy-sensitive, verify it before presenting it strongly. Keep uncertainty where appropriate. Do not turn correlations into causal claims. Simplify without becoming false.

If the educational mechanism is weak, uncertain, or not genuinely useful, choose a better angle or topic.

## Humour requirements

Humour must be integrated into the story rather than saved for a single final joke.

Preferred humour devices:

- relatable observations
- visual exaggeration
- absurd but clear comparisons
- anthropomorphism
- recurring visual gag
- callback
- deadpan object labels
- escalation
- surprise reversal
- punchline attached to an educational point

Use humour to improve retention and understanding, never to obscure the explanation.

For mature long-form videos, target roughly one meaningful humour beat every 10–20 seconds, with lighter visual humour between those beats. MVP videos may be denser.

Avoid mean-spirited humour, obscure references, overly childish jokes, stale meme dependence, or jokes that contradict the educational point.

## Story architecture

Do not structure the video as a list of facts or a textbook chapter.

Preferred narrative arc:

1. **Hook:** show the relatable oddity immediately.
2. **Escalation:** make the situation more recognisable/funny.
3. **Question:** establish what the viewer is going to understand.
4. **Mechanism:** explain the real reason step by step.
5. **Examples/contrast:** demonstrate the idea in different situations.
6. **Surprising implication:** show where else the mechanism matters.
7. **Callback/payoff:** return to the opening situation with new understanding.
8. **Takeaway:** leave the viewer with a memorable answer.

For future 8–10 minute videos, use multiple mini-arcs. Each section should introduce a small question, explain it visually, and end with a mini-payoff while advancing the main story.

## Narration rules

Narration should sound like a smart, funny friend explaining something interesting.

Prefer:

- conversational language
- plain English
- active voice
- short and medium sentences
- concrete examples
- natural transitions
- occasional rhetorical questions
- concise playful phrasing

Avoid:

- “Today we are going to discuss…”
- generic school-essay intros
- excessive jargon
- long definitions
- repetitive filler
- forced jokes in every sentence
- fake certainty
- lecture-like phrasing

## Required JSON editorial metadata

Every new `content/phase7-plan.json` should include at minimum:

```json
"channel_personality": {
  "educational": true,
  "humorous": true,
  "tone": "curious_playful_relatable"
},
"learning_promise": "One sentence describing what the viewer will understand.",
"educational_points": [
  "Meaningful explanatory point 1",
  "Meaningful explanatory point 2"
],
"humour_strategy": {
  "style": ["relatable_observation", "visual_exaggeration", "callback"],
  "recurring_gag": "Optional recurring visual/comedic idea",
  "final_payoff": "The intended final humorous callback/punchline"
}
```

This metadata is for quality control and future automation. It does not need to appear on screen.

## Review gate

Every generated plan must contain:

```json
"approval": {
  "status": "review_required",
  "approved_by": null,
  "approved_at": null
}
```

The planning step must never self-approve.

When the user explicitly says to create/render the video, ChatGPT may change the status to `approved`, set `approved_by` to `user`, add an ISO-8601 approval timestamp, and then trigger the GitHub workflow if workflow-dispatch tooling is available. If dispatch is unavailable, leave the approved plan ready for manual execution.

The GitHub workflow must refuse to render a plan whose approval status is not `approved`.

## Human-readable summary

Together with `content/phase7-plan.json`, write:

`content/phase7-summary.txt`

The summary must let the user judge the CONTENT without reading JSON.

Include:

- Working title
- Approximate intended length
- **Learning promise — what the viewer will understand**
- One-paragraph story overview
- Scene-by-scene storyline in plain English
- The main educational points
- Humour approach / recurring gag
- Final punchline/payoff
- Existing assets expected to be reused
- New assets expected to be generated
- Final line: `STATUS: AWAITING APPROVAL — no video has been rendered.`

Do not dump implementation details or raw JSON into the summary.

## Required planning order

1. Define the learning promise.
2. Define the central question.
3. Define the explanatory mechanism and supporting points.
4. Choose humour devices that naturally fit the topic.
5. Write the narration as a coherent story.
6. Break the narration into environment-led scenes.
7. For every visual beat, describe the visual need before choosing an asset.
8. Search `assets/registry.json` conceptually first and prefer a strong reusable match.
9. If no asset is semantically strong enough, add an `asset_needs[].generation` specification.
10. Ensure generated assets follow `assets/design-system.json` and are reusable beyond one video where practical.
11. Keep infographic information as overlays inside active scenes whenever possible.
12. Use relative `at_pct` beat positions. Kokoro narration remains the master clock; exact seconds are generated later.
13. Run the editorial quality check before committing the plan.

## Hard visual rules

- Never design scenes as PowerPoint slides.
- Avoid title + cards, presentation grids, static comparison panels, paragraph blocks and long full-screen charts.
- Prefer characters, environments, props, reactions, object state changes, visual metaphors, camera motion, short labels and embedded infographic overlays.
- Captions: maximum 7 words.
- Aim for a visible meaningful change approximately every 1.0–1.5 seconds.
- A visual change should usually advance story, explanation, humour or emphasis rather than be motion for motion's sake.
- Maintain Wacky Insights proportions, palette, lighting, stroke treatment and soft-depth vector style.
- Educational graphics should usually exist inside the animated world rather than replacing it.
- Most runtime should remain scene-based and environment-led.

## Visual explanation standard

The visuals must contribute to understanding.

Good examples:

- an attention spotlight narrows while a timer slows perceptually
- two characters demonstrate contrasting behaviours
- a meter fills as a concept builds
- objects physically move through a cause-and-effect chain
- a metaphor transforms into the real mechanism
- labels/arrows follow moving objects

Weak examples:

- narration explains while a character simply stands still
- a full-screen card repeats the narration
- generic decorative icons unrelated to the mechanism
- captions carrying the whole educational explanation

Every scene should answer: **What is the viewer learning or feeling from the visuals that audio alone would not provide?**

## Asset matching

Each asset need must contain:

- `need_id`
- `category`: character, environment, prop, or infographic
- specific `description`
- at least 3 semantic `tags`
- intended narrative/educational purpose where useful
- `generation` only when no strong existing match should be used

The workflow resolves needs against `assets/registry.json`. The current match threshold is controlled by `planner.asset_match_threshold`.

Do not reuse an asset merely because its category matches. Reuse only if the subject, context, viewpoint, actions and quality are suitable.

## Generated asset requirements

A generation specification must contain:

- stable reusable `asset_id`
- approved `template` or supported professional generator type
- descriptive reusable `description`
- semantic `tags`
- intended actions/states where useful
- `reusable: true`

Generated assets should look professionally art-directed, not procedurally crude. They must fit the established design system and work at target resolution.

Generated assets are not persisted merely because they were created. The workflow validates them and successfully renders the video first. Only then may new assets be committed into the permanent registry.

## Storyboard requirements

For the current MVP architecture:

- narration-first timing
- 24 fps
- minimum 5 scenes
- minimum 4 meaningful visual beats per scene
- environment + character in every current Phase 7 scene unless a future renderer explicitly supports another high-quality scene type
- `visuals` contains positioned reusable assets
- `overlays` contains short action-connected labels rather than paragraphs
- `beats[].at_pct` is between 0 and 1 and chronological
- scene captions are short and optional in spirit; the video must remain understandable without relying on them

## Editorial quality gate

Before committing the plan, verify all of the following:

- The learning promise is specific and worthwhile.
- The video teaches at least 2 meaningful things.
- The explanation answers why/how rather than just listing trivia.
- The educational claims are supportable and not exaggerated.
- Humour appears throughout the story.
- The humour supports relatability, pacing or explanation.
- The first scene creates curiosity quickly.
- There is a clear final callback/payoff.
- The visuals actively explain the mechanism.
- The video does not feel like PowerPoint.
- The asset choices are contextually appropriate.
- The planned narration does not contain filler merely to reach a target duration.

If any of these fail, revise before committing.

## Output

Write both:

- `content/phase7-plan.json`
- `content/phase7-summary.txt`

Do not modify Shorts files. Do not trigger a render during the planning/review step.
