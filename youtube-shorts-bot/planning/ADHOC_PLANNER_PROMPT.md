# Wacky Dramas — Ad-hoc Planner

This is the canonical **Ad-hoc profile** entry point for the shared Wacky Dramas planner.

Read and follow, in order:

1. `docs/private/PLANNER_PROMPT.md` — shared connector-native execution/replenishment/drift contract.
2. `planning/PLANNER_MATERIALIZATION.json` — machine-readable ChatGPT/Work checkpoint contract.
3. `planning/ADHOC_PLANNER_RULES.md` — Ad-hoc creative/identity/promotion rules.
4. `planning/STORY_RULES.md`.
5. `docs/background-media-strategy.md` — canonical shared background policy.

Repository code/configuration at exact current `main` is authoritative. Resolve current `main` through the authorized GitHub connector/API and freeze `rules_source_sha`. **Do not shell-Git the repository and do not reconstruct the planner module tree locally.** Fetch the exact-SHA self-contained `planning/connector_checkpoint.py`; only that checkpoint file plus the authored pool/evidence JSON need local staging.

For execution/bootstrap conflicts with older wording, the current `planning/PLANNER_MATERIALIZATION.json` and `docs/private/PLANNER_PROMPT.md` win. GitHub Actions must not perform Ad-hoc creative planning.

## Ad-hoc contract

Use `profile=adhoc` from the standalone checkpoint contract. The ranked pool contains exactly **5** candidates in frozen rank order. `target_count=1`.

For `manual_on_demand`, allocate a distinct stable immutable invocation namespace after current state inspection; multiple manual invocations may coexist on the same Singapore date. An existing same-date `scheduled_daily` request is not a manual collision. For `scheduled_daily`, preserve the canonical once-per-date 01:00 SGT namespace and recover existing canonical state rather than replanning it.

Every candidate uses the canonical immediate publication object:

```json
{"mode":"immediate","timezone":"Asia/Singapore","publish_at":null}
```

## Background readiness and sequence contract

An empty/insufficient registry is `REPLENISH`, not a terminal planner failure. Run the shared bounded automatic procedure; this profile does not implement a separate retry engine. Resume a compatible unfinished session, persist every exact-source visual decision, and continue attempts automatically through `PASS`, a genuine infrastructure blocker, or `E_MEDIA_REPLENISH_EXHAUSTED`. Candidate rejection is not planner failure. On `PASS`, immediately resume this same Ad-hoc invocation and create its five-candidate ranked pool.

New requests use schema v7 `concatenated_fit_to_short`:

- one primary ordered sequence and one backup ordered sequence;
- each sequence has 2-3 distinct atomic clips; 3 preferred;
- every chosen range is at least 60 seconds;
- each sequence totals 210-300 seconds; 240 seconds preferred;
- primary and backup are disjoint;
- freeze exact logical IDs, order, segment start and duration;
- do not freeze playback rate; runtime derives one overall rate after actual TTS duration;
- never repeat a clip to fill time and never intentionally loop;
- avoid recent/repeated assets, exact sequences, categories and substantially overlapping ranges using private receipt history.

The connector-evidence JSON must include only the selected IDs and current exact-SHA evidence showing each is eligible with trusted duration. Do not copy the full registry locally merely to validate the pool.

## Mandatory checkpoint

After creative/adversarial review and complete five-candidate authorship, stage the exact-SHA standalone checkpoint and run:

```bash
python connector_checkpoint.py validate \
  --profile adhoc \
  --pool /tmp/wacky-adhoc-pool.json \
  --rules-source-sha <rules_source_sha> \
  --evidence /tmp/wacky-adhoc-connector-evidence.json
```

All 5 candidates must `PASS` and `commit_allowed` must be true. Re-query current `main` immediately before the final run; evidence `drift.status=PASS` is valid only when `current_main_sha == rules_source_sha` after any required refresh. Final pool bytes must exactly match `draft_sha256`.

Commit only the allowed immutable pool artifact through the authorized GitHub connector/API. Then the existing private Ad-hoc Production workflow mechanically preserves rank order, promotes the first valid candidate, creates the canonical immutable request, validates it and dispatches the public single-item runtime. ChatGPT/Work does not directly render/TTS/upload.
