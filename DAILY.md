# Wacky Dramas Daily

DAILY_WINNER_COUNT = 12

You are the creative planner. Deterministic code owns everything mechanical after your draft.

## Normal run

1. Read `content/context.json`.
2. Generate a broad candidate pool internally and compare it with `recent_story_cards` to reject semantic duplicates.
3. Select exactly `DAILY_WINNER_COUNT` strong, diverse winners.
4. Fully author only those winners. Do not persist rejected or runner-up ideas.
5. For every winner choose exactly 4 semantic emoji cues and exactly 1 `background_category` from `background_categories`.
6. Write exactly one new immutable file under `content/drafts/` containing all winners in one `winners[]` array.
7. Check the **Finalize Draft** workflow triggered by that exact draft commit.
8. If finalization succeeds, stop. Do not manually perform downstream production.

Use a collision-resistant filename such as `draft-YYYYMMDDTHHMMSS-<8 random lowercase hex>.json`. Never overwrite a draft.

## Diversity

Treat the winners as one editorial batch. Avoid near-duplicate premises, conflicts, twists, title patterns, and emotional beats inside the same draft. Each winner must still stand alone as a complete Wacky Dramas Short.

## Analytics interpretation

Use `analytics_summary` as evidence, not as a hard ranking of what to make next.

- Read `analytics_summary.learning` first. Respect its `stage`, `analytics_weight`, and `minimum_pattern_sample`.
- A category, tone, gender, duration bucket, or example with fewer checkpoint observations than `minimum_pattern_sample` is anecdotal. Do not treat one breakout Short as proof that its category or pattern is a winner.
- Prefer more mature evidence when sample sizes are adequate: `7d` > `72h` > `24h` > `6h`. Treat `6h` as an early test signal only.
- During `cold_start`, prioritize creative quality, diversity, and exploration. Roughly 70-80% of the batch should explore strong varied ideas and only 20-30% should deliberately lean into early positive signals.
- During `early_learning`, analytics may influence more selections, but preserve meaningful exploration and diversity.
- During `established`, use repeatable multi-video patterns more confidently while still avoiding formulaic repetition.
- `top_examples` are clues about hooks, conflicts, escalation, and payoff mechanisms. Do not clone their premises, titles, characters, or twists.
- Never sacrifice semantic-duplicate avoidance or batch diversity merely to exploit an analytics signal.

## Repair path

Use this only when **Finalize Draft** creates `content/failures/<draft_id>.json` for the draft you just wrote.

1. Read only the failed draft and matching failure file.
2. If `repairable` is false, stop and report the failure.
3. If the failure contains `violations[]`, repair every listed violation in one replacement draft. Use each violation's zero-based `winner_index` to identify the exact winner; `winner_title` is a human-readable cross-check. Change only those listed winners and preserve every unlisted winner exactly.
4. If `violations[]` is absent, follow the single top-level `field`, `observed_value`, and `required_constraint` exactly. Do not guess which winner failed.
5. Write a new immutable draft containing the complete winners array and set `supersedes_draft_id` to the immediately failed draft ID.
6. Recheck **Finalize Draft**.
7. Create at most 5 repair drafts after the initial draft.

## Winner rules

Each winner uses exactly the same creative contract as Ad-hoc:

- Immediate clear hook.
- Relatable conflict, escalation, payoff/reversal.
- One narrator.
- Roughly 120-175 seconds spoken content.
- `narration` follows the hook and should not deliberately repeat it.
- `payoff` should appear verbatim in `narration`; deterministic fallback uses the final narration sentence.
- `lead_gender`: `female` or `male`; fallback `female`.
- Approved `story_tone`: `natural`, `neutral`, `conversational`, `warm`, `calm`, `expressive`, `dramatic`, `comedy`, `sarcastic`, `dramatic_comedy`, `absurd`; fallback `natural`.
- Exactly four semantic emoji cues. Supported cues: `shock`, `surprise`, `argument`, `anger`, `betrayal`, `suspicion`, `secret`, `evidence`, `money`, `revenge`, `embarrassment`, `victory`, `funny`, `romance`, `panic`, `confusion`, `disbelief`, `warning`, `celebration`, `awkward`.
- Choose one supplied `background_category`; do not choose individual background IDs.
- No background music.

## Draft contract

Hard cutover: only the array shape is valid. Do not write singular `winner`, `draft_version`, `planning_mode`, IDs, timestamps, or publication scheduling fields.

```json
{
  "winners": [
    {
      "premise": "...",
      "category": "...",
      "conflict": "...",
      "twist": "...",
      "hook": "...",
      "narration": "...",
      "title": "...",
      "description": "...",
      "lead_gender": "female",
      "story_tone": "dramatic",
      "payoff": "...",
      "emoji_cues": ["shock", "evidence", "panic", "victory"],
      "background_category": "crafting"
    }
  ]
}
```

The draft must contain exactly `DAILY_WINNER_COUNT` winner objects. This count is a planner instruction only; `pipeline.py` intentionally accepts any non-empty `winners[]` array.
