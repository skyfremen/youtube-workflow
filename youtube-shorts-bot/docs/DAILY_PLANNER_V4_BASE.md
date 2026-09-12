# Wacky Dramas — Daily Planner

This is the single canonical daily planning instruction for the Wacky Dramas production system. Its objective is aggressive subscriber and qualified-view growth without weakening the immutable request/recovery architecture or restoring a retired queue/planner model.

Business target: work aggressively toward **1,000 subscribers** and **10 million qualified public Shorts views within a rolling 90-day window**. Naming cleanup must never dilute this business objective; growth is business-purpose language here, not a technical component or architecture name.

## Objective
Plan **up to 24 strong Wacky Dramas Shorts** for the target `Asia/Singapore` calendar day, using exact top-of-hour YouTube publication slots. Optimize for strong opportunities, not quota filling. Planning never uploads, renders, synthesizes TTS, or downloads production media.

## Planning date and same-day catch-up mode
The normal Daily Wacky Dramas Planner runs at **20:00 Asia/Singapore**. At or after 20:00, plan the **next Singapore calendar day**. All exact hourly slots from `00:00` through `23:00` are eligible before quality/diversity gates.

When manually run before 20:00 Asia/Singapore, use same-day catch-up for the **current Singapore calendar day**. Immediately before slot assignment and again before commit, re-read Singapore time and keep only exact top-of-hour slots at least **30 minutes in the future**. Never recreate, backfill, or shift elapsed/too-close hours. At `01:35`, `02:00` is too close, so the first eligible slot is `03:00`.

Before catch-up, check `content/planning/YYYY-MM-DD.json`. If it exists, do **not** create a second plan or mutate immutable requests. Use the existing content IDs through `daily-production.yml` manual `workflow_dispatch` recovery. Record `planning_mode` as `normal_next_day` or `same_day_catch_up`; catch-up audit also records reference time, eligible slots and omitted elapsed/too-close slots.

## Canonical production contract
Preserve Wacky Dramas / @WACKYDRAMAS; one immutable content_id; requests under `content/requests`; verified receipts under `content/results`; story-aware approved Kokoro voice at 1.75x; 1080×1920/30fps H.264 High, yuv420p, BT.709 + AAC-LC 48kHz; satisfying primary+backup backgrounds; existing opening card/subtitles/handle/SUBSCRIBE; durable upload intent, marker recovery and exact YouTube verification.

Read before planning: `planning/STORY_RULES.md`, `planning/planning_config.py`, `planning/planning_engine.py`, `planning/planning_runner.py`, `analytics/analytics_learning.py`, valid/current `analytics/latest.json` and `analytics/model.json`, `media/background_policy.py`, `media/background_selector.py`, `docs/background-media-strategy.md`, `media-library/backgrounds.json`, and recent immutable requests/results.

`planning_config.py` and executable code are the source of truth for counts, thresholds, weights, diversity limits, analytics confidence and controlled values. If this prompt and current code ever disagree, stop and resolve the mismatch from the repository rather than reproducing stale prompt arithmetic.

## Responsibility boundary
ChatGPT / Work owns semantic and creative judgment: raw premise generation, semantic score components, originality/narrative assessment, semifinalist development, concrete endings/outlines/openings, truthful title candidates and their semantic components, final scripts, metadata, narrator perspective/tone, and semantic background choices subject to the retention-first mechanical policy.

Repository code owns deterministic policy. `planning_engine.py` owns hard rejection, duplicate/near-duplicate checks, weighted arithmetic, thresholds, semifinalist cap enforcement, analytics blending, exploit/explore and diversity selection, ranking, ordering and publication-slot calculation. `analytics_learning.py` owns normalized historical-attribute-fit arithmetic. Work must not manually substitute for those calculations when the canonical executable path is available.

## Funnel
Use progressive detail, not 120 full scripts:
`>=120 raw premises → canonical raw filtering → qualified candidates → ~36 developed semifinalists → concrete ending/outline/opening + >=5 truthful titles → canonical analytics/scoring/final selection → <=24 authoritative winners → full 120–175s scripts → background selection → immutable schema-v4 requests`.
Hard rejection overrides scores. Reject unsafe, misleading, incoherent, weak-payoff, exposition-dependent, visually dependent, duplicate/near-duplicate or superficial swap concepts.

The exact current counts come from `planning_config.py`; the numbers above describe the current architecture and are not permission to override newer code if configuration changes later.

## Mandatory canonical deterministic execution
Work must execute `planning/planning_runner.py` and consume its **actual returned result** at every deterministic checkpoint. Reading source code, reasoning through formulas, copying arithmetic into the prompt, or manually producing an equivalent result is not an acceptable substitute.

### Checkpoint 1 — raw filtering
After ChatGPT has generated the configured raw-candidate pool and supplied the required semantic/editorial fields, serialize the real candidates plus the actual recent-history comparison set into a temporary JSON input and run:

```bash
PYTHONPATH=youtube-shorts-bot python youtube-shorts-bot/planning/planning_runner.py \
  --stage raw-filter \
  --input /tmp/wacky-dramas-raw-input.json \
  --output /tmp/wacky-dramas-raw-result.json
```

Consume `result.qualified_candidates` from that file. Do not develop a hard-rejected candidate, rename it merely to bypass duplicate policy, or manually add a candidate that the runner rejected. ChatGPT may choose which qualified candidates to develop semantically, subject to the current configured semifinalist policy; the final checkpoint re-validates that every submitted semifinalist came from the qualified raw pool.

### Checkpoint 2 — final deterministic selection
After ChatGPT has creatively developed the semifinalists with the fields required by current code, serialize the **same raw pool**, developed semifinalists, plan date, recent-history set, and current analytics model into a second temporary input and run:

```bash
PYTHONPATH=youtube-shorts-bot python youtube-shorts-bot/planning/planning_runner.py \
  --stage final-select \
  --input /tmp/wacky-dramas-final-input.json \
  --output /tmp/wacky-dramas-final-result.json
```

When analytics is enabled, pass the current canonical `analytics/model.json` object as `analytics_model`. The runner itself executes `analytics.analytics_learning.score_candidate` and supplies the model's `analytics_evidence_count` to `planning_engine.evaluate`. A positive evidence count without the model is an error; do not manually inject a historical-fit score. When analytics is disabled/evidence is zero, canonical editorial/diversity fallback remains in force.

`result.selected` from the successful `final-select` execution is the authoritative winner set and order. Only those candidate IDs may proceed to full script/request creation. Do not insert an unselected candidate, resurrect a rejected candidate, bypass diversity, exceed the configured daily limit, or substitute a preferred story. If a selected story later becomes invalid during creative completion, correct the same selected candidate if the fix preserves its selected premise/attributes; otherwise update the deterministic input and rerun canonical final selection before creating immutable requests.

### Fail-closed rule
If either required runner execution cannot complete successfully, its JSON input is invalid, canonical code throws, analytics provenance is inconsistent, or output cannot be produced/consumed, **fail closed**. Do not approximate the result manually, do not reuse stale output, and do not commit manually reconstructed winners or final requests. `planning_runner.py` removes an existing output file before execution and writes a result only after successful canonical execution.

## Editorial and title competition
Use central `EDITORIAL_WEIGHTS` and the canonical execution path above. For semifinalists develop an actual ending and at least five materially different truthful title candidates across controlled title styles. A sensational but inaccurate title is ineligible. The first spoken story-body line must add contradiction, discovery, consequence, urgent conflict or evidence; it must not repeat the opening card.

## YouTube metadata — planner-owned hard contract
For every winning story, ChatGPT must author the complete YouTube metadata **before** the immutable request is committed. Do not rely on the uploader to invent semantic metadata later.

Each schema-v4 `youtube` object must contain exactly:
- `title`: truthful curiosity-driven selected title, <=100 characters total and containing `#Shorts`.
- `description`: concise, story-specific copy. Prefer 1–3 short sentences: a curiosity/reveal-oriented summary that does not spoil the entire payoff, optionally followed by one natural engagement question. Do not use generic boilerplate like `An original Wacky Dramas story.` as normal production copy. Do not keyword-stuff or repeat the title verbatim.
- `hashtags`: 3–8 visible hashtags. Normally include `#Shorts` and `#WackyDramas`, then 1–6 genuinely relevant topic/story hashtags such as `#RelationshipDrama`, `#WorkplaceDrama`, `#FamilyDrama`, `#Storytime`. Avoid irrelevant trending hashtags and repetitive padding.
- `tags`: **4–12 explicit backend semantic tags without `#`**. These are planned per story and stored immutably. Include brand/topic/story-intent terms that genuinely describe the video, e.g. `wacky dramas`, `workplace drama`, `boss story`, `office conflict`, `evidence backfire`, `storytime`. Do not generate hundreds of SEO variants, misleading keywords, competitor/channel names, or cosmetic singular/plural duplicates.
- `category_id` and `made_for_kids` per the canonical production contract.

The uploader constructs final `snippet.tags` in this order: deterministic hidden recovery marker, planned `youtube.tags`, then de-duplicated hashtag words with the leading `#` removed. The hidden marker is backend-owned and must never be authored by ChatGPT or placed in the description.

Hard final-payload limits: title <=100 characters including `#Shorts`; final description <=5,000 UTF-8 bytes after missing request hashtags are appended; final `snippet.tags` <=500 YouTube combined-character cost including hidden marker + planned semantic tags + hashtag-derived tags; hashtags 3–8; semantic tags 4–12.

Before committing **every** winner, validate the exact local production payload:
```python
from publishing.upload import build_upload_body
build_upload_body(request_data, require_future=False)
```
This is authoritative for description assembly, tag de-duplication and final tag cost. If it fails, fix or reject the winner before commit. The backend repeats these checks before expensive generation and at upload time.

## Analytics learning
Use only valid/current analytics state. `analytics/latest.json` contains the latest observation snapshot and evidence count; `analytics/model.json` is the canonical learned model produced by `analytics/analytics_learning.py`. Never invent Studio-only metrics. Use age-matched 24h/72h/7d cohorts. `analytics_evidence_count` is the evidence-equivalent confidence input; it is not a raw count of newly published Shorts. When analytics is disabled or the evidence count is zero, use editorial/diversity fallback. When enabled, the final runner executes canonical historical-attribute-fit scoring and feeds only normalized 0–100 analytics metrics into planning scoring. Do not feed raw views/retention/subscriber/share rates directly into the normalized scorer. Preserve smoothing, evidence confidence and exploration.

Do not substitute `video_count`, `published_video_count`, or `mature_video_count` for `analytics_evidence_count`.

## Diversity
Apply diversity after ranking through the canonical deterministic engine. Respect configured category/conflict/title-pattern/recent-similarity constraints. For a full 24-story day the current configuration yields roughly 19 exploit + 5 explore; exploration must still pass every hard quality/safety gate.

## Retention-first cache-first backgrounds
For every winner read `media-library/backgrounds.json`, successful private receipts, `media/background_selector.py`, `media/background_policy.py`, and `docs/background-media-strategy.md`.

The background is supporting visual motion; the story, narration, captions and punchline remain the primary content. Do **not** require literal story depiction. Prefer strong continuously moving, caption-safe footage such as cooking, baking, food preparation, satisfying processes, crafting, cleaning, assembly, POV movement and city/travel motion. Topic relevance is a secondary boost, not the dominant selection criterion.

Use the selector's retention/quality/recency helpers and `audit_ai_selection()` for mechanical safety. Select two distinct verified fresh registered logical assets whenever possible. Keep the current library: older topic-oriented or generic assets remain eligible when they are strong enough, but weak/static/overused clips rank lower rather than being bulk-deleted.

For a multi-Short daily plan, coordinate variety in the private planning layer. While allocating the day's winners, carry ephemeral `planned_asset_ids` and `planned_categories` (or the selector's current equivalent) so repeated assets and long runs of one visual category receive a soft penalty. Do not persist this batch scratch state in `production-runtime`. Cross-run recency/category/use history comes only from private immutable successful receipts.

If fewer than two suitable registered assets exist, source only the missing licensed Pexels assets, visually verify them, and create exactly one immutable `content/background-sourcing/YYYY-MM-DD.json` manifest for the day. Never invent provider IDs/URLs. Never source random gameplay or creator footage from YouTube, TikTok, Instagram, Twitch or similar platforms. `licensed_gameplay` is allowed only when commercial reuse rights and provenance are explicitly known and recorded. Production ingestion uses `PEXELS_API_KEY` and fails closed before TTS/render/upload if ingestion fails.

Respect `media/background_policy.py` for physical suitability. The production target is 1080×1920 at 30 fps. Physical selection is **smallest sufficient after the real 9:16 crop**: discard post-crop-insufficient renditions, prefer suitable native vertical and exact production dimensions, prefer FPS closest to 30, then prefer lower decode/network cost. Do not blindly select the provider original, largest resolution or largest file. A 1920×1080 landscape source is normally insufficient because its useful portrait crop is only about 607.5×1080; UHD/4K landscape is allowed when the post-crop quality floor genuinely requires it, but must not be selected when a smaller sufficient rendition exists.

If a sourcing manifest is required, its `plan_date` must exactly equal the daily planning audit `plan_date`. Every item in `candidates` must contain the exact `logical_id` being introduced and a non-empty `required_by_content_ids` list. Every listed content ID must be one of that day's new requests and must actually reference that `logical_id` as its primary or backup background.

The current schema-v4 visual contract freezes only logical primary/backup IDs. Do not invent segment, speed or mutable history fields in the request. Persistent segment-level reservations would require an intentional contract/schema evolution; never work around that by creating cross-run mutable state in the public runtime.

## Immutable schema-v4 request
Only after authoritative winner selection/background planning write full scripts and requests. Add scheduled `publication` with timezone `Asia/Singapore` and exact UTC RFC3339 `publish_at`. Include the canonical compact `planning` object: plan_date, editorial components/score, analytics score/weight, final score, >=5 title candidates, selected title score, hook score, exploit/explore class, reason, similarity, controlled attributes and target duration. The request's planning scores/selected title/class/publication must be copied from or remain consistent with the actual selected candidate returned by `final-select`; never manually recompute deterministic fields. `visual.background_primary_id` and backup are the private planner's selected registered logical IDs. `youtube.title`, `description`, `hashtags`, and `tags` are immutable planned metadata and must match the exact payload validated before commit.

## Daily planning audit and execution provenance
Create exactly one `content/planning/YYYY-MM-DD.json` for a new plan. It must contain the required core keys `plan_date`, `planning_mode`, `final_selected`, and `content_ids`, in addition to the existing funnel/diversity/analytics/background/metadata audit details.

Also record a `planning_execution` object containing:
- `raw_filter`: the `execution` object copied verbatim from the successful raw-filter runner output;
- `final_selection`: the `execution` object copied verbatim from the successful final-select runner output;
- `selected_candidate_ids`: the candidate IDs from final `result.selected`, in returned order.

The runner provenance includes the checked-out source SHA when available, implementation SHA-256, input SHA-256, deterministic stage and concrete canonical entry points. Do not replace this with a hand-authored boolean such as `executed: true`.

`content_ids` must exactly equal the stems of the new request filenames in the same commit, with no extra or missing IDs, and `final_selected` must equal the number of those requests. The number and order of full winner requests must derive from the authoritative selected candidate set. Record catch-up reference time, eligible slots, and omitted elapsed/too-close slots when applicable. If no candidate clears hard gates, commit no weak filler.

## Canonical narrator decision
For every final winner, determine whose experience drives the setup and payoff. Resolve `story.lead_gender` as `female` or `male`; do not count isolated relationship words or infer from a secondary character. Resolve ambiguous cases from the narrator whose perspective carries the setup and punchline. If that still cannot be established, explicitly choose the narrator perspective before creating the request.

Freeze `story.story_tone` and `narration.voice` in schema-v4:

- female + natural/general → `af_heart`
- female + funny/dramatic/expressive → `af_bella`
- male + natural/general → `am_echo`
- male + funny/dramatic/expressive → `am_fenrir`

Use one voice for the complete Short. Never randomly rotate voices or switch per sentence.

## Canonical visual-quality decision
White subtitles must remain readable throughout the used background. Logical primary/backup selection prioritizes caption-safe-region readability and continuous useful motion above literal topic match. Reject bright-white, flashing or highly cluttered caption regions unless the approved outline, shadow and subtle darkening treatment can protect them; prefer a better candidate rather than excessive darkening.

The frozen request contains only logical primary and backup IDs. Runtime validates those IDs, chooses the smallest physical rendition whose effective 9:16 crop can produce 1080×1920 within the bounded-upscale safeguard, checks the physical cache, downloads only when needed, probes the real file, normalizes once to production dimensions/FPS/codec when needed, and then renders from the production-sized input. Prefer suitable native vertical and exact production geometry; use UHD landscape only when crop geometry makes it necessary. Never substitute an unrelated third logical asset.

## Commit and handoff
The content commit may contain only the new planning audit, new immutable requests and optional same-day sourcing manifest. Temporary runner inputs/outputs are execution evidence sources and must not be committed as mutable production state. Use commit message `[daily production] YYYY-MM-DD`. ChatGPT planning ends after the content commit; `daily-production.yml` (**Daily Production**) owns production and YouTube scheduling. Never directly upload/render/TTS from the planner.
