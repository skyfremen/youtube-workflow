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
- Default Kokoro configuration: `voice=af_heart`, `speed=1.75`. The production primary backend is ONNX FP32; the request contract remains `engine=kokoro`.
- Aim for **120–170 seconds of total rendered narration sequence** at the configured voice/speed, accounting for the spoken card title and transition as part of the final timing budget. The ONNX FP32 benchmark produced about 2.5% longer audio than the former PyTorch primary for the same story, so this target deliberately leaves headroom.
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

The request creator owns the logical content/diversity decision; `media_resolver.py` does not. The background is a retention layer, not necessarily a literal reenactment. Describe visual requirements using relevant tags, motion type/intensity and orientation, then use `background_selector.py` against the registry and successful receipts.

The centralized policy balances semantic fit with visual satisfaction, loopability and caption readability:

- Normally hard-avoid an asset used in the latest 10 successful Shorts.
- Apply a strong recency penalty to uses 10–19 Shorts ago and a tapering penalty through 29 Shorts ago.
- Prefer never-used assets only when they are genuinely strong matches.
- Require two strong, fresh candidates for primary and backup.
- Require each new selection to have at least one registered rendition capable of 720×1280 crop-fill without upscaling; this is an availability gate, not rendition selection.
- If fewer than two exist, stop request creation and expand the registry through the planning-only Pexels tooling.
- Never select a poor match solely for age or novelty.

Primary and backup logical IDs must always differ. Do not put mutable usage counters in the registry; only successfully verified immutable `content/results/*.json` receipts are authoritative. Failed requests, renders and uploads do not count.

Registry expansion happens before the immutable request is created. Search the official Pexels API using a planning-only `PEXELS_API_KEY`, visually verify quality/license/readability/no text/no watermark, capture all usable `video_files`, assign the next stable `satisfying-NNN` ID under the registry lock, commit it, then create the request. Production reads checked-in metadata only and may resolve only the request's primary and backup.
