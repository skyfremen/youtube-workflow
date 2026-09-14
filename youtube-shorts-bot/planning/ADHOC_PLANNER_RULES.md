# Wacky Dramas — Ad-hoc Planner Rules

These rules apply to **new** Ad-hoc planning. Historical immutable pools/requests retain their historical recovery semantics.

## Profile

- Planning mode: `manual_on_demand` only.
- Target count: 1.
- Candidate count: 1.
- Reserve count: 0.
- Publication: immediate/public.
- The single candidate may keep `rank=1` for pool-shape compatibility.
- Multiple manual invocations may coexist on the same Singapore date when their immutable identities differ.
- `scheduled_daily` is not a valid new-planning mode.

## Creative ownership

ChatGPT/Work owns the final production candidate and all semantic/editorial choices: premise originality, duplicate reasoning, hook, story flow, conflict/stakes, escalation, payoff, ending, truthful title, narration suitability, lead gender/tone, narrator voice meaning, punchline semantics, and background suitability/readability.

Follow `planning/STORY_RULES.md` and current analytics/history evidence. Internally discard a weak premise and generate another if needed, but do not author five complete alternatives merely to create reserves.

## Background selection

New schema-v7 candidates contain one pool-level `background_category` and frozen primary/backup `concatenated_fit_to_short` sequences.

- Both sequences must use that same category.
- Each sequence uses 2–3 distinct clips; 3 is preferred.
- Primary and backup are disjoint.
- Freeze logical clip IDs, sequence order, segment starts, and segment durations.
- Do not author/freeze playback rate; runtime owns playback-rate derivation after actual narration/timeline duration.
- Selected assets must satisfy all hard registration, activity, visual-review, commercial-use, watermark/text, duration, rendition, quality, range, and schema requirements.
- Global inventory minimums/category minimums are not a planner gate.
- Do not start or resume replenishment during normal planning.

Selection recovery is:

```text
preferred suitable category
→ alternate suitable eligible category
→ checkpoint-contract canonical fallback category
```

If one clip fails, replace it with a hard-valid clip from the same chosen category. If the chosen category cannot form both sequences, change the candidate category and rebuild both sequences. Never relax hard validity.

## Validation and recovery

The exact-SHA `planning/connector_checkpoint.py` is the single mechanical authority for new ChatGPT/Work planning. Mechanical failures are repair instructions, not creative rejection signals.

Use:

```text
repair affected field/candidate
→ rerun same checkpoint
→ repeat until 1/1 PASS
```

Do not add a second manual validator, duplicate checkpoint arithmetic, or a reserve rank walk.

Repository drift and safe commit conflicts are recoverable: refresh current `main`, refresh only affected rules/evidence, revalidate, and retry without force-push.

## Termination

Successful immutable pool commit is the end of ChatGPT/Work planning. Do not wait for or monitor downstream private/public production in the same planner invocation.
