# Wacky Dramas — Daily Planner Rules

These rules apply to **new** Daily planning. Historical immutable 36-candidate pools retain their historical recovery semantics.

The business objective remains strong subscriber and qualified-view growth without weakening safety, originality, copyright, immutable-state, recovery, selected-media, or publication guarantees.

## Profile and publication timing

### Normal next day

For the normal scheduled planner invocation at/after **20:00 Asia/Singapore**, plan the **next Singapore calendar day**.

- `planning_mode = normal_next_day`.
- `target_count` is exactly **24**.
- `candidate_count = 24`.
- `reserve_candidate_count = 0`.
- Use the canonical hourly publication slots from `00:00` through `23:00` Asia/Singapore for that plan date.

### Same-day catch-up

For a manual run before 20:00 Asia/Singapore, use `same_day_catch_up` for the **current Singapore calendar day** when the canonical timing rules require catch-up.

- Keep only exact top-of-hour slots at least **30 minutes in the future**.
- `publication_slots` contains exactly those eligible slots in chronological order.
- `target_count` equals the number of eligible remaining slots.
- `candidate_count = target_count`.
- There are no reserves.
- If no eligible catch-up slot remains, fail closed rather than inventing a non-canonical slot.
- Downstream promotion independently rechecks the 30-minute lead at promotion time.

### Existing canonical Daily plan

If canonical `content/planning/YYYY-MM-DD.json` already exists, do **not** create another pool for that date. Use deterministic production recovery through `.github/workflows/daily-production.yml` / its manual recovery path for the already-immutable requests.

### Immutable pool attempts

Daily pool IDs remain immutable attempts such as `dp-YYYYMMDD-a01`, `dp-YYYYMMDD-a02`, and so on. Before a pool is committed, a checkpoint failure is repaired in the current draft and the same checkpoint is rerun. Once an immutable pool has been successfully committed, downstream automation must not creatively repair or rerank it; production recovery uses the frozen request/content identities.

There is no new-planning 36-candidate pool and no first-24-valid rank walk. If candidate N is weak or invalid before pool commit, repair/regenerate candidate N while preserving unaffected candidates.

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
