# Wacky Dramas — Daily Planner

This is the canonical **Daily profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — shared bootstrap/materialization/replenishment-continuation/drift contract.
2. `planning/DAILY_PLANNER_RULES.md` — Daily creative/schedule/diversity/promotion rules.
3. `planning/STORY_RULES.md`.
4. `docs/background-media-strategy.md` — canonical shared background policy.

Repository code/configuration at current `main` is authoritative. For ChatGPT/Work, use the canonical shared connector-first bootstrap in `docs/private/PLANNER_PROMPT.md`: resolve current `main` through the authorized GitHub connector/API, freeze the exact `rules_source_sha`, materialize and verify the exact-SHA manifest/files, then execute planner Python. Do not attempt shell Git before connector/API acquisition and do not require `.git`. Use `profile=daily` from the live `planning.planner_contract` output.

For any background-specific or replenishment-continuation conflict with older profile-rule wording, the live planner contract, `docs/private/PLANNER_PROMPT.md` and `docs/background-media-strategy.md` supersede legacy wording; non-background Daily rules remain mandatory.

### Shared materialization completion gate

Do not duplicate or replace bootstrap logic in this profile. Execute the shared **canonical ChatGPT/Work materialization completion gate** in `docs/private/PLANNER_PROMPT.md` before any planner checkpoint. `MATERIALIZATION_BLOCKED` is valid only under the shared named connector/API failure or verifier-`FAIL` conditions; Git/DNS/checkout failures are not valid ChatGPT/Work blockers.

## Mandatory checkpoints

After exact SHA-pinned planner bootstrap, run locally in ChatGPT/Work:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

An empty or insufficient active background registry is a normal `REPLENISH` state, not a terminal failure. If readiness is `REPLENISH`, execute the **shared automatic resumable replenishment procedure in `docs/private/PLANNER_PROMPT.md` exactly** before candidate finalization. In particular: resume compatible unfinished attempts; do not create duplicates; do not return merely because required Background Management discovery/readiness work is queued/in-progress; use the shared bounded continuation polling window; continue through visual review, readiness-manifest ingestion and the second Background Management run when they complete in-window; and report `DEFERRED_REPLENISHMENT` rather than failure only when a required bounded wait genuinely expires. A later scheduled Daily invocation must resume that immutable attempt from its exact continuation point rather than creating a parallel replenishment attempt.

Once a matching immutable discovery result exists, continue through visual review and readiness-manifest creation in the **same planner invocation**. Follow the shared artifact-first evidence contract in `docs/private/PLANNER_PROMPT.md` and `docs/background-media-strategy.md`:

1. Require a matching run-scoped `content/background-sourcing/review-evidence/<request_id>-run-*.json` produced by private Background Management. If the required evidence run is still legitimately building/uploading evidence, use the shared bounded continuation window rather than returning early.
2. Use the newest usable index's exact workflow-run and artifact ID/name/digest to retrieve `background-review-evidence-<request_id>-<run_id>` through the GitHub connection. Download/extract it locally, verify `evidence-manifest.json` against the indexed SHA-256 and immutable discovery result, then inspect the actual `*/contact-sheet.jpg` pixels. GitHub generated the frames but did **not** approve them; ChatGPT/Work owns approval and semantic metadata.
3. If an artifact is expired/unavailable or individual evidence is insufficient, regenerate a run-scoped evidence artifact when possible and exhaust native exact-source Pexels inspection plus exact local preview-image/video transfer, including `media.preview_review_materializer --input-dir` where applicable. Reject inaccessible candidates individually and continue reserves.
4. `EVIDENCE_ACCESS_BLOCKED` is legal only after usable private indexed artifacts plus all other trustworthy exact-source visual channels are unavailable for the remaining candidates needed for readiness. A successful required Background Management evidence run with a missing/mismatched artifact/index is `REVIEW_EVIDENCE_TRANSPORT_FAILED`, not a creative failure.
5. If too few candidates survive, continue the next immutable discovery attempt under the same deficits; never weaken `verified_preview`.

Do not bypass discovery results by guessing provider metadata. Private GitHub Actions may perform exact-source transport/download/FFmpeg contact-sheet generation, but must never set `verified_preview`, approve/reject candidates, assign semantic metadata, or author the readiness manifest. No separate manual seed/populate step is required.

## Sequence background contract

New candidates must use the current schema and `concatenated_fit_to_short` background contract exposed by `planning.planner_contract`.

- Freeze one primary ordered sequence and one backup ordered sequence.
- Each sequence contains exactly 2-3 distinct atomic clips; 3 is preferred.
- Freeze exact logical IDs, order, segment start and segment duration for every clip.
- Each selected range must be at least the live atomic minimum.
- Each sequence must provide the live required unique source coverage; prefer the live preferred coverage.
- Primary and backup sequences must be disjoint.
- Do not freeze playback rate; runtime concatenates the frozen sequence once and derives one overall rate after actual TTS duration is known.
- Prefer coherent retention-first progressions across the live high-retention background categories.
- Never repeat a clip to fill time and never plan intentional loops.
- Runtime may fail over only from the entire frozen primary sequence to the entire frozen backup sequence; it may not mix sequences or creatively substitute footage.
- Old pre-reset backgrounds were deleted; do not reference, recreate or assume hidden legacy IDs.
- Avoid repeated assets, exact sequences, categories and substantially overlapping temporal ranges using verified private receipt history.

After authoring/final-ranking the complete Daily pool, run the canonical ChatGPT/Work connector-mode precommit exactly as inherited from the shared contract:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_precommit \
  --profile daily \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha <rules_source_sha>
```

The command above is the canonical ChatGPT/Work precommit. Its source-integrity proof is the shared connector materialization evidence plus `planning.materialization_verify PASS`; any separate real-Git checkout verification mode is documented only in the shared contract. The gate requires **all 36 candidates PASS** before immutable commit. The compatibility wrapper `planning.daily_precommit` remains available for existing callers but contains no independent validation logic.

The final immutable pool bytes must exactly match the successful `draft_sha256`. Manual checks, downstream admission/promotion or GitHub Actions are not substitutes for planner-time pre-commit.

ChatGPT/Work remains creative/editorial owner. Private workflows validate/promote mechanically; public runtime executes statelessly.
