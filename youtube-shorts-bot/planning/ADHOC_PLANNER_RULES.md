# Wacky Dramas — Ad-hoc Planner Profile Rules

This file contains **Ad-hoc-specific** planning rules only. Shared execution, schema, background, recovery, connector/bootstrap, and checkpoint rules are owned by the current executable/shared surfaces and must not be redefined here.

Authoritative order for ChatGPT/Work:

1. `planning/ADHOC_PLANNER_PROMPT.md`
2. `docs/private/PLANNER_PROMPT.md`
3. `planning/PLANNER_MATERIALIZATION.json`
4. the exact-SHA `planning/connector_checkpoint.py` contract
5. `planning/STORY_RULES.md`
6. `docs/background-media-strategy.md`
7. this profile document for Ad-hoc-only policy

Repository code/configuration at the exact current `main` SHA is authoritative when implementation details change. ChatGPT/Work uses the authorized GitHub connector/API and the standalone connector checkpoint; shell Git and repository-tree reconstruction are not planner bootstrap requirements. Developers/CI may separately use the repository-native modules from a genuine checkout.

## Current profile contract

The current ranked-pool contract is intentionally:

- pool schema: current `POOL_SCHEMA_VERSION` exposed by the live contract;
- exactly **5** complete candidates in frozen rank order;
- ranks exactly `1..5`;
- `target_count=1`;
- planning modes: `scheduled_daily` and `manual_on_demand`;
- current new-request schema: **v7**;
- publication: immediate public using exactly `{"mode":"immediate","timezone":"Asia/Singapore","publish_at":null}`.

The five-candidate pool is deliberate resilience capacity. All five must be production-quality and pass planner-time checkpointing. Downstream promotion mechanically chooses the first still-valid candidate in frozen rank order; it never creatively re-ranks, rewrites, repairs, or substitutes a candidate.

## Identity and idempotency

### `scheduled_daily`

Use the once-per-Singapore-date 01:00 namespace required by the live contract. Before creating a pool, inspect immutable state for an existing canonical scheduled Ad-hoc request for that date. If one exists, recover/reuse it instead of replanning.

A failed immutable pool attempt may be followed by a new immutable pool attempt only when no canonical request was promoted. Never edit or delete the failed attempt.

### `manual_on_demand`

Allocate a distinct stable manual identity after current-state inspection. Multiple manual invocations may coexist on the same Singapore date. A same-date `scheduled_daily` request is not itself a manual collision.

## Creative ownership and quality

ChatGPT/Work owns candidate generation/rejection, duplicate reasoning, analytics/editorial judgment, complete story/title/metadata writing, lead gender/tone/voice semantics, semantic punchline metadata, exact logical backgrounds/ranges, visual-review/fallback reasoning, and final rank.

Repository code owns deterministic contract discovery, validation, immutable-state checks, promotion, recovery evidence, and dispatch. GitHub Actions must not perform creative winner selection.

Generate/evaluate enough ideas to produce five genuinely different final candidates. Hard-reject unsafe, misleading, incoherent, duplicate/near-duplicate, weak-payoff, exposition-dependent, or visually dependent concepts. Every final candidate must be complete production-ready material; reserves are not filler.

Use the live configured score-component names and controlled values. Follow `STORY_RULES.md` and current analytics-learning rules rather than copying constants into this document.

## Background readiness and schema-v7 ownership

Ad-hoc currently participates in the shared readiness-first, bounded replenishment contract defined by `docs/private/PLANNER_PROMPT.md`, `planning/PLANNER_MATERIALIZATION.json`, and `docs/background-media-strategy.md`. `REPLENISH` is a recoverable planner state under that current architecture; this profile does not implement a separate replenishment engine.

For new schema-v7 requests:

- use `concatenated_fit_to_short`;
- freeze one ordered primary sequence and one ordered backup sequence;
- each sequence contains 2-3 distinct atomic clips, with 3 preferred;
- each chosen range is at least 60 seconds;
- each sequence totals 210-300 seconds, with 240-300 preferred;
- primary and backup sequences are disjoint;
- freeze logical IDs, order, segment start, and segment duration;
- **do not freeze playback rate**; runtime derives the overall playback rate from the frozen unique source coverage and actual required output duration;
- never repeat a clip merely to fill time and never intentionally loop.

Eligibility is determined by the current registry/readiness policy (`status`, verification, licensing, watermark/text, quality/retention, trusted duration, and production rendition). Do not use retired `selection_enabled` semantics for new planning.

Historical request schemas remain recovery formats as defined by `validation.validate_content`; this profile document does not redefine their compatibility behavior.

## Connector-native checkpoint

Before immutable pool commit, use the exact-SHA standalone checkpoint and small connector-evidence envelope defined by `PLANNER_MATERIALIZATION.json`.

Required result:

- all 5 candidates `PASS`;
- `valid_candidates == 5`;
- `failed_candidates == 0`;
- `commit_allowed == true`;
- connector drift evidence proves current `main == rules_source_sha` at final checkpoint;
- selected-background evidence covers every logical background referenced by the pool;
- immutable pool bytes exactly match the returned `draft_sha256`.

Do not bypass or weaken the validator to make an authored candidate pass. If authored bytes change, rerun the checkpoint.

## Pool and promotion semantics

Commit exactly one new immutable Ad-hoc pool attempt under:

`youtube-shorts-bot/content/planning-pools/adhoc/ap-<stable-id>.json`

The commit subject begins `[adhoc pool]`. Do not directly create the canonical request from the planner.

`adhoc-production.yml` then:

1. admits the exact committed pool;
2. mechanically evaluates frozen rank order;
3. promotes the first valid candidate;
4. creates one immutable canonical request;
5. revalidates immediate-public semantics and scheduled-date uniqueness when applicable;
6. publishes canonical private state only after final validation;
7. creates one opaque execution and dispatches public `single.yml`.

Once a canonical immutable request exists, retries/recovery reuse that exact content ID and immutable request. Never create a replacement identity merely because rendering, upload, or verification failed.
