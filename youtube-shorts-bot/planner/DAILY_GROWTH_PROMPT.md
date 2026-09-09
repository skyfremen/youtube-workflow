# Wacky Dramas — Daily Growth Planner

This is the single canonical daily planning instruction for the aggressive Wacky Dramas Shorts growth system. It evolves the immutable request architecture; it must never restore the retired legacy queue/planner model.

## Objective

Plan **up to 24 strong Wacky Dramas Shorts** for the next `Asia/Singapore` calendar day, one intended YouTube publication slot per hour from `00:00` through `23:00`.

Optimize for **24 strong opportunities**, not quota filling. If fewer than 24 stories pass hard quality, safety, originality, duration and truthfulness gates, create fewer requests and explain the shortfall in the planning audit.

Planning must never upload, render, synthesize TTS, download production media, or create success receipts.

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
→ validation/background selection
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

The title creates the first unanswered question. The first spoken story-body line must add a contradiction, discovery, consequence, urgent conflict or evidence immediately. Avoid generic history such as “for context”, “this happened a few years ago”, relationship-length introductions or family-tree exposition unless essential.

The renderer narrates the short opening card hook separately. `story.script` must still begin strongly after the card disappears and must not repeat the card wording.

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

## Immutable schema-v3 request

Only after final selection write full scripts and immutable requests. Each selected request adds:

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

Use controlled enums from `growth_config.py`; do not invent an unbounded tag taxonomy.

## Planning audit and commit

Create exactly one compact immutable daily audit:

`youtube-shorts-bot/content/planning/YYYY-MM-DD.json`

It must at minimum record the funnel counts, analytics confidence/weight/fallback reason, duplicate rejections, diversity substitutions, exploit/explore counts, final selected count, and the exact `content_ids` created in the same commit. It may summarize rejected candidates instead of permanently storing all 120 verbose drafts.

Create 1–24 new immutable request files in the same **content-only** commit. Never modify any existing request, result, recovery record or prior planning audit. Never mix implementation/code changes into that content commit.

The commit message must begin:

`[daily growth] YYYY-MM-DD`

That marker routes the commit to the canonical batch production workflow. The planning job itself performs no YouTube action.

## Backgrounds and production cost

Do not preflight/download production media, run TTS, render or upload for rejected candidates. Only final winners reach expensive production.

For each winner use the existing verified background registry and centralized selector. Primary and backup must differ and be strong/fresh. If two acceptable verified assets are unavailable, complete safe planning-time registry expansion before creating that request; never let production mutate the registry or choose a different logical background.

## Failure behavior

- Fewer than 24 qualified winners: create fewer, never lower hard gates.
- Missing analytics: editorial fallback with reason.
- One malformed winner: reject it before request creation.
- Partial batch failure: do not alter another immutable request or blindly retry an upload. Durable per-content intent/recovery evidence remains authoritative.
- Upload accepted but later step fails: recovery must resolve the existing video before any insert is considered.
- Receipt is created only after YouTube state matches the immutable publication contract and render evidence.
