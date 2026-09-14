# Wacky Dramas — Daily Planner Profile Rules

This file contains **Daily-specific** planning rules only. Shared execution, schema, background, recovery, connector/bootstrap, and checkpoint rules are owned by the current executable/shared surfaces and must not be redefined here.

Authoritative order for ChatGPT/Work:

1. `planning/DAILY_PLANNER_PROMPT.md`
2. `docs/private/PLANNER_PROMPT.md`
3. `planning/PLANNER_MATERIALIZATION.json`
4. the exact-SHA `planning/connector_checkpoint.py` contract
5. `planning/STORY_RULES.md`
6. `docs/background-media-strategy.md`
7. this profile document for Daily-only policy

Repository code/configuration at the exact current `main` SHA is authoritative when implementation details change. ChatGPT/Work uses the authorized GitHub connector/API and the standalone connector checkpoint; shell Git and repository-tree reconstruction are not planner bootstrap requirements. Developers/CI may separately use the repository-native modules from a genuine checkout.

## Current profile contract

The current ranked-pool contract is intentionally:

- pool schema: current `POOL_SCHEMA_VERSION` exposed by the live contract;
- exactly **36** complete candidates in frozen rank order;
- ranks exactly `1..36`;
- `normal_next_day` target count: exactly **24**;
- `same_day_catch_up` target count: exactly the number of valid remaining publication slots, from 1 through 24;
- current new-request schema: **v7**;
- publication template before promotion: exactly `{"mode":"scheduled","timezone":"Asia/Singapore","publish_at":null}`.

The 36-candidate pool is deliberate resilience capacity. All 36 candidates must be production-quality and pass planner-time checkpointing. Downstream promotion walks frozen rank order and selects the first `target_count` candidates that are still mechanically valid; it never creatively re-ranks, rewrites, repairs, or substitutes a candidate.

## Daily scheduling

The normal Daily planner runs at **20:00 Asia/Singapore**.

For `normal_next_day`:

- plan the next Singapore calendar day;
- `target_count=24`;
- use exactly the 24 top-of-hour Singapore slots from 00:00 through 23:00;
- persist slots as canonical UTC RFC3339 timestamps in chronological order;
- author exactly 36 ranked candidates.

For `same_day_catch_up`:

- use the current Singapore calendar day;
- retain only exact top-of-hour slots at least **30 minutes in the future**;
- set `target_count` equal to the number of retained slots;
- keep those slots unique and chronological;
- author exactly 36 ranked candidates under the current ranked-reserve contract;
- immediately before pool commit, refresh Singapore time and remove any slot that no longer meets the lead-time rule.

If no valid catch-up slot remains, fail closed. If canonical `content/planning/YYYY-MM-DD.json` already exists, do not create another pool; recover the existing immutable content IDs instead.

## Creative ownership and quality

ChatGPT/Work owns raw premise generation/rejection, duplicate reasoning, semantic/editorial scoring, analytics interpretation, exploit/explore and diversity judgment, hooks/endings/title competition, complete story/title/metadata writing, lead gender/tone/voice semantics, semantic punchline metadata, exact logical backgrounds/ranges, visual-review/fallback reasoning, and final rank.

Repository code owns deterministic contract discovery, validation, immutable-state checks, promotion, recovery evidence, and dispatch. GitHub Actions must not perform creative ranking or winner selection.

The current broad funnel remains approximately:

`>=120 raw premises -> hard semantic filtering -> strong developed contenders -> >=5 materially different truthful title options for serious contenders -> final editorial/diversity/analytics comparison -> 36 complete ranked candidates`.

Hard rejection overrides scores. Reject unsafe, misleading, incoherent, weak-payoff, exposition-dependent, visually dependent, duplicate/near-duplicate, or superficial role-swap concepts. Reserve positions are not permission for filler.

Use the live configured score-component names, controlled values, diversity limits, and analytics-confidence rules from current code. Follow `STORY_RULES.md` rather than copying shared constants here.

## Background readiness and schema-v7 ownership

Daily currently participates in the shared readiness-first, bounded replenishment contract defined by `docs/private/PLANNER_PROMPT.md`, `planning/PLANNER_MATERIALIZATION.json`, and `docs/background-media-strategy.md`. `REPLENISH` is a recoverable planner state under that current architecture; this profile does not implement a separate replenishment engine.

For new schema-v7 requests:

- use `concatenated_fit_to_short`;
- freeze one ordered primary sequence and one ordered backup sequence;
- each sequence contains 2-3 distinct atomic clips, with 3 preferred;
- each chosen range is at least 60 seconds;
- each sequence totals 210-300 seconds, with 240-300 preferred;
- primary and backup sequences are disjoint;
- freeze logical IDs, order, segment start, and segment duration;
- **do not freeze playback rate**; runtime derives the overall playback rate from the frozen unique source coverage and actual required output duration;
- never repeat a clip merely to fill time and never intentionally loop;
- preserve batch-level variety using current private receipt/history evidence.

Eligibility is determined by the current registry/readiness policy (`status`, verification, licensing, watermark/text, quality/retention, trusted duration, and production rendition). Do not use retired `selection_enabled` semantics for new planning.

Historical request schemas remain recovery formats as defined by `validation.validate_content`; this profile document does not redefine their compatibility behavior.

## Connector-native checkpoint

Before immutable pool commit, use the exact-SHA standalone checkpoint and small connector-evidence envelope defined by `PLANNER_MATERIALIZATION.json`.

Required result:

- all 36 candidates `PASS`;
- `valid_candidates == 36`;
- `failed_candidates == 0`;
- `commit_allowed == true`;
- connector drift evidence proves current `main == rules_source_sha` at final checkpoint;
- selected-background evidence covers every logical background referenced by the pool;
- immutable pool bytes exactly match the returned `draft_sha256`.

Do not bypass or weaken the validator to make an authored candidate pass. If authored bytes change, rerun the checkpoint.

## Pool and promotion semantics

Commit exactly one new immutable Daily pool attempt under:

`youtube-shorts-bot/content/planning-pools/daily/YYYY-MM-DD/dp-<attempt-id>.json`

The commit subject begins `[daily pool] YYYY-MM-DD`. A failed immutable attempt is never edited or deleted; if no canonical Daily plan exists, a corrected new attempt may be created. Once the canonical plan exists, use recovery instead of replanning.

`daily-production.yml` then:

1. admits the exact committed pool;
2. mechanically walks frozen rank order;
3. promotes the first `target_count` valid candidates onto the frozen publication slots;
4. materializes immutable requests and the canonical planning audit;
5. revalidates the rebased canonical state;
6. publishes private state only after final validation;
7. dispatches one opaque public-runtime batch.

For a normal day, successful canonical state contains exactly 24 immutable requests. For catch-up, successful canonical state contains exactly `target_count` immutable requests.

Once immutable requests exist, retries/recovery reuse those exact content IDs and source identities. Never rewrite historical immutable production state to match a newer planning contract.
