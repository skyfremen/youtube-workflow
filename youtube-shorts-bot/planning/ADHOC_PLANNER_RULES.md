# Wacky Dramas — Ad-hoc Planner (schema v5 ranked-pool contract)

This is the single canonical Ad-hoc planning instruction for Wacky Dramas. It shares creative, analytics, metadata, safety, background and schema rules with `DAILY_PLANNER_PROMPT.md`, but it produces exactly one immediate-public Short from a ranked pool of five complete candidates.

Do not use a legacy V4 base prompt and do not use a retired planner-execution bridge.

## Repository-first rule

Before planning, inspect the current `main` branch of `skyfremen/youtube-workflow`. Repository code/configuration is authoritative when implementation details change.

Read at minimum:

- `planning/DAILY_PLANNER_PROMPT.md`
- `planning/STORY_RULES.md`
- `planning/planning_config.py`
- `planning/planning_engine.py`
- `planning/planner_contract.py`
- `planning/adhoc_precommit.py`
- `analytics/analytics_learning.py`
- current `analytics/latest.json` and `analytics/model.json` when present
- `validation/validate_content.py`
- `publishing/upload.py`
- `media/media_readiness.py`
- `media/background_selector.py`
- `media/background_treatment.py` as a **policy/history reference**, not an authoritative allocator
- `media/background_policy.py`
- `media/pexels_registry.py`
- `docs/background-media-strategy.md`
- `media-library/backgrounds.json`
- recent immutable `content/requests/*.json` and verified `content/results/*.json`
- `.github/workflows/background-management.yml`
- `.github/workflows/adhoc-production.yml`

Inspect `skyfremen/production-runtime` only when needed to verify the current single-item runtime/publication contract. Do not copy execution into the private repository.

## Ownership

**ChatGPT / Work owns the complete creative planning path and freezes final rank #1 through #5.** This includes candidate generation/rejection, duplicate reasoning, scoring/analytics interpretation, editorial comparison, story/title/metadata writing, voice, punchline semantics, exact backgrounds, planning-time background audit reasoning, replenishment candidate review, fallback decision and treatment values.

GitHub does not creatively select, generate, rewrite or repair a winner. Repository code supplies authoritative contract discovery, deterministic validation, Pexels metadata enrichment and registry persistence only. `adhoc-production.yml` validates candidates mechanically in the frozen AI order and promotes the first valid candidate.

There is no `planner-execution.yml`, no `planning/execution_bridge.py`, and no repository-side winner-selection round trip for new Ad-hoc pools.

## Mandatory live contract discovery

Do not manually remember or reproduce schema details that the repository can expose mechanically.

Before authoring the five final candidates, from `youtube-shorts-bot` execute:

```bash
python -m planning.planner_contract
```

Consume the actual returned JSON. Treat it as the live machine-readable planning contract for fields it exposes, including:

- request schema version;
- ranked-pool schema version and Ad-hoc pool size;
- valid planning modes;
- the canonical content-ID regular expression;
- candidate-ID contract;
- exact editorial/title/hook score-component names;
- controlled planning values;
- approved voices and tones;
- narration constants;
- exact immediate-public publication object;
- the shared media-readiness minimum inventory and category minimums.

Do not substitute remembered constants, stale cached output, manual arithmetic, or a previous run's contract output.

If the contract command cannot execute successfully, fail closed before creating an immutable pool.

`planner_contract.py` is a discovery surface only. It must import authoritative configuration/validation constants rather than become a second independently maintained copy of those rules.

## Shared media readiness and replenishment prerequisite

Daily and Ad-hoc use the single automatic, bounded, resumable procedure in
`docs/private/PLANNER_PROMPT.md`, `media.replenishment_state`, and
`docs/background-media-strategy.md`. This profile does not redefine that engine.

Ad-hoc must preserve its original planner invocation and content-ID namespace across
all replenishment attempts. After repository-backed readiness becomes `PASS`, resume
that same invocation and author the five-candidate ranked pool. Never select a
recovery-only asset or commit a pool while readiness is `REPLENISH`.

## Scheduled vs manual planning modes

Every pool must explicitly declare one of two modes:

- `scheduled_daily` — the normal once-per-day 01:00 Asia/Singapore Ad-hoc run;
- `manual_on_demand` — a distinct user-requested extra Ad-hoc run.

Every pool also records `singapore_date` as `YYYY-MM-DD`.

### scheduled_daily idempotency

For a scheduled run, all five candidate content IDs must use the namespace:

`wd-YYYYMMDDT010000-adhoc-...`

where the date is `singapore_date`.

The full content ID must also satisfy the exact live `content_id_pattern` returned by `planning.planner_contract`. Do not infer the random-suffix width or other details from examples.

Before creating a scheduled pool, inspect existing immutable requests and ranked pools for that date. If a canonical scheduled request already exists, do not create another pool; report/recover that exact request instead.

If a previous scheduled pool attempt exists but failed before any canonical request was promoted, a new immutable pool attempt with a different `pool_id` is allowed. Never edit/delete the failed pool.

Repository-side promotion independently enforces that at most one canonical scheduled Ad-hoc request exists for a Singapore date. Ad-hoc promotion workflows are serialized, and uniqueness is rechecked after rebasing onto latest `main` before the validated request is pushed.

### manual_on_demand

Manual/on-demand pools may use a distinct stable Ad-hoc identity and may coexist with the scheduled Daily Ad-hoc request, while preserving all immutable/fail-closed/publication rules.

## Candidate quality

Use the same business objective and quality bar as Daily. Generate/evaluate enough raw ideas to make five strong, genuinely different final candidates. Hard reject unsafe, misleading, incoherent, duplicate/near-duplicate, weak-payoff or visually dependent concepts.

All five final candidates must be complete production-quality Shorts, not placeholders. Rank them editorially #1 through #5. The reserves exist only so candidate-specific production-time validation failure does not collapse the Ad-hoc run.

Follow `STORY_RULES.md` and current Daily metadata/analytics rules. Each candidate must include complete story, title competition outcome, YouTube metadata, voice, semantic punchline, controlled planning fields, exact backgrounds and treatments.

When authoring score dictionaries, use the exact component names returned by the current live contract. In particular, never rename, paraphrase or guess configured score keys.

## Background audit and treatment ownership

For all five candidates ChatGPT must inspect the **readiness-PASS selectable registry**, current policy and private receipt history and freeze final background decisions.

For each candidate:

1. choose distinct primary/backup logical IDs;
2. require current selectable/registered/active/verified/commercial-use/watermark/text/quality/rendition hard facts;
3. reject any asset with `selection_enabled=false` even if it exists for historical recovery;
4. apply retention/readability, recency and story-fit evidence as planning judgment;
5. when a normal pair cannot safely satisfy the rules, ChatGPT may use the current configured emergency pair only if it independently remains selectable and safe; retired defaults are not permitted;
6. author both immutable treatments: `segment_start_seconds`, `segment_duration_seconds`, `playback_rate`;
7. avoid recently repeated segments/rates using current private receipt history;
8. `media/background_treatment.py` may be read for current treatment-policy constants/history interpretation, but its output is not an authoritative allocation decision;
9. when source duration is unknown/untrusted, use `segment_start_seconds=0` and `segment_duration_seconds=null` with a valid rate.

GitHub independently validates shared readiness plus hard registry/licensing/rendition/treatment facts; it never invents a replacement story/background/treatment.

## Ranked-pool contract

ChatGPT ultimately commits exactly one new immutable file per successful Ad-hoc planning attempt:

`youtube-shorts-bot/content/planning-pools/adhoc/ap-<stable-id>.json`

The commit subject must begin:

`[adhoc pool]`

Do not directly commit a new `content/requests/*.json`. `adhoc-production.yml` materializes the one canonical request only after validation.

The pool shape is:

```json
{
  "schema_version": 1,
  "pool_type": "adhoc",
  "pool_id": "ap-<same filename stem>",
  "planning_mode": "scheduled_daily",
  "singapore_date": "YYYY-MM-DD",
  "target_count": 1,
  "planning_execution": {
    "editorial_selection_owner": "chatgpt",
    "planning_method": "chatgpt_ranked_pool",
    "rules_source_sha": "<exact parent SHA inspected before this pool commit>",
    "ranked_candidate_ids": ["<exact 5 IDs in rank order>"]
  },
  "ranked_candidates": [
    {
      "rank": 1,
      "candidate_id": "...",
      "request": {"...": "complete schema-v5 immediate-public request"}
    }
  ]
}
```

Requirements:

- exactly **5** candidates;
- ranks exactly `1..5`, contiguous and unique;
- unique candidate IDs and request content IDs;
- every content ID contains `-adhoc-`;
- every content ID satisfies the current canonical content-ID pattern returned by `planning.planner_contract`;
- `scheduled_daily` content IDs use the exact date-scoped 01:00 namespace;
- every candidate uses the current request schema version returned by the live contract;
- `planning_execution.ranked_candidate_ids` exactly matches candidate order;
- `rules_source_sha` equals the exact parent of the eventual pool commit;
- every publication object exactly matches the current immediate-public object returned by the live contract.

For clarity, the current immediate-public shape is expected to resolve to this exact object (the live contract remains authoritative if it changes):

```json
{
  "mode": "immediate",
  "timezone": "Asia/Singapore",
  "publish_at": null
}
```

The upload body must resolve to YouTube `privacyStatus: public` with no `publishAt` field.

## Mandatory ChatGPT pre-commit validation and repair loop

The immutable planning-pool path is **not a drafting area**.

After ChatGPT has authored and frozen all five complete candidates, but **before creating any file under `content/planning-pools/adhoc/` and before any `[adhoc pool]` commit**:

1. resolve and retain the exact current repository HEAD:
   ```bash
   git rev-parse HEAD
   ```
2. ensure `planning_execution.rules_source_sha` in the draft equals that exact SHA;
3. rerun shared media readiness and require `status: PASS` immediately before draft validation;
4. write the complete pool to temporary working storage outside immutable repository state, for example `/tmp/wacky-adhoc-pool.json`;
5. from `youtube-shorts-bot`, execute the canonical validator against that exact temporary file:
   ```bash
   python -m planning.adhoc_precommit \
     --pool /tmp/wacky-adhoc-pool.json \
     --rules-source-sha <exact-head-sha>
   ```
6. consume the actual JSON output;
7. require all of the following:
   - `status == "PASS"`;
   - `commit_allowed == true`;
   - `valid_candidates == 5`;
   - `failed_candidates == 0`;
   - no pool errors;
   - every candidate result is `PASS`;
8. if validation fails, ChatGPT must read the exact errors, repair its own draft, and execute the validator again;
9. continue the repair/validation loop until the complete five-candidate draft passes;
10. never override, bypass, weaken or edit the validator merely to make an authored candidate pass;
11. never treat manual inspection or "this should pass" reasoning as a substitute for actual validator execution.

The pre-commit validator must use the same live request/schema/background/upload-body validation surfaces used by production promotion and must additionally require **all five** candidates to pass. Production promotion may still retain first-valid-candidate semantics for resilience; pre-commit authorship is deliberately stricter.

### Exact validated bytes

The pre-commit report returns `draft_sha256`.

After a 5/5 PASS:

- use the exact validated temporary file bytes as the immutable pool file;
- copy/move those bytes to the final `content/planning-pools/adhoc/<pool_id>.json` path;
- verify the final file SHA-256 equals the reported `draft_sha256`;
- do not reconstruct, reserialize, "clean up", or otherwise rewrite the pool after the successful validation;
- if any byte changes after validation, validate the changed file again before committing.

Immediately before committing, re-check that repository HEAD still equals `rules_source_sha`. If HEAD changed, fail closed, reload current repository rules, refresh the draft provenance as appropriate, rerun media readiness, and rerun the complete pre-commit validation. Do not commit a draft validated against a different parent.

Only after these checks may ChatGPT create the immutable `[adhoc pool]` commit.

## Promotion semantics

`adhoc-production.yml` processes only frozen rank order:

```text
#1 PASS -> promote #1 and stop
#1 FAIL, #2 PASS -> promote #2 and stop
...
all 5 FAIL -> fail closed
```

It must not re-rank, re-score, rewrite, fix or creatively substitute a candidate.

The private workflow sequence is:

```text
shared media readiness PASS
  -> ChatGPT 5/5 pre-commit PASS
  -> exact validated pool bytes committed on main
  -> private promotion preflight
  -> validate five candidates locally in AI rank order
  -> materialize one request locally
  -> create local [adhoc production] commit
  -> rebase onto latest main
  -> final schema/registry/immediate-public validation
  -> scheduled_daily uniqueness recheck on rebased state
  -> only then push the immutable request
  -> create opaque single execution
  -> dispatch public single.yml
```

A concurrent `main` update after final validation causes push failure rather than publication of unvalidated state.

## Recovery and idempotency

Once an immutable canonical Ad-hoc request exists, all retries/recovery reuse that exact content ID. Never create a replacement content ID merely because rendering/upload/verification failed.

A historical request may continue to resolve an asset later marked `selection_enabled=false`; that flag blocks **new planning**, not immutable recovery.

Preserve exact source SHA, compatibility fingerprint, dispatch/start evidence, upload intent, duplicate-upload protection, receipt verification and public/private state boundaries.

Ad-hoc never consumes or modifies Daily's 24 scheduled publication slots.

## Final pre-commit checklist

Before committing an Ad-hoc pool confirm:

- current repository rules/config/analytics/history were inspected;
- `planning.planner_contract` was actually executed and its current output consumed;
- shared `media.media_readiness` was actually executed and returned `PASS` on current `main`;
- if replenishment was needed, it completed through an immutable readiness manifest and Background Management before pool authorship;
- exactly 5 complete production-quality candidates exist;
- ranks and IDs are unique;
- `planning_mode` and `singapore_date` are correct;
- scheduled mode has no existing canonical scheduled request for that Singapore date;
- every content ID satisfies the live canonical regex and scheduled IDs use the correct 01:00 namespace;
- every candidate uses the current request schema and exact immediate-public contract;
- exact configured score-component names were taken from the live contract, not memory;
- ChatGPT owns all creative/editorial/background/treatment decisions;
- all selected backgrounds are currently selectable and none has `selection_enabled=false`;
- hard background/treatment expectations are satisfied;
- no planner-execution bridge is used;
- the complete temporary draft was actually validated with `planning.adhoc_precommit`;
- the final pre-commit result is 5/5 PASS with `commit_allowed=true`;
- the final immutable file bytes exactly match the validated `draft_sha256`;
- repository HEAD still equals the draft's `rules_source_sha`;
- exactly one new immutable pool file is added;
- commit subject begins `[adhoc pool]`.

If any checklist item cannot be proven from current repository state or actual command output, fail closed before commit.
