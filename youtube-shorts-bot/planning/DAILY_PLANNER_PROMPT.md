# Wacky Dramas — Daily Planner (canonical entry point)

This is the canonical Daily planner entry point. Read and follow `planning/DAILY_PLANNER_RULES.md` in full, together with `planning/STORY_RULES.md` and every analytics/background/schema/configuration file it references.

`DAILY_PLANNER_RULES.md` preserves the complete creative funnel, analytics, schedule, media-readiness, ranked-pool, publication, promotion and recovery rules. The execution-environment rules below supersede only any older wording in that file that requires `git rev-parse HEAD`, a local `.git` directory, an authenticated checkout, snapshot bootstrap, a snapshot manifest, synthetic Git metadata, an exact local checkout HEAD, a repository archive, whole-repository download, whole-directory source materialization, an automatic connector filesystem mount, a special connector-to-filesystem bridge, or GitHub Actions as the planner execution engine.

## Canonical Python execution rule

Daily and Ad-hoc planner Python must run from ordinary explicitly materialized source/config/data files. A Git checkout, Git executable, `.git` directory, authenticated clone, branch state, synthetic HEAD, repository archive, whole-repository download, automatic connector filesystem mount, special connector materialization bridge, or GitHub Actions planner job is **not** a planner prerequisite.

1. Inspect current `main` through the GitHub API/connector and retain its exact immutable 40-character commit SHA as `rules_source_sha`. Treat that SHA only as explicit immutable repository identity; do not derive it with local Git.
2. Read `planning/PLANNER_MATERIALIZATION.json` from that same immutable source SHA. It is the authoritative bootstrap contract.
3. Fetch each path declared in `required_python_files` and `required_data_files` **directly from the exact `rules_source_sha`** through the GitHub API/connector.
4. For every fetched path, treat the decoded UTF-8 `content` returned by the connector/API response as the exact source bytes. ChatGPT/Work itself must create the parent directories in a plain temporary working directory and write that returned content to the same repository-relative path. The connector does **not** need to mount files into the Python/container filesystem and no separate Files/materialize API, repository archive, authenticated checkout, or special bridge is required.
5. If the GitHub response returns the exact file content successfully, the file is considered available for materialization. Do **not** fail merely because the connector response is represented as a tool/content resource rather than a mounted filesystem object. Fail closed only if the exact required source content cannot be fetched, cannot be written as a local UTF-8 file, or a required canonical Python entrypoint fails after materialization.
6. Materialize only the applicable existence/uniqueness state placeholders declared by the manifest. Do not enumerate or download whole source directories.
7. The materialized directory is deliberately not a repository. Failure to obtain a repository archive, checkout or `.git` metadata is therefore **not a blocker**.
8. Set `PYTHONPATH` to the materialized `youtube-shorts-bot` directory as needed and execute the live contract normally:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.planner_contract
```

9. Execute shared media readiness normally:

```bash
PYTHONPATH=youtube-shorts-bot python -m media.media_readiness audit --allow-not-ready
```

10. If readiness reports `REPLENISH`, source reviewed Pexels candidates with reserve capacity rather than only the exact deficit. Stay within the current manifest maximum (currently 48), preserve the required category coverage, and prefer enough reserves that one or more rendition-policy rejects do not require a new attempt. Background Management will try candidates in manifest order, report every rejected source/rendition candidate it encounters, skip those recoverable candidate failures, and then enforce the normal shared readiness threshold. Identity collisions remain hard failures.
11. Do not freeze final background IDs until replenishment has completed successfully and current `main` contains the accepted registry update. Re-read the accepted registry and choose exact primary/backup backgrounds from that canonical state.
12. After authoring and freezing the complete temporary Daily ranked pool, execute the exact canonical pre-commit validator:

```bash
PYTHONPATH=youtube-shorts-bot python -m planning.daily_precommit \
  --pool /tmp/wacky-daily-pool.json \
  --rules-source-sha <rules_source_sha>
```

13. `planning_execution.rules_source_sha` in the draft must exactly equal the explicit `rules_source_sha` supplied to the validator.
14. The normal validator must not require or infer any Git state. Do not use `--verify-git-head`, create synthetic Git metadata, clone the repository, require a repository archive, require an automatic connector filesystem mount, or substitute Git commands/GitHub Actions for the explicit SHA contract.
15. **FAIL CLOSED if the exact pre-commit module cannot be executed after the connector-returned source has been written locally.** Manual schema checks, hand-written arithmetic, partial reimplementation, downstream promotion, or later GitHub Actions validation are not substitutes for planner-time pre-commit. Do not commit a pool unless all 36 candidates PASS the actual validator.
16. Private Daily Production independently reruns the same pre-commit validation as a committed-pool admission gate before ranked promotion. This is defense in depth only; it does not waive step 15 and it is not the planner execution engine.
17. Before the immutable pool commit, re-read current GitHub `main`. If its SHA differs from `rules_source_sha`—including because background replenishment committed a registry update—do not commit the stale draft. Refresh `rules_source_sha`, re-read the manifest from that SHA, refetch its explicit required files, rewrite the temporary materialization from those returned source contents, rerun live contract discovery, media readiness and complete pre-commit validation against the new canonical state.
18. The final immutable pool bytes must exactly match the successful validator `draft_sha256`.

Everything else in `DAILY_PLANNER_RULES.md` remains mandatory unless current executable repository code/configuration has superseded it.
