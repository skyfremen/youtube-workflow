# Wacky Dramas — Daily Growth Planner

This is the single canonical daily planning instruction for the aggressive Wacky Dramas Shorts growth system. It evolves the immutable request architecture; it must never restore a retired queue/planner model.

## Objective
Plan **up to 24 strong Wacky Dramas Shorts** for the target `Asia/Singapore` calendar day, using exact top-of-hour YouTube publication slots. Optimize for strong opportunities, not quota filling. Planning never uploads, renders, synthesizes TTS, or downloads production media.

## Planning date and same-day catch-up mode
The normal Daily Wacky Dramas Planner runs at **20:00 Asia/Singapore**. At or after 20:00, plan the **next Singapore calendar day**. All exact hourly slots from `00:00` through `23:00` are eligible before quality/diversity gates.

When manually run before 20:00 Asia/Singapore, use same-day catch-up for the **current Singapore calendar day**. Immediately before slot assignment and again before commit, re-read Singapore time and keep only exact top-of-hour slots at least **30 minutes in the future**. Never recreate, backfill, or shift elapsed/too-close hours. Example: at `01:35`, `02:00` is too close, so the first eligible slot is `03:00`.

Before catch-up, check `content/planning/YYYY-MM-DD.json`. If it exists, do **not** create a second plan or mutate immutable requests. Use the existing content IDs through `daily-growth-batch.yml` manual `workflow_dispatch` recovery. Record `planning_mode` as `normal_next_day` or `same_day_catch_up`; catch-up audit also records reference time, eligible slots and omitted elapsed/too-close slots.

## Canonical production contract
Preserve Wacky Dramas / @WACKYDRAMAS; one immutable content_id; requests under `content/requests`; verified receipts under `content/results`; Kokoro af_heart 1.75x; 720×1280/30fps H.264 + AAC; satisfying primary+backup backgrounds; existing opening card/subtitles/handle/SUBSCRIBE; durable upload intent, marker recovery and exact YouTube verification.

Read before planning: `planner/STORY_RULES.md`, `growth_config.py`, `growth_planner.py`, `background_policy.py`, `background_selector.py`, `media-library/backgrounds.json`, recent immutable requests/results, and valid `analytics/latest.json`.

## Funnel
Use progressive detail, not 120 full scripts:
`>=120 raw premises → hard rejection/duplicate filtering → ~60 qualified → ~36 semifinalists → concrete ending/outline/opening + >=5 truthful titles → title/hook competition → analytics adjustment → diversity + ~80/20 exploit/explore → <=24 winners → full 120–175s scripts → background selection → immutable schema-v3 requests`.
Hard rejection overrides scores. Reject unsafe, misleading, incoherent, weak-payoff, exposition-dependent, visually dependent, duplicate/near-duplicate or superficial swap concepts.

## Editorial and title competition
Use central `EDITORIAL_WEIGHTS` and `growth_planner.py`. For semifinalists develop an actual ending and at least five materially different truthful title candidates across controlled title styles. A sensational but inaccurate title is ineligible. The first spoken story-body line must add contradiction, discovery, consequence, urgent conflict or evidence; it must not repeat the opening card.

## YouTube metadata — planner-owned hard contract
For every winning story, ChatGPT must author the complete YouTube metadata **before** the immutable request is committed. Do not rely on the uploader to invent semantic metadata later.

Each schema-v3 `youtube` object must contain exactly:
- `title`: truthful curiosity-driven selected title, <=100 characters total and containing `#Shorts`.
- `description`: concise, story-specific copy. Prefer 1–3 short sentences: a curiosity/reveal-oriented summary that does not spoil the entire payoff, optionally followed by one natural engagement question. Do not use generic boilerplate like `An original Wacky Dramas story.` as normal production copy. Do not keyword-stuff or repeat the title verbatim.
- `hashtags`: 3–8 visible hashtags. Normally include `#Shorts` and `#WackyDramas`, then 1–6 genuinely relevant topic/story hashtags such as `#RelationshipDrama`, `#WorkplaceDrama`, `#FamilyDrama`, `#Storytime`. Avoid irrelevant trending hashtags and repetitive padding.
- `tags`: **4–12 explicit backend semantic tags without `#`**. These are planned per story and stored immutably. Include brand/topic/story-intent terms that genuinely describe the video, e.g. `wacky dramas`, `workplace drama`, `boss story`, `office conflict`, `evidence backfire`, `storytime`. Do not generate hundreds of SEO variants, misleading keywords, competitor/channel names, or cosmetic singular/plural duplicates.
- `category_id` and `made_for_kids` per the canonical production contract.

The uploader constructs final `snippet.tags` in this order: deterministic hidden recovery marker, planned `youtube.tags`, then de-duplicated hashtag words with the leading `#` removed. The hidden marker is backend-owned and must never be authored by ChatGPT or placed in the description.

Hard final-payload limits: title <=100 characters including `#Shorts`; final description <=5,000 UTF-8 bytes after missing request hashtags are appended; final `snippet.tags` <=500 YouTube combined-character cost including hidden marker + planned semantic tags + hashtag-derived tags; hashtags 3–8; semantic tags 4–12.

Before committing **every** winner, validate the exact local production payload:
```python
from upload import build_upload_body
build_upload_body(request_data, require_future=False)
```
This is authoritative for description assembly, tag de-duplication and final tag cost. If it fails, fix or reject the winner before commit. The backend repeats these checks before expensive generation and at upload time.

## Analytics learning
Use only valid/current `analytics/latest.json`. Never invent Studio-only metrics. Use the embedded analytics model and age-matched 24h/72h/7d cohorts. When analytics is disabled, use editorial/diversity fallback. When enabled, score historical attribute fit using canonical analytics-learning arithmetic and feed only normalized 0–100 analytics metrics into growth scoring. Do not feed raw views/retention/subscriber/share rates directly into the normalized scorer. Preserve smoothing, evidence confidence and exploration.

## Diversity
Apply diversity after ranking. Respect configured category/conflict/title-pattern/recent-similarity constraints. For a full 24-story day target roughly 19 exploit + 5 explore; exploration must still pass every hard quality/safety gate.

## AI-owned cache-first backgrounds
For every winner read `media-library/backgrounds.json`, successful receipts and `background_selector.py` recency/quality helpers. Semantically select two genuinely suitable, verified, fresh cached assets whenever possible; primary and backup must differ. Use `audit_ai_selection()` for mechanical quality/freshness/rendition safety. If fewer than two suitable cached assets exist, source only the missing Pexels assets, visually verify them, and create exactly one immutable `content/background-sourcing/YYYY-MM-DD.json` manifest for the day. Never invent provider IDs/URLs. Production ingestion uses PEXELS_API_KEY and fails closed before TTS/render/upload if ingestion fails. Respect `background_policy.py`: prefer 720×1280, then 30fps/lowest decode cost; max 1920×1080 or 1080×1920 equivalent; reject UHD/4K production selection.

## Immutable schema-v3 request
Only after winner selection/background planning write full scripts and requests. Add scheduled `publication` with timezone `Asia/Singapore` and exact UTC RFC3339 `publish_at`. Include the canonical compact `planning` object: plan_date, editorial components/score, analytics score/weight, final score, >=5 title candidates, selected title score, hook score, exploit/explore class, reason, similarity, controlled attributes and target duration. `visual.background_primary_id` and backup are the AI-selected cache IDs. `youtube.title`, `description`, `hashtags`, and `tags` are immutable planned metadata and must match the exact payload validated before commit.

## Daily planning audit
Create exactly one `content/planning/YYYY-MM-DD.json` for a new plan. Record planning mode/date, funnel counts, selected count/content IDs, diversity/exploration summary, analytics availability/model cohort/evidence/weight/fallback, background reuse/sourcing, metadata validation summary, and catch-up slot details where applicable. If no candidate clears hard gates, commit no weak filler.

## Commit and handoff
The content commit may contain only the new planning audit, new immutable requests and optional same-day sourcing manifest. Use commit message `[daily growth] YYYY-MM-DD`. ChatGPT planning ends after the content commit; the canonical Daily Growth Batch owns production and YouTube scheduling. Never directly upload/render/TTS from the planner.
