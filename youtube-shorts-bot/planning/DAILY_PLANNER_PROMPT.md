# Wacky Dramas — Daily Planner

This is the canonical **Daily profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — shared bootstrap/materialization/drift contract.
2. `planning/DAILY_PLANNER_RULES.md` — Daily creative/schedule/diversity/promotion rules.
3. `planning/STORY_RULES.md`.
4. `docs/background-media-strategy.md` — canonical shared background policy.

Repository code/configuration at current `main` is authoritative. Prefer the shared **Git-first exact detached snapshot**. If Git cannot obtain the exact current-main snapshot, use the canonical **connector/API fallback**; Git metadata is not required to execute deterministic planner Python. Use `profile=daily` from the live `planning.planner_contract` output.

For any **background-specific** conflict with older profile-rule wording, the live planner contract plus `docs/background-media-strategy.md` supersede legacy single-source, schema-v5/v6, `selection_enabled`, emergency-default, short-loop, or planner-frozen-playback wording; non-background Daily rules remain mandatory.

## Mandatory checkpoints

After exact SHA-pinned planner bootstrap, run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

An empty active background registry is a normal `REPLENISH` state, not a terminal failure. If readiness is `REPLENISH`, **automatically complete the canonical replenishment path before candidate finalization**:

1. consume exact total/category/duration deficits;
2. request deterministic provider discovery by creating exactly one new immutable file under `youtube-shorts-bot/content/background-sourcing/discovery-requests/` with fields `schema_version=1`, current `plan_date`, a unique stable `request_id` matching `dr-[A-Za-z0-9-]{8,96}`, and `max_candidates=48`; commit it with a `[media discovery]` message;
3. Background Management uses the repository's `media.pexels_discovery` helper and the GitHub-held `PEXELS_API_KEY` only for provider/API discovery. It filters out clips below the live atomic minimum and clips without a production-suitable rendition, then commits the matching immutable result under `youtube-shorts-bot/content/background-sourcing/discovery-results/`. This stage is deterministic eligibility filtering only and must never set `verified_preview=true`, assign final semantic metadata, or make editorial choices;
4. refresh current `main` and consume the matching discovery result. If the result has not been committed yet, inspect Background Management status and refresh again within the current planning run; never fabricate provider IDs, durations, renditions, or preview URLs;
5. review actual visual preview evidence from the discovery result for every proposed source before `verified_preview=true`, following the live `media_readiness.preview_review` contract and `docs/background-media-strategy.md`; **full-length/end-to-end playback is not required**, but metadata-only review is insufficient; if one candidate has no accessible visual preview evidence or is visually unsuitable, reject it and continue through the remaining discovery candidates rather than failing the whole replenishment attempt;
6. create exactly one immutable readiness manifest from visually approved candidates only;
7. commit that manifest so Background Management performs official API re-enrichment/persistence and reserve fallback;
8. refresh current `main`;
9. rerun contract + readiness;
10. if deficits remain, create a new immutable discovery request/result/review/readiness attempt; continue Daily planning only after `PASS`.

Do not bypass the discovery result by guessing duration from public search pages. Do not move creative/editorial review into GitHub Actions. No separate manual seed/populate step is required.

## Sequence background contract

New candidates must use the current schema and `concatenated_fit_to_short` background contract exposed by `planning.planner_contract`.

- Freeze one **primary ordered sequence** and one **backup ordered sequence**.
- Each sequence contains exactly 2-3 distinct atomic clips; 3 is preferred.
- Freeze exact logical IDs, order, segment start and segment duration for every clip.
- Each selected range must be at least the live atomic minimum (currently 60 seconds).
- Each sequence must provide 210-300 seconds total unique source coverage; 240-300 seconds is preferred.
- Primary and backup sequences must be disjoint.
- Do **not** freeze playback rate; runtime concatenates the frozen sequence once and derives one overall rate after actual TTS duration is known.
- Prefer coherent retention-first progressions across cooking/baking/food-prep/satisfying/crafting/cleaning/assembly/POV/city-motion/licensed-gameplay footage.
- Never repeat a clip to fill time and never plan intentional loops.
- Runtime may fail over only from the entire frozen primary sequence to the entire frozen backup sequence; it may not mix sequences or creatively substitute footage.
- Old pre-reset backgrounds were deleted; do not reference, recreate, or assume hidden legacy IDs.
- Avoid repeated assets, exact sequences, categories and substantially overlapping temporal ranges using verified private receipt history.

After authoring/final-ranking the complete Daily pool, run:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile daily \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha <rules_source_sha> \
  --verify-git-head
```

In connector/API fallback omit `--verify-git-head`. The gate requires **all 36 candidates PASS** before immutable commit. The compatibility wrapper `planning.daily_precommit` remains available for existing callers but contains no independent validation logic.

The final immutable pool bytes must exactly match the successful `draft_sha256`. Manual checks, downstream admission/promotion, or GitHub Actions are **not substitutes for planner-time pre-commit**.

ChatGPT/Work remains creative/editorial owner. Private workflows validate/promote mechanically; public runtime executes statelessly.
