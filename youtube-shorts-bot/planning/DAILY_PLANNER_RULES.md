# Wacky Dramas — Daily Planner Rules

These rules apply to **new** Daily planning. Historical immutable 36-candidate pools retain their historical recovery semantics.

The business objective remains strong subscriber and qualified-view growth without weakening safety, originality, copyright, immutable-state, recovery, selected-media, or publication guarantees.

## Profile

### Normal next day

- `planning_mode = normal_next_day`.
- `target_count = 24`.
- `candidate_count = 24`.
- `reserve_candidate_count = 0`.
- Use the canonical 24 hourly publication slots for the plan date.

### Same-day catch-up

If current `main` still supports catch-up:

- resolve eligible remaining slots using the current lead-time contract;
- `target_count = eligible_slot_count`;
- `candidate_count = target_count`;
- there are no reserves.

There is no new-planning 36-candidate pool and no first-24-valid rank walk. If candidate N is weak or invalid, repair/regenerate candidate N while preserving unaffected candidates.

## Creative ownership and batch diversity

ChatGPT/Work owns all semantic/editorial decisions. Follow `planning/STORY_RULES.md`, current analytics learning, recent history, and the configured Daily diversity limits.

The final required set should be strong as individual Shorts and as a batch. Review for premise/semantic duplication, conflict/category concentration, title-pattern repetition, ending/payoff repetition, weak hooks, exposition, unclear stakes, weak escalation, weak payoff, narration awkwardness, voice mismatch, background mismatch/readability, and undesirable recent media reuse.

Cheap internal premise exploration/rejection is allowed. Do not fully author extra production candidates merely as reserves.

## Background selection

Each new schema-v7 pool candidate includes one `background_category` plus frozen primary/backup `concatenated_fit_to_short` sequences.

- Every clip in both sequences must match the candidate's chosen category.
- Each sequence uses 2–3 distinct clips; 3 is preferred.
- Primary and backup are disjoint.
- Freeze logical IDs, order, segment starts, and segment durations.
- Do not author/freeze playback rate; runtime derives it after actual narration/timeline duration.
- Selected assets must satisfy current hard registration, activity, visual-review, commercial-use, watermark/text, duration, rendition, quality, range, and schema rules.
- Different Daily candidates may use different categories; retain useful batch variety.
- Global media inventory/category minimums are not a planner gate.
- Do not create/resume replenishment during normal planning.

Selection recovery is:

```text
preferred suitable category
→ alternate suitable eligible category
→ checkpoint-contract canonical fallback category
```

If a clip fails, replace it with another hard-valid clip from the same category. If the category cannot produce both required sequences, choose an alternate/fallback category and rebuild both sequences. Never relax hard validity.

## Validation and repair

The exact-SHA `planning/connector_checkpoint.py` is the single mechanical authority for new ChatGPT/Work planning.

For a normal day require 24/24 PASS. For catch-up require `target_count/target_count` PASS. A failure is an actionable repair instruction:

```text
read exact diagnostic
→ repair only affected authored input
→ preserve unaffected candidates
→ rerun same checkpoint
```

Do not manually reproduce checkpoint arithmetic or add a second validator. Do not weaken checkpoint rules.

Repository drift and safe commit conflicts are recoverable: refresh current `main`, refresh affected rules/evidence, repair only if required, revalidate, and retry without force-push.

## Termination

Successful immutable Daily planning-pool commit is the end of ChatGPT/Work planning. Do not wait for private promotion, rendering, upload, YouTube verification, or public runtime completion in the same invocation.
