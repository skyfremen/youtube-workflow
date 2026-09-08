# Wacky Dramas — Ad-hoc Story Planner

Generate exactly **one** original Wacky Dramas request and commit it as one new immutable JSON file:

`youtube-shorts-bot/content/requests/<content_id>.json`

Never edit, overwrite, or reuse an existing request. A correction or regenerated story requires a new `content_id`.

Before writing the request, read `STORY_RULES.md`, the verified `media-library/backgrounds.json`, and recent successful `content/results/*.json` receipts. Choose a strong, recently underused primary satisfying background and a different backup. Prefer the cache; research the public web only when the library lacks sufficient quality/diversity. Any newly added media must have current license/source metadata verified before it enters the registry.

The content ID format is:

`wd-YYYYMMDDTHHMMSS-topic-slug-random6`

Use UTC consistently for the timestamp. Use a concise lowercase topic slug and a collision-resistant six-character lowercase alphanumeric suffix.

The request must use schema version 2:

```json
{
  "schema_version": 2,
  "content_id": "wd-20260908T161000-boss-overtime-a7c42f",
  "channel": {
    "name": "Wacky Dramas",
    "handle": "@WACKYDRAMAS"
  },
  "story": {
    "category": "WORKPLACE",
    "story_type": "BACKFIRE",
    "hook": "My boss demanded unpaid overtime. It backfired.",
    "script": "FULL ORIGINAL STORY HERE",
    "card_emojis": ["💼", "😤", "📧", "😳", "🔥"]
  },
  "narration": {
    "engine": "kokoro",
    "voice": "af_heart",
    "speed": 1.75
  },
  "visual": {
    "background_primary_id": "satisfying-001",
    "background_backup_id": "satisfying-002"
  },
  "youtube": {
    "title": "My Boss Demanded Unpaid Overtime — It Backfired #Shorts",
    "description": "An original Wacky Dramas story.",
    "hashtags": ["#shorts", "#storytime", "#wackydramas"],
    "category_id": "24",
    "made_for_kids": false
  }
}
```

Do not include privacy, `publishAt`, direct media URLs, license/creator data, usage counters, fixed `duration_seconds`, old setup/payoff/CTA fields, music fields, queue slots, series fields, or Part 2 fields. The production workflow owns private-upload policy and runtime duration.
