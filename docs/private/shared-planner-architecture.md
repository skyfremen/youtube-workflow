# Shared Planner Architecture

Daily and Ad-hoc are two profiles of one Wacky Dramas planner. This architecture describes **new planning**; historical immutable artifacts retain versioned compatibility.

## Ownership

Shared behavior belongs in shared code/configuration. Classify a new planner feature as:

- `SHARED` — default when both profiles should behave the same;
- `DAILY_ONLY` — only for genuine Daily semantics such as publication slots/batch diversity;
- `ADHOC_ONLY` — only for genuine Ad-hoc semantics such as immediate publication/manual identity.

Schema validation, story/title/punchline contracts, narration/voice rules, selected-background hard validation, sequence validation, publication validation and candidate validation are shared.

Profile-specific differences are current candidate/target cardinality, identity/uniqueness, publication scheduling and batch diversity.

Global media-library readiness and replenishment are **not part of normal planner admission**. Separate background-library maintenance tooling may continue independently.

## Current architecture

```text
current private main
        |
authorized GitHub connector/API
        |
resolve exact current-main SHA
        |
freeze rules_source_sha
        |
read exact-SHA profile/contract + targeted evidence
        |
creative authorship of exactly required candidates
        |
standalone connector_checkpoint.py
        |
repair affected authored input and rerun if needed
        |
connector/API current-main drift check
        |
immutable planning pool commit
        |
CHATGPT / WORK PLANNER ENDS
        |
private deterministic production workflow
        |
immutable request(s)
        |
public stateless production-runtime
```

For ChatGPT/Work, the authorized GitHub connector/API is the repository source-acquisition mechanism. Shell Git access to `github.com` is neither attempted nor required. GitHub Actions is downstream deterministic CI/production/control-plane infrastructure only and never owns creative planning.

## Current profile contracts

### Ad-hoc

- `manual_on_demand` only for new planning;
- target 1, candidate count 1, reserve count 0;
- immediate/public publication;
- no global readiness gate;
- no planner-bound automatic replenishment;
- selected-background hard validation and same-category primary/backup required.

### Daily

- normal full day target/candidate count 24;
- catch-up target is eligible remaining slot count and candidate count equals target;
- reserve count 0;
- no first-24-of-36 promotion for new pools;
- no global readiness gate;
- no planner-bound automatic replenishment;
- selected-background hard validation and same-category primary/backup required.

## Shared implementation

- `planning/planner_profiles.py` — declarative current profile differences.
- `planning/planner_core.py` — shared pool/candidate/date/publication validation helpers and schema-v1 compatibility primitives.
- `planning/planner_precommit.py` — repository-native developer/CI validator for current pools.
- `planning/connector_checkpoint.py` — self-contained, exact-SHA ChatGPT/Work mechanical planning authority.
- `planning/planner_contract.py` / `planner_contract_base.py` — machine-readable current contract.
- `planning/planner_drift.py` — deterministic path classification for drift.
- `validation/validate_content.py` — shared request/schema and selected-background validation. Schema-v7 validates referenced assets without requiring global inventory readiness.
- `validation/publication.py` — shared publication and YouTube metadata constraints.
- `planning/daily_precommit.py` / `planning/adhoc_precommit.py` — compatibility wrappers around shared precommit.
- `planning/ranked_promotion.py` — downstream deterministic promotion. Current schema-v2 pools have no reserve walk; historical schema-v1 pools retain their versioned compatibility path.

## Canonical ChatGPT/Work connector bootstrap

1. Query the authorized connector/API for exact current `main` and freeze it as `rules_source_sha`.
2. Fetch `planning/PLANNER_MATERIALIZATION.json` and the profile/rule files required by that invocation at the same SHA.
3. Fetch only the exact-SHA standalone `planning/connector_checkpoint.py` for local checkpoint execution.
4. Load targeted recent/history/analytics/identity/background evidence through connector reads.
5. Author the required pool.
6. Assemble a small connector-evidence JSON containing current drift/uniqueness and hard-valid facts only for selected backgrounds.
7. Run the standalone checkpoint.

Do not first try Git fetch/clone/pull/ls-remote, worktree creation, Git authentication repair, DNS/proxy repair, `.git` health checks, a full repository materialization, or a local full background-registry copy.

## Selected-background architecture

Every current schema-v2 pool candidate carries one `background_category`. Its schema-v7 request freezes primary and backup ordered sequences, but the category remains planning metadata and is not added to the public request schema.

The checkpoint/repository validator enforces:

- selected asset hard eligibility;
- exact category equality for every primary and backup clip;
- valid clip/sequence counts and duration ranges;
- no duplicate asset within a sequence;
- primary/backup disjointness;
- exact segment range validity.

ChatGPT chooses the preferred semantically suitable category. If it cannot form valid sequences, ChatGPT tries another suitable eligible category and finally the single canonical fallback category exposed by the checkpoint contract. The fallback never weakens validation.

Schema-v7 playback rate remains runtime-owned: ChatGPT freezes IDs/order/start/duration, while runtime derives the overall rate from actual final narration/timeline duration.

## Drift protection

Immediately before immutable pool commit, re-query current `main` through the connector/API and compare it with `rules_source_sha`.

If main changed, use changed-path evidence where available:

| Class | Examples | Required action |
| --- | --- | --- |
| rules | planner, validation, media policy, shared planner docs | refresh affected exact-SHA contract/rules; repair if needed; rerun checkpoint |
| media | background registry/selected-asset facts | refresh selected-background evidence; rerun checkpoint |
| history | analytics, requests, results, planning pools | refresh affected semantic/editorial history; rerun checkpoint if authored bytes change |
| operational | recovery/completion/diagnostics evidence | continue without creative restart solely for unrelated operational drift |
| unknown | unclassified path | conservatively refresh affected contract/evidence and revalidate |

Do not restart all creative planning merely because an unrelated operational file changed.

## Validation model

ChatGPT owns semantic/editorial review. Mechanical facts are proven once by the canonical deterministic checkpoint. Do not duplicate it with a hand-written validation pass.

A checkpoint failure normally means:

```text
read exact diagnostic
→ repair affected authored field/candidate/selected asset
→ preserve unaffected work
→ rebuild draft bytes if changed
→ rerun same checkpoint
```

A successful checkpoint must report `commit_allowed=true` and all required candidates valid. The final committed pool bytes must exactly match checkpoint `draft_sha256`.

Developer/CI may separately run repository-native modules from a genuine Git checkout, including `--verify-git-head`. This mode is not a prerequisite or fallback requirement for ChatGPT/Work.

## Production boundary and historical compatibility

After a successful immutable pool commit, ChatGPT/Work planning ends. Private production workflows perform deterministic defense-in-depth validation, materialize canonical immutable requests and dispatch the public stateless runtime. They must not creatively rewrite/rerank stories, choose replacement backgrounds or repair malformed planner content.

Current planning-pool schema v2 expresses the simplified cardinality/category contract. Historical schema-v1 pools remain immutable and recoverable: 5-candidate Ad-hoc, 36-candidate Daily and scheduled Ad-hoc semantics remain available only through the historical compatibility path. Request schemas v4/v5/v6 also remain historical recovery formats.

No `production-runtime` change is required merely for this planner simplification because promoted schema-v7 request shape is unchanged.
