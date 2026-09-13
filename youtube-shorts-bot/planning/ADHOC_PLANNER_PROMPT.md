# Wacky Dramas — Ad-hoc Planner (canonical entry point)

This is the canonical Ad-hoc planner entry point. Read and follow `planning/ADHOC_PLANNER_RULES.md` in full, together with every shared Daily/story/background/schema file it references.

`ADHOC_PLANNER_RULES.md` preserves the complete planning, creative, analytics, safety, media-readiness, ranked-pool, publication, promotion and recovery rules. The execution-environment rules below supersede only any older wording in that file that requires `git rev-parse HEAD`, a local `.git` directory, an authenticated checkout, snapshot bootstrap, a snapshot manifest, synthetic Git metadata, or an exact local checkout HEAD.

## Canonical Python execution rule

Daily and Ad-hoc planner Python must run from ordinary materialized source/config/data files. A Git checkout, Git executable, `.git` directory, authenticated clone, branch state or synthetic HEAD is **not** a planner prerequisite.

1. Inspect current `main` through the GitHub API/connector and retain its exact immutable 40-character commit SHA as `rules_source_sha`. Treat that SHA only as explicit immutable repository identity; do not derive it with local Git.
2. Read/materialize the Python/config/data inputs required by the current planner into any plain temporary directory using the normal available file/connector mechanism. The directory does not need to be a repository.
3. Set `PYTHONPATH` to the materialized `youtube-shorts-bot` directory as needed and execute the live contract normally:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
```

4. Execute shared media readiness normally:

```bash
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

5. If readiness reports `REPLENISH`, source reviewed Pexels candidates with reserve capacity rather than only the exact deficit. Stay within the current manifest maximum (currently 48), preserve the required category coverage, and prefer enough reserves that one or more rendition-policy rejects do not require a new attempt. Background Management will try candidates in manifest order, report every rejected source/rendition candidate it encounters, skip those recoverable candidate failures, and then enforce the normal shared readiness threshold. Identity collisions remain hard failures.
6. Do not freeze final background IDs until replenishment has completed successfully and current `main` contains the accepted registry update. Re-read the accepted registry and choose exact primary/backup backgrounds from that canonical state.
7. After authoring the complete temporary five-candidate pool, execute the exact canonical pre-commit validator:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.adhoc_precommit \
  --pool /tmp/wacky-adhoc-pool.json \
  --rules-source-sha <rules_source_sha>
```

8. `planning_execution.rules_source_sha` in the draft must exactly equal the explicit `rules_source_sha` supplied to the validator.
9. The normal validator must not require or infer any Git state. Do not use `--verify-git-head`, create synthetic Git metadata, clone the repository, or substitute Git commands for the explicit SHA contract.
10. **FAIL CLOSED if the exact pre-commit module cannot be executed.** Manual schema checks, hand-written arithmetic, partial reimplementation, downstream promotion, or later GitHub Actions validation are not substitutes for planner-time pre-commit. Do not commit a pool unless all five candidates PASS the actual validator.
11. Private Ad-hoc Production independently reruns the same pre-commit validation as a committed-pool admission gate before ranked promotion. This is defense in depth only; it does not waive step 10.
12. Before the immutable pool commit, re-read current GitHub `main`. If its SHA differs from `rules_source_sha`—including because background replenishment committed a registry update—do not commit the stale draft. Refresh `rules_source_sha`, rerun live contract discovery, media readiness and complete pre-commit validation against the new canonical state.
13. The final immutable pool bytes must exactly match the successful validator `draft_sha256`.

For `manual_on_demand`, multiple same-date manual runs remain allowed under distinct stable immutable invocation identities. Existing `scheduled_daily` state is not a reuse/stop condition for a distinct manual invocation.

Everything else in `ADHOC_PLANNER_RULES.md` remains mandatory unless current executable repository code/configuration has superseded it.
