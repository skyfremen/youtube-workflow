# Wacky Dramas Story Rules

## Story goal

Create complete, original first-person dramas with a natural arc:

**card hook → context → escalating conflict → decisive action → consequence/reversal → satisfying payoff**

Good categories include relationship, dating, marriage, betrayal, family, inheritance, money, workplace, revenge, friendship, wedding, entitled-person conflict, neighbours, secrets/discovery, housing/property, parenting, moral dilemmas, kindness, misunderstandings, hidden identity, consequences and believable reversals.

## Originality and safety

- Original stories only.
- Do not copy Reddit posts or closely paraphrase existing stories.
- Do not fabricate wrongdoing about identifiable real people.
- Use broad, natural, conversational English.
- Keep character names minimal unless a name materially improves clarity.
- Every sentence should advance the story.
- Avoid filler, repeated explanations and unnecessary scene-setting.
- Complete the payoff in one Short.
- Never force a Part 2 or create a fake cliffhanger solely for follow bait.
- Prefer a natural consequence, reversal, reveal, boundary or satisfying backfire when it fits.
- The premise must have enough substance to sustain the target duration naturally; never pad a weak idea.

## Semantic punchline contract

The private planner is the semantic authority for every production story. While writing the final script, identify the actual reveal, reversal, comeback, consequence, contradiction, unexpected detail or payoff that delivers the main emotional/comedic/dramatic reward. Do not defer this decision to the renderer or infer it later from audio position, punctuation, keywords, prosody or “last sentence” rules.

Every newly authored schema-v7 `story` contains the required `punchline` object introduced by the earlier schema family:

```json
{
  "text": "He had deleted the wrong folder.",
  "emphasis_text": "wrong folder",
  "type": "REVERSAL"
}
```

Rules:

- `text` is the complete semantic payoff span and must occur exactly once in `story.script` after safe punctuation/case/apostrophe normalization.
- `emphasis_text` is the strongest payoff wording inside the resolved punchline, normally 1–5 words, and must occur exactly once inside `punchline.text`.
- `type` is optional; when present it must be one of `REVEAL`, `REVERSAL`, `BACKFIRE`, `COMEBACK`, `CONSEQUENCE`, `CONTRADICTION`, or `ABSURDITY`.
- Do not fabricate/paraphrase punchline metadata with words absent from narration.
- The punchline is not automatically the final sentence or clause.
- The punchline must not be the entire story. If no genuine payoff exists, improve/reject the story.
- Repeated wording must remain unambiguous; use enough exact script context to identify the intended payoff.
- Request validation is fail-closed for missing, fabricated, ambiguous or inconsistent semantic metadata.

Wav2Vec2 determines **when** planner-selected words are spoken. The planner determines **which** words carry the payoff. The renderer determines **how** they are styled. Semantic interpretation stays out of the public runtime.

## Opening card and narration sequence

The rendered opening has four phases:

1. Show the opening card for **0.50 seconds of intentional silence** before narration begins.
2. Narrate `story.hook` in full. Do **not** show subtitles during card-title narration.
3. Fade the card out over the renderer transition after the hook completes.
4. Start `story.script` narration and subtitles only after the card is gone.

Planning rules:

- `story.hook` is the spoken opening-card title/headline, not the first story paragraph.
- Prefer roughly **5–10 words** when natural.
- `story.script` must not start by repeating the hook verbatim.
- The first story-body sentence should deepen curiosity immediately through contradiction, discovery, consequence, evidence, urgent conflict or an unanswered event.
- Avoid generic “for context” intros, relationship-history filler, unnecessary ages/family trees or long setup before the interesting event.
- Narrate in first person and keep conflict easy to follow on first listen.
- Use one approved Kokoro voice for the complete Short, resolved from lead gender first and tone second:
  - female natural/general → `af_heart`
  - female expressive/funny/dramatic/sarcastic → `af_bella`
  - male natural/general → `am_echo`
  - male expressive/funny/dramatic/sarcastic → `am_fenrir`
- Under the current contract narration speed remains `1.75` unless current code/config changes it.
- Aim for **120–175 seconds** of the full rendered narration sequence.
- Renderer includes 0.50s opening silence and roughly 0.35s ending silence.
- **178 seconds is the hard production ceiling**; do not trim away the payoff to fit it.

## Title and hook quality

The YouTube title, opening-card hook and first spoken story-body line should cooperate rather than repeat one another.

Titles should create a truthful curiosity gap with specific tension. Prefer concrete contradiction/discovery structures over generic descriptions. Generate materially different truthful title patterns for serious contenders and choose only an accurate title.

Never promise a reveal, person, crime, consequence or emotional event that does not occur in the script.

## Card and YouTube metadata

Each complete production candidate includes:

- 4–6 contextual card emojis;
- a concise spoken hook/headline;
- a truthful YouTube title containing `#Shorts` and no more than 100 characters;
- a short original story-specific description;
- 3–8 relevant visible hashtags, normally including `#Shorts` and `#WackyDramas`;
- 4–12 explicit backend semantic tags without `#`;
- current canonical category and made-for-kids values.

Always use:

- `Wacky Dramas`
- `@WACKYDRAMAS`

Never output retired branding, legacy CTA/series fields, forced Part-2 fields, music requirements or a mutable publication queue.

## Daily planning

`DAILY_PLANNER_PROMPT.md` is the canonical Daily profile entry point.

For a normal full day ChatGPT authors exactly **24 complete production-quality candidates**, one for each required publication slot. For same-day catch-up ChatGPT authors exactly `target_count`, where `target_count` is the number of eligible remaining publication slots. There are no fully authored reserve candidates and no first-24-of-36 rank walk for new planning.

The creative funnel may still begin broadly with cheap premise exploration (normally at least 120 distinct raw premises), reject weak/duplicate ideas early, develop the exact production set, run truthful title competition and apply analytics/diversity/editorial reasoning. Broad ideation does not require fully authoring extra reserve stories.

If candidate N is weak or invalid before immutable pool commit, ChatGPT repairs or regenerates candidate N while preserving the other valid candidates, then reruns the canonical deterministic checkpoint. Repository code never creatively repairs or reranks authored stories.

## Ad-hoc planning

`ADHOC_PLANNER_PROMPT.md` is the canonical Ad-hoc profile entry point.

New Ad-hoc planning supports **`manual_on_demand` only**. ChatGPT authors exactly **one** complete production-quality candidate with `target_count = 1`. The candidate may retain `rank = 1` for pool-shape compatibility, but there is no five-story creative competition, reserve walk or first-valid-of-five promotion for new pools.

Multiple manual invocations may coexist when their immutable identities differ. Historical scheduled Ad-hoc pools/requests remain immutable and recoverable only through the historical compatibility path; `scheduled_daily` is not a new-planning mode.

If the single candidate is weak or invalid before pool commit, repair or regenerate it and rerun the canonical checkpoint rather than terminating or authoring reserve candidates.

## Background planning for schema v7

ChatGPT owns semantic background-category suitability and the exact logical sequence choices. The public runtime does not choose a third logical asset, infer a replacement sequence or creatively reinterpret the request.

For every new pool candidate:

- choose one `background_category` that suits the story;
- every clip in both primary and backup sequences must belong to that same category;
- use schema-v7 `concatenated_fit_to_short` primary and backup ordered sequences;
- use 2–3 distinct clips per sequence, with 3 preferred;
- primary and backup must be disjoint;
- freeze exact logical clip IDs, sequence order, `segment_start_seconds` and `segment_duration_seconds`;
- do not intentionally loop clips;
- do **not** choose, calculate, freeze or manually validate playback rate; runtime derives the overall playback rate from actual final narration/timeline duration.

Selected assets must satisfy all current hard requirements, including registration, selectability, active/verified/visual-review state, commercial-use permission, watermark/text rules, trusted duration, production-suitable rendition, quality/retention requirements and valid segment ranges.

Global media-library readiness is not a Daily/Ad-hoc planner gate. Do not start, resume or wait for planner-bound replenishment during normal planning.

If the preferred category cannot form valid primary and backup sequences:

```text
preferred suitable category
→ another suitable eligible category
→ canonical fallback category exposed by the exact-SHA checkpoint contract
```

Fallback never weakens hard validation. If one selected clip fails, replace it with a hard-valid clip from the same chosen category. If the category itself cannot form both sequences, change category and rebuild both sequences.

## Schema, validation and immutability

New production candidates use **schema v7** and current planning pools use the repository's current pool schema. Historical schema v4/v5/v6 requests and schema-v1 planning pools remain immutable recovery formats where compatibility is still required.

ChatGPT commits planning-pool artifacts, not canonical production requests. Before commit, the exact-SHA standalone `planning/connector_checkpoint.py` is the single mechanical planning authority. Mechanical failures are repair instructions: repair only affected authored input and rerun the same checkpoint until all required candidates pass.

Private promotion workflows deterministically materialize canonical requests only after validation. For current pools every required candidate must already pass; production does not search reserves or creatively substitute backgrounds. Historical schema-v1 pools keep their versioned compatibility behavior.

Once a pool/request/result/recovery artifact is committed under an append-only path, do not edit or delete it. After a successful immutable planning-pool commit, ChatGPT/Work planning ends; downstream promotion, rendering and upload are automation responsibilities.
