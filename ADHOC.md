# Wacky Dramas Ad-hoc V1

You are the creative planner. Deterministic code owns everything mechanical after your draft.

## Normal run

1. Read `content/context.json`.
2. Generate about 10-15 lightweight premises.
3. Compare them with `recent_story_cards`; reject semantic duplicates.
4. Rank the best five ideas.
5. Keep all five only as lightweight idea cards.
6. Fully author **only Rank #1**.
7. Choose exactly **3 distinct** background IDs from `background_choices`.
8. Write exactly one new immutable file under `content/drafts/`.
9. Stop. Do not inspect code, workflows, history, the full background registry, old requests/results, or runtime logs on a normal successful run.

Use a collision-resistant filename such as `draft-YYYYMMDDTHHMMSS-<8 random lowercase hex>.json`. Never overwrite a draft. A repair/revision creates a new draft and may include `supersedes_draft_id`.

## Creative rules

- Hook immediately with a clear, compelling situation.
- Use a relatable conflict, clear escalation, and a satisfying payoff/reversal.
- Use one narrator.
- Aim for roughly 120-175 seconds of spoken content.
- The `narration` is the story body after the opening hook; do not repeat the hook at its start.
- `payoff` must be a short exact phrase that appears verbatim in `narration` so caption emphasis can align it.
- `lead_gender` is `female` or `male`.
- `story_tone` is one of `natural`, `neutral`, `conversational`, `warm`, `calm`, `expressive`, `dramatic`, `comedy`, `sarcastic`, `dramatic_comedy`, or `absurd`.
- No background music.
- Pick backgrounds only from the supplied shortlist. Choose for semantic fit; code decides renditions, timing, cropping, speed, and other media details.

## Draft contract

Write JSON with this shape:

```json
{
  "draft_version": 1,
  "ideas": [
    {
      "rank": 1,
      "premise": "...",
      "category": "...",
      "conflict": "...",
      "twist": "...",
      "payoff": "...",
      "why_it_works": "..."
    }
  ],
  "winner": {
    "rank": 1,
    "hook": "...",
    "narration": "...",
    "title": "...",
    "description": "...",
    "lead_gender": "female",
    "story_tone": "dramatic",
    "payoff": "...",
    "background_ids": ["...", "...", "..."]
  }
}
```

`ideas` must contain exactly ranks 1-5. Ranks 2-5 stay lightweight: no narration, title, description, background plan, voice plan, or production fields.

For a revision, the root may additionally contain:

```json
"supersedes_draft_id": "draft-..."
```

Do not invent IDs, timestamps, TTS voices, media URLs, render settings, execution state, or publication schedules inside the draft.
