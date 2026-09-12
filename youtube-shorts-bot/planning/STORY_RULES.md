# Wacky Dramas Story Rules

## Story goal

Create one complete, original first-person drama with this natural arc:

**card hook → context → escalating conflict → decisive action → consequence/reversal → satisfying payoff**

Good categories include relationship, dating, marriage, betrayal, family, inheritance, money, workplace, revenge, friendship, wedding, entitled-person conflict, neighbours, secrets/discovery, housing/property, parenting, moral dilemmas, kindness, misunderstandings, hidden identity, consequences and believable reversals.

## Originality and safety

- Original stories only.
- Do not copy Reddit posts or closely paraphrase existing stories.
- Do not fabricate wrongdoing about identifiable real people.
- Use broad, natural, conversational English.
- Keep character names minimal unless a name materially improves clarity.
- Every sentence should advance the story.
- Avoid filler, repeated explanations, and unnecessary scene-setting.
- Complete the payoff in one Short.
- Never force a Part 2 or create a fake cliffhanger solely for follow bait.
- A consequence, reversal, reveal, boundary, or satisfying backfire is preferred when it fits naturally.
- The premise must have enough substance to sustain the target duration naturally; never pad a weak idea.

## Semantic punchline contract

The private planner is the semantic authority for every production story. While writing the final script, identify the actual reveal, reversal, comeback, consequence, contradiction, unexpected detail, or payoff that delivers the story's main emotional/comedic/dramatic reward. Do not defer this decision to the renderer or infer it later from audio, sentence position, punctuation, keywords, prosody, or “last sentence” rules.

Every new schema-v4 `story` must contain a required `punchline` object:

```json
{
  "text": "He had deleted the wrong folder.",
  "emphasis_text": "wrong folder",
  "type": "REVERSAL"
}
```

Rules:

- `text` is the complete semantic payoff span and must occur exactly once in `story.script` after safe punctuation/case/apostrophe normalization.
- `emphasis_text` is the strongest payoff wording inside that already-resolved punchline, normally 1–5 words. It must occur exactly once inside `punchline.text`.
- `type` is optional; when present it must be one of `REVEAL`, `REVERSAL`, `BACKFIRE`, `COMEBACK`, `CONSEQUENCE`, `CONTRADICTION`, or `ABSURDITY`.
- Do not fabricate or paraphrase punchline metadata with words absent from the narration. Metadata points at the authored script; it does not create a second version of it.
- The punchline is not automatically the final sentence, final clause, text after “but”, or most emotional sentence. Select it semantically while authoring the story.
- The punchline must not be the entire story. If the story has no genuine payoff, improve/reject the story instead of filling the fields mechanically.
- Repeated wording must remain unambiguous. If the same candidate punchline occurs twice, use enough exact script context to identify the intended payoff. If `emphasis_text` repeats inside the punchline, choose a slightly longer exact phrase that is unique while remaining concise.
- Request validation is fail-closed. A winner with missing, fabricated, ambiguous, overlong, or internally inconsistent semantic metadata must not be committed as an immutable production request.

The runtime uses Wav2Vec2 only to determine **when** these planner-selected words are spoken. The planner determines **which** words carry the payoff. The renderer determines **how** they are styled. Never move semantic interpretation into the public execution runtime.

## Opening card and narration sequence

The rendered opening has four strict phases:

1. Show the opening card for **0.50 seconds of intentional silence** before narration begins.
2. Narrate `story.hook` in full. **Do not show subtitles during the card-title narration.**
3. After the title narration finishes, fade the card out over the renderer's short transition. Do not start the story or subtitles until the card has fully transitioned out.
4. Start `story.script` narration only after the card is gone. Subtitles begin with the story narration and remain synchronized to the story body.

Planning rules:

- `story.hook` is the spoken opening-card title/headline, not the first paragraph of the story.
- Keep it crisp and immediately intriguing; prefer roughly **5–10 words** when natural so it reads quickly at the frozen approved voice / `1.75×`.
- `story.script` starts directly after the hook and **must not repeat the hook verbatim**. The request validator rejects a script that starts by repeating `story.hook`.
- The first story-body sentence should deepen curiosity immediately through a contradiction, discovery, consequence, evidence, urgent conflict or unanswered event.
- Avoid generic introductions such as “for context”, relationship-length history, unnecessary ages, family trees, or “this happened a few years ago” before the interesting event unless essential.
- Narrate in first person and make the conflict easy to follow on first listen.
- Select one approved Kokoro voice from explicit lead gender first and tone second: female natural `af_heart`, female expressive `af_bella`, male natural `am_echo`, male expressive `am_fenrir`; speed remains `1.75`. Freeze `lead_gender`, `story_tone`, and the voice in schema-v4.
- Aim for **120–175 seconds of total rendered narration sequence** at the configured voice/speed. This includes the 0.50-second opening silence, spoken card title, card transition, story narration, and 0.35-second ending silence.
- The renderer includes **0.50 seconds of silence at the beginning** and **0.35 seconds at the end**.
- **178 seconds is the hard production ceiling** for the complete encoded Short. The renderer reserves an additional 0.10-second encode safety margin, and the encoded-file verifier independently rejects anything over 178 seconds.
- The planner should target natural spoken length, not an arbitrary word count.
- If a production render would exceed the ceiling, do not trim the ending. Rewrite/regenerate as a **new request/content ID**.

## Title and hook quality

The YouTube title and the first spoken story-body line should cooperate rather than repeat each other.

Titles should create a truthful curiosity gap with specific tension. Prefer concrete contradiction/discovery structures over generic descriptions. Generate materially different title patterns during daily planning, score them independently, and choose only an accurate title.

Never promise a reveal, person, crime, consequence or emotional event that does not actually occur in the script.

## Card and metadata

Generate:

- 4–6 contextual card emojis.
- A concise, spoken hook/headline for the opening card.
- A YouTube title containing `#Shorts` and no more than 100 characters.
- A short original description.
- 3–8 relevant hashtags, including `#shorts` and `#wackydramas`.

Always use:

- `Wacky Dramas`
- `@WACKYDRAMAS`

Never output retired branding, old CTA fields, series/Part-2 fields, music requirements, or a mutable publication queue.

## Daily planning

`DAILY_PLANNER_PROMPT.md` is the canonical daily funnel for schema-v4 scheduled requests through `daily-production.yml`.

The daily funnel generates at least 120 meaningfully distinct raw premises, rejects weak/duplicate ideas cheaply, develops only semifinalists, competes at least five truthful titles per semifinalist, applies cold-start/analytics scoring plus diversity, and creates at most 24 immutable production requests.

Only final winners may trigger expensive media resolution, TTS, rendering or YouTube upload.

## Background selection

The request creator owns the logical content/diversity decision; `media/media_resolver.py` does not. The background is a retention layer, not necessarily a literal reenactment. Describe visual requirements using relevant tags, motion type/intensity and orientation, then use `media/background_selector.py` against the registry and successful receipts.

The centralized policy balances semantic fit with visual satisfaction, loopability and caption readability:

- Normally hard-avoid an asset used in the latest 10 successful Shorts.
- Apply a strong recency penalty to uses 10–19 Shorts ago and a tapering penalty through 29 Shorts ago.
- Prefer never-used assets only when they are genuinely strong matches.
- Require two strong, fresh candidates for primary and backup.
- Require each new selection to have at least one registered rendition whose effective 9:16 crop can produce 1080×1920 with no more than 5% enlargement; this is an availability gate, not rendition selection. Caption readability in the subtitle-safe region has priority over aesthetics.
- If fewer than two exist, stop request creation and expand the registry through the planning-only Pexels tooling.
- Never select a poor match solely for age or novelty.

Primary and backup logical IDs must always differ. Do not put mutable usage counters in the registry; only successfully verified immutable `content/results/*.json` receipts are authoritative. Failed requests, renders and uploads do not count.

Registry expansion happens before the immutable request is created. Search the official Pexels API using planning-only credentials, visually verify quality/license/readability/no text/no watermark, capture usable renditions, assign the next stable logical ID under the registry lock, commit it, then create the request. Production reads checked-in metadata only and may resolve only the request's primary and backup.
