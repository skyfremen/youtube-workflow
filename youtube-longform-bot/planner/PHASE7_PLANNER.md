# Wacky Insights Phase 7/8+ — ChatGPT Planner Contract

This file is the reusable source of truth for ChatGPT when creating a new Wacky Insights long-form plan.

## Read first

Before planning anything, read and obey:

1. `planner/CHANNEL_PERSONALITY.md`
2. `assets/design-system.json`
3. `assets/registry.json`
4. recent long-form plan/summary files when useful for avoiding repetition

The active style is **`wacky_insights_v2`**.

The channel promise is **educational value + humour**. Every video must teach something meaningful while remaining relatable, witty and visually entertaining.

A plan is off-brand if it is funny but shallow, educational but dry, trivia-heavy without a coherent explanation, slide-like, visually repetitive, or static while narration does all the work.

Target reaction: **“I actually learned something — and that was funny.”**

## Operating model

ChatGPT is the planning/intelligence layer. GitHub Actions is the deterministic production layer.

For a planning request, ChatGPT must:

1. Read the required instruction files above.
2. Understand or choose the topic.
3. Define a one-sentence learning promise.
4. Identify the central question/mystery.
5. Decide the core explanatory mechanism and 2–4 meaningful supporting insights.
6. Choose humour devices that naturally fit the topic.
7. Write coherent narration with hook, escalation, explanation, examples/contrasts, payoff and takeaway.
8. Break narration into environment-led scenes and distinct shots.
9. Describe every visual need before selecting assets.
10. Reuse strong matching assets from `assets/registry.json` where suitable.
11. When no strong asset exists, define a professional reusable `wacky_insights_v2` generation spec.
12. Produce `content/phase7-plan.json`.
13. Produce `content/phase7-summary.txt` for human review.
14. Commit both review artifacts.
15. STOP. Do not trigger rendering until the user explicitly approves.

## Topic selection

When no topic is supplied, choose one broadly relatable topic that supports BOTH explanation and humour.

Strong topic families include everyday psychology, habits and human behaviour, relationships and social behaviour, sleep, food behaviour, phones and technology, work and school habits, memory and attention, travel behaviour, household routines, awkward social situations, common body/brain experiences that can be explained safely and accurately, and surprising everyday science.

Prefer topics where the viewer instantly recognises the situation and naturally asks “why?” or “how?”.

Avoid obscure trivia, shock-value-only topics, weak mechanisms, or topics with little visual storytelling potential.

## Educational-value requirements

Every plan must include:

- `learning_promise`
- `central_question`
- `educational_points`

The script should normally contain:

- one central question or mystery
- 2–4 meaningful explanatory ideas
- at least one concrete everyday example
- at least one visual analogy, comparison, demonstration, or cause-and-effect sequence
- a clear takeaway near the end

The explanation should answer WHY or HOW, not merely state facts.

### Accuracy

Do not invent mechanisms or present guesses as facts.

When a claim is scientific, medical, psychological, historical, financial, numerical, disputed, or otherwise accuracy-sensitive, verify it before presenting it strongly. Preserve uncertainty where appropriate. Do not turn correlations into causal claims. Simplify without becoming false.

If the educational mechanism is weak or uncertain, choose a better angle or topic rather than padding with trivia.

## Humour requirements

Humour must be integrated into the story rather than saved for a single final joke.

Preferred devices:

- relatable observations
- visual exaggeration
- absurd but clear comparisons
- anthropomorphism
- recurring visual gags
- callbacks
- deadpan object labels
- escalation
- reaction comedy
- surprise reversals
- punchlines attached to educational points

For mature long-form videos, target roughly one meaningful humour beat every 10–20 seconds, with lighter visual humour between beats. MVP videos may be denser.

Avoid mean-spirited humour, obscure references, overly childish jokes, stale meme dependence, or jokes that contradict the educational point.

## Story architecture

Do not structure the video as a list of facts or a textbook chapter.

Preferred arc:

1. **Hook** — show the relatable oddity immediately.
2. **Escalation** — make it more recognisable/funny.
3. **Question** — establish what the viewer will understand.
4. **Mechanism** — explain the real reason step by step.
5. **Examples/contrast** — demonstrate it in different situations.
6. **Surprising implication** — show where else the mechanism matters.
7. **Callback/payoff** — return to the opening with new understanding.
8. **Takeaway** — leave a memorable answer.

For future 8–10 minute videos, use multiple mini-arcs. Each section should introduce a small question, explain it visually, and end with a mini-payoff while advancing the main story.

## Narration rules

Narration should sound like a smart, funny friend explaining something interesting.

Prefer conversational language, plain English, active voice, short and medium sentences, concrete examples, natural transitions, occasional rhetorical questions and concise playful phrasing.

Avoid generic school-essay intros, excessive jargon, long definitions, repetitive filler, forced jokes in every sentence, fake certainty and lecture-like phrasing.

## Required JSON editorial metadata

Every new `content/phase7-plan.json` must include at minimum:

```json
"style_id": "wacky_insights_v2",
"channel_personality": {
  "educational": true,
  "humorous": true,
  "tone": "curious_playful_relatable"
},
"learning_promise": "One sentence describing what the viewer will understand.",
"central_question": "The mystery being answered.",
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

The `planner.design_system` field must also equal `wacky_insights_v2`.

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

When the user explicitly says to create/render the video, ChatGPT may change the status to `approved`, set `approved_by` to `user`, add an ISO-8601 approval timestamp, and then trigger the GitHub workflow if workflow-dispatch tooling is available.

The GitHub workflow must refuse to render a plan whose approval status is not `approved`.

## Wacky Insights v2 visual direction

The target is an original professional editorial 2D explainer style with:

- rounded, readable, animation-friendly characters
- medium-detail real environments
- clear foreground/midground/background hierarchy
- topic-specific props
- muted environments with stronger focal subjects
- soft depth and consistent lighting
- integrated charts, meters, arrows, labels, screens and boards
- visual humour inside the action
- purposeful motion
- broad reusable environment and character packs

Use broad professional explainer-animation principles such as clarity, modularity, visual hierarchy and integrated information graphics. Never copy another channel's branding, exact characters, exact scene compositions, proprietary assets or distinctive visual identity.

## Hard visual rules

- Never design scenes as PowerPoint slides.
- Avoid title + cards, presentation grids, static comparison panels, paragraph blocks and long full-screen charts.
- Prefer characters, environments, props, reactions, object state changes, visual metaphors, camera motion, short labels and embedded infographic overlays.
- Captions: maximum 7 words.
- Aim for a meaningful visual change approximately every 1.0–1.5 seconds.
- Motion must advance story, explanation, humour or emphasis.
- Educational graphics should usually exist inside the animated world rather than replacing it.
- Most runtime should remain scene-based and environment-led.
- Target roughly 80% environment-led storytelling, no more than about 15% full-screen infographic, and very little text-only runtime.

## Visual explanation standard

Every scene should answer: **What is the viewer learning or feeling from the visuals that audio alone would not provide?**

Good examples include cause/effect chains, attention spotlights, animated meters, physical metaphors, split behaviour, moving arrows and labels that follow active objects.

Weak examples include a standing character while narration explains everything, full-screen cards repeating narration, decorative icons unrelated to the mechanism, or captions carrying the explanation.

## Scene transition rules — HARD REQUIREMENT

Transitions must feel **seamless but clearly intentional**.

### Core rule

A true scene change must introduce a meaningfully different shot.

If the next shot uses nearly the same background, framing and focal action, it should usually **not** become a new scene. Keep it inside the current scene and use a camera move, reframe, insert, reaction close-up, new focal object, prop-state change, overlay beat or character movement.

### Same-environment rule

If a new scene intentionally keeps the same environment, it must differ clearly in at least **two** of these dimensions:

- framing
- camera angle
- focal subject
- subject grouping
- prop state
- action emphasis
- story emphasis

If it does not, merge it into the previous scene.

### Preferred transitions

Prefer:

- match-action cuts
- pan/follow into the next beat
- push-in to close-up
- cut to an insert/object detail
- reaction shot
- moving-object wipe
- motivated reframe
- overlay-led transition
- cut to a clearly different environment

Avoid:

- blink-like cuts
- same-background/same-framing cuts
- random flash cuts
- presentation-slide replacement cuts

The viewer should feel **progression, not blinking**.

## Shot variety rules

Deliberately vary shot grammar across the video:

- wide establishing shot
- medium action shot
- close-up
- insert/object shot
- over-shoulder where useful
- reaction shot
- split-behaviour scene
- diagram/data integrated into an environment

Do not repeatedly present the same character in the same location at the same scale.

Every scene should include planning metadata for visual distinction where practical:

```json
"shot": {
  "framing": "wide|medium|closeup|insert|over_shoulder|reaction|split_behavior",
  "camera_angle": "front|three_quarter|side|over_shoulder|detail",
  "focal_subject": "asset_or_story_focus",
  "transition_in": "cut_to_distinct_environment|match_action|push_in|insert_cut|reaction_cut|reframe|object_wipe|continuation"
}
```

For consecutive scenes, avoid identical `environment + framing + camera_angle + focal_subject` combinations.

## Asset intelligence

For every visual need:

1. define the subject
2. define its narrative/educational purpose
3. define context/environment
4. define viewpoint/framing when important
5. define required actions/states
6. search `assets/registry.json`
7. reuse only if the match is genuinely strong
8. otherwise define `generation`

Do not reuse an asset merely because its category matches. Legacy `wacky_insights_v1` assets may be reused only when they visually fit v2 well enough; otherwise request a v2 replacement rather than forcing weak reuse.

## Generated asset requirements

A generation specification must contain:

- stable reusable `asset_id`
- approved `template` or supported professional generator type
- descriptive reusable `description`
- semantic `tags`
- `style_id`: `wacky_insights_v2`
- intended actions/states where useful
- `reusable: true`

Generated assets should look professionally art-directed, not procedurally crude. They must fit the v2 design system and work at target resolution.

Generated assets are not persisted merely because they were created. The workflow validates them and successfully renders the video first. Only then may new assets be committed into the permanent registry.

## Storyboard requirements

For the current MVP architecture:

- narration-first timing
- 24 fps
- minimum 5 scenes
- minimum 4 meaningful visual beats per scene
- environment + character in every current Phase 7 scene unless a future renderer supports another high-quality scene type
- `visuals` contains positioned reusable assets
- `overlays` contains short action-connected labels rather than paragraphs
- `beats[].at_pct` is between 0 and 1 and chronological
- captions are short support only; the video must remain understandable without relying on them
- every scene should define a `shot` object so transition quality can be checked

## Human-readable summary

Together with `content/phase7-plan.json`, write `content/phase7-summary.txt`.

The summary must let the user judge CONTENT without reading JSON. Include:

- working title
- approximate intended length
- learning promise
- one-paragraph story overview
- scene-by-scene storyline in plain English
- main educational points
- humour approach / recurring gag
- final punchline/payoff
- scene/location variety at a glance
- existing assets expected to be reused
- new assets expected to be generated
- final line: `STATUS: AWAITING APPROVAL — no video has been rendered.`

## Editorial quality gate

Before committing the plan, verify all of the following:

- The learning promise is specific and worthwhile.
- The video teaches at least 2 meaningful things.
- The explanation answers why/how rather than listing trivia.
- Educational claims are supportable and not exaggerated.
- Humour appears throughout the story.
- Humour supports relatability, pacing or explanation.
- The first scene creates curiosity quickly.
- There is a clear final callback/payoff.
- Visuals actively explain the mechanism.
- The video does not feel like PowerPoint.
- Scene boundaries are visually distinct enough to avoid blink-like cuts.
- Repeated environments are treated as continuity or strongly reframed.
- Shot scale/framing varies across the story.
- Asset choices are contextually appropriate and professionally designed.
- The narration contains no filler merely to reach target duration.

If any condition fails, revise before committing.

## Output

Write both:

- `content/phase7-plan.json`
- `content/phase7-summary.txt`

Do not modify Shorts files. Do not trigger a render during the planning/review step.
