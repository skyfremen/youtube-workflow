# Wacky Insights Long-form — Channel Personality

This file defines the editorial personality for every Wacky Insights long-form video. It is a hard planning requirement.

## Core promise

Every video must deliver BOTH:

1. **Real educational value** — the viewer should understand something useful, surprising, or clearer than before.
2. **Humour** — the explanation should stay light, relatable, witty, and entertaining without weakening the facts.

A video that is funny but teaches almost nothing is off-brand. A video that is informative but dry, lecture-like, or humourless is also off-brand.

Target reaction:

> “I actually learned something — and that was funny.”

## Editorial identity

Wacky Insights explains familiar everyday behaviour, science, psychology, technology, habits, social situations, household routines and odd human experiences in a way that is easy to understand and fun to watch.

The channel should feel:

- curious
- clever but not smug
- playful
- relatable
- visually energetic
- concise
- broad-audience friendly
- grounded in real explanations
- comfortable using absurd comparisons and exaggeration for comedy

It should NOT feel:

- academic or lecture-heavy
- like a school presentation
- like a generic facts channel
- like a list of trivia with no story
- like stand-up comedy with no explanation
- mean-spirited
- overly childish
- corporate
- clickbait with no payoff

## Educational value standard

Every planned video must have one clear **learning promise** that can be written in one sentence.

A long-form plan should normally contain:

- one central question or mystery
- 2–4 meaningful explanatory ideas supporting the answer
- at least one concrete everyday example
- at least one visual analogy, comparison, mini-demonstration, or cause-and-effect explanation
- a clear takeaway near the end

Prefer WHY/HOW explanation over trivia. Facts should support the story rather than interrupt it.

When factual claims are uncertain, nuanced, disputed, medical, scientific, historical, financial, numerical, or otherwise accuracy-sensitive, research/verify before presenting them strongly. Avoid inventing mechanisms, overstating correlation as causation, or turning a useful simplification into a false absolute.

## Humour standard

Humour should be woven through the explanation rather than added as a separate joke section.

Preferred humour:

- relatable observations
- exaggerated visual consequences
- unexpected comparisons
- anthropomorphism of objects or concepts
- callbacks to earlier jokes
- deadpan labels
- visual irony
- escalation
- reaction comedy
- small punchlines attached to educational points
- a final payoff that rewards the viewer for watching

Avoid:

- jokes that require obscure cultural knowledge
- insults aimed at groups or individuals
- cruelty or humiliation
- sexual humour as a default
- excessive meme references that will age quickly
- forcing a joke into every sentence
- jokes that obscure or contradict the educational point

For mature long-form videos, a useful rhythm is roughly one meaningful humour beat every 10–20 seconds, with lighter visual humour between those beats. MVP tests may be denser.

## Story structure

Do not write the video like a textbook chapter, listicle or bullet deck. Build a story.

Preferred structure:

1. **Hook / relatable mystery** — immediately show the weird or familiar behaviour.
2. **Escalation** — make the situation more recognisable or amusing.
3. **Question** — clearly establish what the viewer is about to learn.
4. **Explanation** — reveal the mechanism step by step.
5. **Examples / contrasts** — make the explanation tangible.
6. **Surprising implication** — show why the idea matters or where else it appears.
7. **Callback / punchline** — return to the opening situation with new understanding.
8. **Takeaway** — viewer leaves knowing the answer.

For future 8–10 minute videos, use multiple mini-arcs rather than one uninterrupted lecture. Each section should have its own small question, explanation, visual demonstration and mini-payoff while advancing the main story.

## Narration voice

Narration should sound conversational and confident, as though a smart, funny friend is explaining something interesting.

Prefer:

- short and medium-length sentences
- plain English
- active voice
- specific examples
- rhetorical questions used sparingly
- occasional playful phrasing
- clear transitions that feel spoken, not written

Avoid:

- “Today we are going to discuss…”
- school-essay intros
- jargon without immediate explanation
- long definitions
- excessive qualifiers that make narration cumbersome
- fake certainty
- repeating the same idea just to extend runtime
- lecture-like phrasing

## Wacky Insights v2 visual personality

The active design system is `wacky_insights_v2`.

The target visual feel is an **original, professional editorial 2D explainer style**: clean vector characters, diverse real environments, readable props, integrated information graphics, medium detail, soft depth, purposeful motion and broad topic flexibility.

Use professional explainer-animation principles such as clarity, modularity, visual hierarchy, environment variety and information embedded into scenes. Do not copy another channel's branding, characters, proprietary assets, exact compositions or distinctive visual identity.

Most runtime should show:

- characters acting out the idea
- environments that establish context
- moving props
- cause-and-effect animations
- visual metaphors
- diagrams integrated into the physical scene
- screens, boards and charts that exist inside the world
- labels attached to objects
- counters, meters, arrows, trails, timelines and highlights that animate with narration
- comedic visual exaggerations and reactions

The humour can happen visually even while narration explains a serious point.

Never turn the video into a sequence of slides. Full-screen text, title cards, infographic boards, charts or comparisons should be rare and brief. Prefer making educational graphics exist inside the animated world.

## Scene and transition philosophy

Scenes should flow seamlessly, but a true scene boundary must feel intentionally different.

### Core rule

If two consecutive shots use nearly the same background, framing and focal action, they should usually **not** be separate scenes.

Keep them inside one scene and create progression with:

- a camera push or pan
- a reframe
- an insert shot
- a reaction close-up
- a new focal object
- a prop/state change
- an overlay beat
- character movement

### When to use a true scene cut

A true scene change should introduce meaningful visual progression through a distinctly new environment or a strongly different shot. If the same environment is retained across a scene boundary, change at least two dimensions such as:

- framing
- camera angle
- focal subject
- subject grouping
- prop state
- action emphasis
- story emphasis

Avoid cuts where the next frame looks almost identical to the previous one. Those read as a blink or accidental flicker instead of storytelling.

Preferred transitions include motivated pans, match-action cuts, push-ins, inserts, reaction shots, object wipes, reframes and cuts to clearly different environments.

The viewer should always feel **progression, not blinking**.

## Shot variety

Across a video, deliberately vary shot grammar:

- wide establishing shot
- medium character/action shot
- close-up
- insert/object shot
- over-shoulder shot where useful
- reaction shot
- split-behaviour comparison
- diagram or data integrated into an environment

Do not repeatedly show the same character, same environment and same scale. If the location remains the same, either keep it as one continuous scene or reframe it strongly enough to create a clearly new shot.

## Quality check before committing a plan

Before writing `phase7-plan.json`, verify:

- Can the learning promise be stated in one sentence?
- Does the viewer learn at least 2 meaningful things rather than just hear trivia?
- Is the explanation understandable without specialist knowledge?
- Is humour present throughout rather than only at the end?
- Does every joke support pacing, relatability or explanation?
- Is there a clear hook and final payoff/callback?
- Are the visuals actively explaining the concept?
- Would the video still be interesting if on-screen captions were removed?
- Does it avoid PowerPoint-style presentation scenes?
- Are scene boundaries visually distinct enough to avoid blink-like cuts?
- If a background repeats, is it treated as continuity or strongly reframed?
- Do the planned assets look consistent with `wacky_insights_v2`?

If any answer is no, revise the plan before committing it.
