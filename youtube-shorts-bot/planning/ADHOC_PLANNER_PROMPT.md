# Wacky Dramas — Ad-hoc Planner (canonical entry point)

This is the canonical Ad-hoc planner entry point. Read and follow `planning/ADHOC_PLANNER_RULES.md` in full, together with every shared Daily/story/background/schema file it references.

`ADHOC_PLANNER_RULES.md` preserves the complete planning, creative, analytics, safety, media-readiness, ranked-pool, publication, promotion and recovery rules. The execution-environment rules below supersede only any older wording in that file that requires `git rev-parse HEAD`, a local `.git` directory, an authenticated checkout, snapshot bootstrap, a snapshot manifest, synthetic Git metadata, or an exact local checkout HEAD.

## Canonical Python execution rule

Daily and Ad-hoc planner Python must run the same way as the repository's other ordinary Python utilities.

1. Inspect current `main` through GitHub and retain its exact immutable 40-character commit SHA as `rules_source_sha`.
2. Read/materialize the Python/config/data inputs required by the current planner using the normal available execution mechanism. A Git checkout is **not** required.
3. Execute the live contract normally:

```bash
python -m planning.planner_contract
```

4. Execute shared media readiness normally:

```bash
python -m media.media_readiness audit --allow-not-ready
```

5. After authoring the complete temporary five-candidate pool, execute:

```bash
python -m planning.adhoc_precommit \
  --pool /tmp/wacky-adhoc-pool.json \
  --rules-source-sha <rules_source_sha>
```

6. `planning_execution.rules_source_sha` in the draft must exactly equal the explicit `rules_source_sha` supplied to the validator.
7. The normal validator must not require `.git`, `git rev-parse`, snapshot bootstrap, or synthetic HEAD metadata.
8. `--verify-git-head` is optional developer/CI hardening for execution inside a real checkout only. ChatGPT/Work must not use it as a prerequisite.
9. All five candidates must still PASS. Schema, media, uniqueness, immediate-public, identity, duplicate and immutable-state rules are unchanged.
10. Before the immutable pool commit, re-read current GitHub `main`. If its SHA differs from `rules_source_sha`, do not commit the stale draft: refresh the rules source SHA, rerun live contract discovery, media readiness and complete pre-commit validation.
11. The final immutable pool bytes must still exactly match the successful validator `draft_sha256`.

For `manual_on_demand`, multiple same-date manual runs remain allowed under distinct stable immutable invocation identities. Existing `scheduled_daily` state is not a reuse/stop condition for a distinct manual invocation.

Everything else in `ADHOC_PLANNER_RULES.md` remains mandatory unless current executable repository code/configuration has superseded it.
