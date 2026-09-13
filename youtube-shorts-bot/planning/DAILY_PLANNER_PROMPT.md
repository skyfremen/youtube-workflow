# Wacky Dramas — Daily Planner

This is the canonical **Daily profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — shared connector-native execution/replenishment/drift contract.
2. `planning/PLANNER_MATERIALIZATION.json` — machine-readable ChatGPT/Work checkpoint contract.
3. `planning/DAILY_PLANNER_RULES.md` — Daily creative/schedule/diversity/promotion rules.
4. `planning/STORY_RULES.md`.
5. `docs/background-media-strategy.md` — canonical shared background policy.

Repository code/configuration at exact current `main` is authoritative. Resolve current `main` through the authorized GitHub connector/API and freeze `rules_source_sha`. **Do not shell-Git the repository and do not reconstruct the planner module tree locally.** Fetch the exact-SHA self-contained `planning/connector_checkpoint.py`; only that checkpoint file plus the authored pool/evidence JSON need local staging.

For execution/bootstrap conflicts with older wording, the current `planning/PLANNER_MATERIALIZATION.json` and `docs/private/PLANNER_PROMPT.md` win. GitHub Actions must not perform Daily creative planning.

## Daily contract

Use `profile=daily` from the standalone checkpoint contract. The ranked pool contains exactly **36** candidates in frozen rank order. `normal_next_day` target is 24 canonical hourly slots; `same_day_catch_up` follows the current Daily rules and minimum lead-time contract.

## Background readiness and sequence contract

An empty/insufficient registry is `REPLENISH`, not a terminal planner failure. Run the shared bounded automatic procedure; this profile does not implement a separate retry engine. Resume a compatible unfinished session, persist every exact-source visual decision, and continue attempts automatically through `PASS`, a genuine infrastructure blocker, or `E_MEDIA_REPLENISH_EXHAUSTED`. Candidate rejection is not planner failure. On `PASS`, immediately resume this same Daily invocation and its canonical candidate/ranking pipeline.

New requests use schema v7 `concatenated_fit_to_short`:

- one primary ordered sequence and one backup ordered sequence;
- each sequence has 2-3 distinct atomic clips; 3 preferred;
- every chosen range is at least 60 seconds;
- each sequence totals 210-300 seconds; 240 seconds preferred;
- primary and backup are disjoint;
- freeze exact logical IDs, order, segment start and duration;
- do not freeze playback rate; runtime derives one overall rate after actual TTS duration;
- never repeat a clip to fill time and never intentionally loop;
- preserve Daily diversity and anti-repetition requirements across the batch.

The connector-evidence JSON includes only selected IDs with current exact-SHA eligibility/duration evidence; the full registry is not a required local checkpoint input.

## Mandatory checkpoint

After complete Daily authorship/ranking, run:

```bash
python connector_checkpoint.py validate \
  --profile daily \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha <rules_source_sha> \
  --evidence /tmp/wacky-daily-connector-evidence.json
```

All 36 candidates must `PASS` and `commit_allowed` must be true. Re-query current `main` immediately before the final run; evidence `drift.status=PASS` is valid only when `current_main_sha == rules_source_sha` after any required refresh. Final pool bytes must exactly match `draft_sha256`.

Commit only the allowed immutable Daily pool artifact through the authorized GitHub connector/API. Existing private workflows then validate/promote mechanically and dispatch the public stateless runtime. ChatGPT/Work does not directly render/TTS/upload.
