# Wacky Dramas — Daily Planner (schema v5 + ChatGPT editorial selection overlay)

This is the canonical Daily planner entry point. Read `docs/DAILY_PLANNER_V4_BASE.md` in full first. Preserve its business objective, story rules, analytics rules, metadata, scheduling, safety, recovery, immutable-request architecture and background policy except where this overlay explicitly supersedes winner-selection and schema-v4/background-treatment behavior.

Repository code remains the source of truth for deterministic calculations and validation. Before planning, inspect the current `planning/planning_engine.py`, `planning/planning_runner.py`, `analytics/analytics_learning.py`, `validation/validate_content.py`, `common/runtime_contract.py`, `media/background_selector.py`, `media/background_treatment.py`, `media/background_policy.py`, registry and current production/dry-run workflows.

## Editorial ownership — authoritative override

**ChatGPT / Work owns the final editorial choice of the Daily winners.**

`planning_engine.py` and `planning_runner.py` are deterministic support systems. They may hard-reject invalid candidates, calculate editorial/title/hook/analytics scores, normalize analytics, rank candidates, enforce configured limits, detect duplicates/near-duplicates, validate diversity, assign publication slots and validate the final ChatGPT-selected set. They must **not replace ChatGPT's editorial judgment by choosing the authoritative winner set for new planning runs**.

The legacy `final-select` runner stage exists only for compatibility/recovery of historical planning artifacts that were created under the old deterministic-winner contract. Do not use it to choose winners for a new Daily plan.

The canonical new-planning flow is:

```text
ChatGPT generates raw candidates
  -> planning.raw-filter
  -> ChatGPT develops qualified semifinalists
  -> planning.candidate-evaluation
  -> deterministic scores/checks/ranking evidence returned
  -> ChatGPT reviews that evidence plus semantic/editorial quality
  -> ChatGPT chooses up to 24 winners
  -> planning.validate-selection
  -> deterministic diversity/duplicate/count/scheduling validation
  -> ChatGPT writes full stories for the validated chosen IDs
  -> background allocation/treatment
  -> schema/request validation
  -> immutable requests
```

ChatGPT may not choose a candidate that failed hard filtering or candidate evaluation. ChatGPT may choose a lower-ranked eligible candidate over a higher-ranked eligible candidate when its editorial/semantic judgment supports that choice, provided the final chosen set passes deterministic selection validation. Ranking is evidence, not authority.

If `planning.validate-selection` rejects the chosen set, ChatGPT must revise its editorial selection and validate again. The deterministic validator may reject an invalid set; it may not silently substitute different winners.

## Mandatory deterministic checkpoints

### Checkpoint 1 — raw filter

Actually execute `planning/planning_runner.py --stage raw-filter` (or the repository-side `planning.raw-filter` bridge operation when local execution is unavailable). Consume the actual `result.qualified_candidates`. Do not develop hard-rejected candidates.

### Checkpoint 2 — candidate evaluation

After ChatGPT develops the semifinalists, actually execute `planning/planning_runner.py --stage candidate-evaluation` (or `planning.candidate-evaluation`). This stage owns deterministic score arithmetic, analytics blending/normalization, title/hook thresholds and eligibility. Consume the actual `result.evaluated_candidates` and rejection evidence.

This stage does **not** choose the final Daily winners.

### Checkpoint 3 — ChatGPT editorial selection

ChatGPT / Work compares the evaluated candidates using both the deterministic evidence and its own semantic/editorial judgment, including hook strength, curiosity gap, emotional stakes, escalation, payoff, title potential, broad relatability, originality, narration suitability, daily variety and likely viewer response.

ChatGPT then chooses the final candidate IDs, up to the current Daily publication limit. Do not mechanically take the top N scores unless ChatGPT independently judges that those are the strongest final set.

### Checkpoint 4 — deterministic selection validation

Actually execute `planning/planning_runner.py --stage validate-selection` (or `planning.validate-selection`) with:

- the exact evaluated candidate objects returned by candidate evaluation;
- `selected_candidate_ids` in ChatGPT's chosen order;
- the target `plan_date`;
- the applicable selection limit.

Consume the actual validated result. This stage checks membership/eligibility, duplicate IDs, diversity limits, near-duplicates, configured selection bounds, exploration requirements for a full Daily set, and deterministic publication scheduling. It must fail closed instead of substituting winners.

Only the candidate IDs explicitly selected by ChatGPT and successfully validated may proceed to full story/request creation.

## Planning provenance

For a new Daily planning audit, record execution provenance for:

- `raw_filter`;
- `candidate_evaluation`;
- `selection_validation`.

Also record `editorial_selection_owner: "chatgpt"` and the exact `selected_candidate_ids` chosen by ChatGPT before validation. The validated set must contain the same IDs; deterministic validation may reorder them for publication scheduling but must not replace them.

Historical audits using `final_selection` remain valid for recovery and must not be rewritten.

## Preserved Daily scheduling rules

The normal Daily planner runs at 20:00 Asia/Singapore and plans the next Singapore calendar day. Before 20:00, manual runs use the existing same-day catch-up rules. Keep only top-of-hour slots at least 30 minutes in the future. Never recreate elapsed/too-close slots. Existing plan/recovery idempotency remains unchanged.

## Schema-v5 override

New immutable production requests use schema v5. Schema v4 remains readable only for existing recovery/migration.

The v5 `visual` object contains exactly:

- `background_primary_id`
- `background_backup_id`
- `background_primary_treatment`
- `background_backup_treatment`

Each treatment contains:

- `segment_start_seconds`
- `segment_duration_seconds`
- `playback_rate`

Use the canonical private background selector and treatment allocator. Do not hand-author deterministic treatment values after running the allocator. Carry same-run planned asset/category/treatment scratch state across Daily winners. Persistent history remains private immutable successful receipts only.

## Analytics

Analytics remains evidence-gated through `analytics_evidence_count`. `analytics_learning.py` owns normalized historical-fit arithmetic. Deterministic analytics scores support ChatGPT's judgment; they do not make the editorial winner decision. When evidence is zero/disabled, ChatGPT still chooses using editorial evidence and deterministic hard constraints.

## Public runtime boundary

Do not move media downloading, probing, physical rendition selection, normalization, cropping, FFmpeg treatment, rendering, TTS, alignment or upload into the private planner. The private planner freezes logical IDs and treatments; `production-runtime` executes heavy generation/upload work.

## Final request checks

Before committing each winner, confirm:

- the candidate ID was explicitly chosen by ChatGPT;
- it appears in successful `planning.validate-selection` output;
- schema version is 5;
- planning scores/title fields remain consistent with canonical candidate-evaluation evidence;
- primary/backup logical IDs are distinct and valid;
- treatment objects came from the canonical allocator;
- exact upload-payload validation succeeds;
- no immutable existing production JSON is modified.

Fail closed on any deterministic validation failure. **Failing closed means ChatGPT must revise or stop; deterministic code must never silently pick replacement winners.**
