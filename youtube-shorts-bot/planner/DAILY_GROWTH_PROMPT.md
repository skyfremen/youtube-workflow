# Wacky Dramas — Daily Growth Planner

This is the single canonical daily planning instruction for the aggressive Wacky Dramas Shorts growth system. It evolves the immutable request architecture; it must never restore a retired queue/planner model.

## Objective

Plan **up to 24 strong Wacky Dramas Shorts** for the next `Asia/Singapore` calendar day, one intended YouTube publication slot per hour from `00:00` through `23:00`.

Optimize for **24 strong opportunities**, not quota filling. If fewer than 24 stories pass hard quality, safety, originality, duration, truthfulness and background gates, create fewer requests and explain the shortfall in the planning audit.

Planning must never upload, render, synthesize TTS, or download production media.

## Canonical production contract

Preserve all of these invariants:

- Channel `Wacky Dramas`, handle `@WACKYDRAMAS`.
- One immutable `content_id` per story.
- Requests: `youtube-shorts-bot/content/requests/<content_id>.json`.
- Verified immutable receipts: `youtube-shorts-bot/content/results/<content_id>.json`.
- Kokoro `af_heart` at `1.75` speed.
- 720×1280, 30 fps, H.264 video and AAC narration.
- Satisfying background video with immutable primary + backup logical IDs.
- Existing opening card, subtitles, handle and SUBSCRIBE treatment.
- Durable upload intent, marker recovery, exact YouTube verification, and receipt only after verified success.

Read before planning:

- `planner/STORY_RULES.md`
- `growth_config.py`
- `growth_planner.py`
- `background_policy.py`
- `background_selector.py`
- `media-library/backgrounds.json`
- recent immutable requests/results
- `analytics/latest.json` when it exists and is valid

## Funnel

Use progressive detail. Do **not** write 120 full scripts.

```text
>=120 distinct raw premises
→ hard rejection / duplicate filtering
→ editorial scoring
→ roughly 60 qualified ideas naturally, without keeping weak fillers
→ roughly 36 semifinalists
→ actual ending + stronger outline + opening line + >=5 titles each
→ title + hook competition
→ confidence-weighted analytics adjustment
→ diversity + approximately 80/20 exploit/explore
→ <=24 winners
→ full 120–175 second scripts
→ AI cache-first background selection / optional sourcing
→ immutable schema-v3 production requests
```

Hard rejection always overrides numerical scores. Reject malformed, unsafe, misleading, incoherent, weak-duration, missing-payoff, exposition-dependent, visually dependent, exact duplicate, near duplicate, or superficial name/relationship-swap concepts.

## Raw premise breadth

Explore genuinely different idea spaces across relationship, dating, marriage, betrayal, family, inheritance, money, workplace, revenge, friendship, wedding, entitled-person conflict, neighbors, secrets, discoveries, social conflict, housing/property, parenting, moral dilemma, kindness, misunderstanding, hidden identity, consequences, reversals and wildcard concepts.

Vary conflict type, emotional tone, protagonist/antagonist roles, setting, escalation, hook structure, title structure and ending structure. A different name, gender, location or relationship label is not a different premise.

Each raw candidate needs enough structured information to judge protagonist/context, inciting incident, conflict, escalation potential, likely payoff, category and tags.

## Editorial cold-start scoring

Use the central `EDITORIAL_WEIGHTS` in `growth_config.py`:

- Opening hook potential: 20
- Curiosity gap: 20
- Emotional stakes: 15
- Escalation potential: 10
- Payoff quality: 10
- Title potential: 10
- Broad relatability: 5
- Originality: 5
- Narration suitability: 5

Score components 0–100 and let `growth_planner.py` own weighted arithmetic.

## Semifinalists, titles and opening line

For roughly the top 36, develop a short but concrete outline with opening situation, first reveal, escalation, turning point and actual ending/payoff. Add an opening spoken story-body line, controlled attributes, and **at least five materially different truthful title candidates**.

Rotate title patterns: hidden revelation, discovery, normal→abnormal, decision→consequence, countdown, underestimated narrator, moral conflict, delayed revelation, contradiction and consequence-first. Do not produce five cosmetic rewrites or repeatedly use a generic “Then THIS Happened” formula.

A more sensational but inaccurate title is ineligible. Never promise a person, crime, reveal, consequence or emotional event that the story does not contain.

The title creates the first unanswered question. The first spoken story-body line must add a contradiction, discovery, consequence, urgent conflict or evidence immediately. Avoid generic history such as “for context”, relationship-length introductions or family-tree exposition unless essential.

The renderer narrates the short opening card hook separately. `story.script` must still begin strongly after the card disappears and must not repeat the card wording.

## YouTube metadata limits — hard planner gate

ChatGPT must account for YouTube metadata limits **while generating every winning request**, not leave them for the backend to discover after planning.

Hard limits for the final production payload:

- `youtube.title`: maximum **100 characters total**, including `#Shorts`. Prefer meaningful titles comfortably below the hard ceiling instead of targeting exactly 100.
- Final YouTube description: maximum **5,000 UTF-8 bytes** after production appends any missing request hashtags. Keep the authored `youtube.description` concise and leave generous headroom; do not approach the 5,000-byte ceiling intentionally.
- Final YouTube `snippet.tags`: maximum **500 combined characters/cost** across all tags. This includes the deterministic hidden Wacky Dramas recovery marker plus every request hashtag after the leading `#` is removed. Tags containing spaces consume extra encoded cost in the production calculation.
- Keep `youtube.hashtags` to the schema-allowed **3–8 concise, relevant hashtags**. Do not pad tags for SEO or consume the 500-character budget unnecessarily.

Before writing or committing **any** immutable winner request, validate the exact local upload payload using the same production code:

```python
from upload import build_upload_body
build_upload_body(request_data, require_future=False)
```

This validation is local/read-only. It must happen during planning before the content-only commit and does not contact YouTube.

`build_upload_body(..., require_future=False)` is authoritative for the final description/tag cost because it applies the same deterministic hashtag appending and hidden recovery marker used by production. If it raises for description length, tag length, privacy/publication metadata, or another upload-contract error, **fix or reject that winner before committing it**. Never create an over-limit immutable request and rely on the GitHub production batch to fail later.

The backend still repeats these checks as a fail-fast safety net before expensive generation and again at upload time; planner-side validation is the first line of defense.

## Analytics learning

Use `analytics/latest.json` only when valid and current enough to help. The collector records API-available public views, `engagedViews` (used as qualified/engaged Shorts views), average view duration, average view percentage, likes, comments, shares and subscribers when exposed.

The targeted Analytics API path does **not** provide the exact Studio “viewed vs swiped away” control used in the UI. Never invent it. The system may use the explicitly named `engaged_view_rate = engagedViews / views` as an API-available continuation proxy, but must not relabel that proxy.

Use `growth_video_count`, not private/test receipt count, when determining confidence. Let `growth_planner.analytics_weight()` increase analytics influence gradually from zero while retaining editorial/exploration contribution. Missing, empty, malformed, stale or unavailable analytics means a documented editorial fallback, never fabricated values.

Prefer normalized rates and comparable public-age windows. Use 24h, 72h and 7d snapshots where available. Do not compare a two-hour-old Short directly with a seven-day-old Short using raw views.

Learn from controlled attributes such as category, subtype, conflict, primary emotion, protagonist/antagonist roles, opening style, title style, ending style and duration. Use sample size, recency and smoothing; one viral outlier must not monopolize tomorrow’s plan.

## Diversity and exploration

Apply diversity after ranking rather than taking a blind numerical top 24. Default constraints from `growth_config.py` include approximately:

- max 4 from one major category
- max 2 with essentially the same conflict
- max 3 with one title pattern
- no strong recent near duplicate
- avoid identical ending/title patterns in adjacent slots
- avoid excessive protagonist/antagonist repetition

For a full 24-story day, target roughly 19 exploit + 5 explore selections. Exploratory candidates must still clear every hard quality/safety gate.

## AI-owned cache-first background selection

Background semantic matching is owned by **ChatGPT during planning**, not by a blind production fallback.

For every final winner:

1. Read `media-library/backgrounds.json` first. This is the background cache.
2. Read successful immutable receipts and use `background_selector.py` recency/quality helpers so backgrounds used within the last 10 successful Shorts are hard-avoided and older recent use is penalized.
3. Semantically compare the actual story with cached asset titles, visual tags, motion type/intensity, orientation, visual satisfaction, loopability and caption readability. Do not rely only on literal keyword overlap when the meaning is obvious.
4. Prefer cached assets whenever **two genuinely suitable, active, verified, fresh assets** exist. Do not search the web merely for novelty.
5. The selected cached primary and backup must differ. Use `audit_ai_selection()` as the mechanical quality/freshness/rendition safety gate; its metadata semantic score is informational, while ChatGPT owns the final semantic-fit judgment.
6. A cached asset is production-ready only if it has a rendition accepted by `background_policy.py`.

### Cache miss: source only what is missing

If the cache cannot provide two genuinely suitable fresh backgrounds, ChatGPT must source only the missing background(s) **before the immutable request is finalized**.

Current automatic ingestion provider: **Pexels**. Use public web research/preview inspection to find an appropriate Pexels video. Do not invent a provider ID or URL. Visually inspect the available preview or representative frames and confirm the clip is suitable, has no embedded text/watermark, leaves captions readable, and has satisfying continuous/loopable motion.

For each new Pexels candidate use the deterministic logical ID:

`Satisfying ID = satisfying-px-<Pexels video ID>`

Example: Pexels video `424242` becomes `satisfying-px-424242`.

When at least one new background is required, create exactly one immutable sourcing manifest for the day:

`youtube-shorts-bot/content/background-sourcing/YYYY-MM-DD.json`

Schema:

```json
{
  "schema_version": 1,
  "plan_date": "YYYY-MM-DD",
  "provider": "Pexels",
  "candidates": [
    {
      "logical_id": "satisfying-px-424242",
      "provider_asset_id": "424242",
      "source_page": "https://www.pexels.com/video/...-424242/",
      "title": "Concise visual description",
      "visual_tags": ["satisfying", "cleaning", "repetitive-motion"],
      "motion_type": "continuous",
      "motion_intensity": "medium",
      "loopability_score": 90,
      "visual_satisfaction_score": 92,
      "caption_readability_score": 90,
      "verified_preview": true,
      "required_by_content_ids": ["<content_id>"]
    }
  ]
}
```

Set `verified_preview=true` only after actual AI visual/source review. Every sourced logical ID must be referenced by at least one request in the same daily growth commit, and every `required_by_content_ids` entry must actually reference that ID as primary or backup.

The backend batch uses its GitHub-held `PEXELS_API_KEY` to fetch official Pexels `video_files`, verify an acceptable physical rendition exists, append the asset to `backgrounds.json`, validate the cache, and persist that cache append **before any TTS/render/upload work**. If ingestion fails, the batch fails closed before expensive production. Production never searches for an unrelated third background.

### Rendition cost rule

The final Short is permanently 720×1280/30fps, so production must not download a 1440p/4K source simply to scale it down.

`background_policy.py` enforces:

- prefer exact 720×1280 when available
- then prefer 30fps and the lowest decode/download cost
- maximum source budget: 1920×1080 or 1080×1920 equivalent (2,073,600 pixels)
- allow at most 1.25× crop-fill upscale, which permits a normal 1920×1080 landscape clip to fill the portrait crop
- reject UHD/4K renditions from production selection
- generic provider-original fallback is allowed only if the original itself fits the same source budget

The registry may retain higher-resolution provider metadata for audit, but `media_resolver.py` must never select or download those UHD entries.

## Immutable schema-v3 request

Only after final story selection and background resolution planning write full scripts and immutable requests. Each selected request adds:

```json
"publication": {
  "mode": "scheduled",
  "timezone": "Asia/Singapore",
  "publish_at": "<UTC RFC3339 timestamp ending Z>"
}
```

Assign unique local hourly slots `00:00` through `23:00`; convert them to exact UTC timestamps. The schedule lives inside the immutable request—there is no mutable publication queue.

Each request also includes a compact `planning` object containing:

- `plan_date`
- editorial component scores and overall score
- analytics score (`null` when unavailable) and analytics weight
- final score
- >=5 title candidates with component scores/style/truthfulness
- selected title score
- hook score
- `selection_class` (`exploit` or `explore`)
- selection reason
- similarity result including `max_recent_similarity`
- controlled attributes: subtype, conflict, primary emotion, protagonist role, antagonist role, opening style, title style, ending style
- target duration in the 120–175 second range

The request's `visual.background_primary_id` and `visual.background_backup_id` are the cache IDs chosen by ChatGPT. Once committed, production may use only those two logical assets.

## Planning audit and commit

Create exactly one compact immutable daily audit:

`youtube-shorts-bot/content/planning/YYYY-MM-DD.json`

It must at minimum record the funnel counts, analytics confidence/weight/fallback reason, duplicate rejections, diversity substitutions, exploit/explore counts, final selected count, exact `content_ids`, background cache-hit count, background sourced count, and any background shortfall reason.

Create 1–24 new immutable request files in the same **content-only** commit. Add the optional same-day background sourcing manifest only when the cache genuinely misses. Never modify an existing request, result, recovery record, prior planning audit or prior sourcing manifest. Never mix implementation/code changes into that content commit.

The commit message must begin:

`[daily growth] YYYY-MM-DD`

That marker routes the commit to the canonical batch production workflow. Planning itself performs no YouTube action and does not download production media.

## Production cost discipline

Do not preflight/download production media, run TTS, render or upload for rejected candidates. Only final winners reach expensive production. Cache ingestion is metadata/API work and happens before rendering. The renderer receives only the lowest-cost production-suitable rendition of the immutable primary or backup ID.

## Failure behavior

- Fewer than 24 qualified winners: create fewer, never lower hard gates.
- Missing analytics: editorial fallback with reason.
- One malformed winner: reject it before request creation.
- YouTube metadata over limit or invalid upload contract: repair/reject the winner during planning before immutable request creation; never defer this to production.
- Cache miss: source reviewed Pexels candidate(s), write the immutable sourcing manifest, and let backend ingestion validate/store them before rendering.
- Pexels ingestion/key/rendition failure: fail closed before TTS/render/upload; never pick a random background.
- Partial batch failure: do not alter another immutable request or blindly retry an upload. Durable per-content intent/recovery evidence remains authoritative.
- Upload accepted but later step fails: recovery must resolve the existing video before any insert is considered.
- Receipt is created only after YouTube state matches the immutable publication contract and render evidence.
