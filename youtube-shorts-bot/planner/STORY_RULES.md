# Wacky Dramas Story Rules

## Story goal

Create one complete, original first-person drama with this natural arc:

**card hook → context → escalating conflict → decisive action → consequence/reversal → satisfying payoff**

Good categories include workplace, boss/coworker, roommate, neighbours, relationship, dating, marriage, family, friendship, customers/service, school, travel, money, and everyday conflict.

## Originality and safety

- Original stories only.
- Do not copy Reddit posts or closely paraphrase Reddit stories.
- Do not fabricate wrongdoing about identifiable real people.
- Use broad, natural, conversational English.
- Keep character names minimal unless a name materially improves clarity.
- Every sentence should advance the story.
- Avoid filler, repeated explanations, and unnecessary scene-setting.
- Complete the payoff in one Short.
- Never force a Part 2 or create a fake cliffhanger solely for follow bait.
- A consequence, reversal, reveal, or satisfying backfire is preferred when it fits naturally.

## Opening card and narration sequence

The rendered opening has three strict phases:

1. Show the opening card and narrate `story.hook` in full. **Do not show subtitles during the card-title narration.**
2. After the title narration finishes, fade the card out over the renderer's short transition. Do not start the story or subtitles until the card has fully transitioned out.
3. Start `story.script` narration only after the card is gone. Subtitles begin with the story narration and remain synchronized to the story body.

Planning rules:

- `story.hook` is the spoken opening-card title/headline, not the first paragraph of the story.
- Keep it crisp and immediately intriguing; prefer roughly **5–10 words** when natural so it reads quickly at `af_heart` / `1.75×` and leaves room for controlled acceptance/debug renders.
- `story.script` should start directly after the hook and **must not repeat the hook verbatim**. Legacy immutable requests that already duplicate the hook are handled defensively by the renderer, but new requests should not rely on that fallback.
- Open the story body with immediate context or action so the transition from title into story feels continuous.
- Narrate in first person.
- Make the conflict easy to follow on first listen.
- Default Kokoro configuration: `voice=af_heart`, `speed=1.75`.
- Aim for **120–175 seconds of total rendered narration sequence** at the configured voice/speed, accounting for the spoken card title and transition as part of the final timing budget.
- **178 seconds is a hard production ceiling** including the opening sequence and natural ending tail.
- The planner should target natural spoken length, not an arbitrary word count.
- If a production render would exceed the ceiling, do not trim the ending. Rewrite/regenerate as a **new request/content ID**.

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

Never output:
- legacy channel branding, handle, or hashtags
- `DOUBLE TAP TO AGREE`
- `FOLLOW FOR PART`
- `comedy_mechanism`
- series/queue/hourly-slot concepts
- background music requirements

## Background selection

The background is a retention layer, not a literal reenactment. Prefer verified, visually satisfying, loopable, low-distraction motion with strong caption readability. Rank primarily by:
1. visual satisfaction
2. loopability
3. caption readability
4. moderate motion intensity
5. recent usage derived from successful result receipts
6. variety

Primary and backup IDs must always differ. Do not mutate background usage counters; successful `content/results/*.json` receipts are the authoritative usage history.
