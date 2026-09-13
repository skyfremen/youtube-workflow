# Wacky Dramas — Ad-hoc Planner

This is the canonical **Ad-hoc profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — shared bootstrap/materialization/replenishment-continuation/drift contract.
2. `planning/ADHOC_PLANNER_RULES.md` — Ad-hoc creative/identity/promotion rules.
3. `planning/STORY_RULES.md`.
4. `docs/background-media-strategy.md` — canonical shared background policy.

Repository code/configuration at current `main` is authoritative. Prefer the shared Git-first exact detached snapshot. If Git cannot obtain the exact current-main snapshot, use the canonical connector/API fallback; Git metadata is not required to execute deterministic planner Python. Use `profile=adhoc` from the live `planning.planner_contract` output.

For any background-specific or replenishment-continuation conflict with older profile-rule wording, the live planner contract, `docs/private/PLANNER_PROMPT.md` and `docs/background-media-strategy.md` supersede legacy wording; non-background Ad-hoc rules remain mandatory.

## Mandatory checkpoints

After exact SHA-pinned planner bootstrap, run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

An empty or insufficient active background registry is a normal `REPLENISH` state, not a terminal failure. If readiness is `REPLENISH`, execute the **shared automatic resumable replenishment procedure in `docs/private/PLANNER_PROMPT.md` exactly** before candidate finalization. In particular: resume compatible unfinished attempts; do not create duplicates; do not return merely because required Background Management discovery/readiness work is queued/in-progress; use the shared bounded continuation polling window; continue through visual review, readiness-manifest ingestion and the second Background Management run when they complete in-window; and report `DEFERRED_REPLENISHMENT` rather than failure only when a required bounded wait genuinely expires. A later manual/on-demand retry must resume that immutable attempt from its exact continuation point.

Once a matching immutable discovery result exists, continue through visual review and readiness-manifest creation in the **same planner invocation** whenever an exact-source visual channel is available. At that point `DEFERRED_REPLENISHMENT` is not a valid visual-review status. Follow the shared tool-adaptive evidence ladder with ChatGPT/Work-local exact-source review as the canonical path: use the exact immutable preview URLs directly, prefer native exact-source visual inspection when possible, and otherwise download the exact discovered media into local working storage and inspect representative frames/motion with available tooling. `media.preview_review_materializer` is the canonical repository helper when local Python outbound HTTP/media tooling works; local Python outbound HTTP is not itself a prerequisite because another exact download surface may feed the same local review. Any public review-evidence workflow is optional fallback only and must never block planning.

Do not bypass discovery results by guessing provider metadata. Do not move creative/editorial review into GitHub Actions. No separate manual seed/populate step is required.

## Sequence background contract

New candidates must use the current schema and `concatenated_fit_to_short` background contract exposed by `planning.planner_contract`.

- Freeze one primary ordered sequence and one backup ordered sequence.
- Each sequence contains exactly 2-3 distinct atomic clips; 3 is preferred.
- Freeze exact logical IDs, order, segment start and segment duration for every clip.
- Each selected range must be at least the live atomic minimum.
- Each sequence must provide the live required unique source coverage; prefer the live preferred coverage.
- Primary and backup sequences must be disjoint.
- Do not freeze playback rate; runtime concatenates the frozen sequence once and derives one overall rate after actual TTS duration is known.
- Never repeat a clip to fill time and never plan intentional loops.
- Runtime may fail over only from the entire frozen primary sequence to the entire frozen backup sequence; it may not mix sequences or creatively substitute footage.
- Old pre-reset backgrounds were deleted; do not reference, recreate or assume hidden legacy IDs.
- Avoid repeated assets, exact sequences, categories and substantially overlapping temporal ranges using verified private receipt history.

After authoring the complete five-candidate ranked pool, run:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile adhoc \
  --pool /tmp/wacky-adhoc-pool.json \
  --rules-source-sha <rules_source_sha> \
  --verify-git-head
```

In connector/API fallback omit `--verify-git-head`. The gate requires all five candidates PASS. The compatibility wrapper `planning.adhoc_precommit` remains available for existing callers but contains no independent validation logic.

The final immutable pool bytes must exactly match the successful `draft_sha256`. Manual checks, downstream admission/promotion or GitHub Actions are not substitutes for planner-time pre-commit.

For `manual_on_demand`, distinct same-date invocations may coexist. For `scheduled_daily`, preserve current once-per-date uniqueness. Every promoted Ad-hoc request remains immediate-public according to the live profile contract.

ChatGPT/Work remains creative/editorial owner. Private promotion preserves frozen rank order; public runtime executes statelessly.
