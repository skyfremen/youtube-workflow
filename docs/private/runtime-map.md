# Public Runtime Owner Map

This owner-only map explains the generic public surface. It is a debugging aid, not a second source of truth.

## Module responsibilities

| Public path | Owner responsibility |
| --- | --- |
| `runtime/core.py` | One-batch coordinator, bounded worker execution, generic public summary, and failure capture |
| `runtime/transport.py` | Exact-revision private input fetch, allowlisted state transport, explicit START creation, completion and diagnostic write-back |
| `runtime/base/contract.py` | Shared immutable request identity and output contract |
| `runtime/engine/batch.py` | Batch membership, ordering, uniqueness, sourcing-manifest validation, and schedule-slot validation |
| `runtime/engine/shard.py` | Deterministic 1–24 item partitioning into bounded single/paired execution units |
| `runtime/engine/pipeline.py` | Bounded internal concurrency and per-item failure isolation |
| `runtime/engine/aggregate.py` | Daily shard-summary validation, fail-closed aggregation, and partial-failure diagnostics |
| `runtime/engine/check.py` | Production-equivalent Dry Run test harness |
| `runtime/engine/benchmark.py` | Internal concurrency benchmark harness |
| `runtime/engine/evidence.py` | Test-only evidence export helper |
| `runtime/guard/readiness.py` | Shared fail-first environment, runtime, filesystem, registry, and remote-channel readiness checks |
| `runtime/guard/request.py` | Immutable state guard |
| `runtime/guard/schema.py` | Versioned canonical request schema, branding/publication validation, and schema-v5 background-treatment validation |
| `runtime/guard/semantic.py` | Planner-authored punchline contract validation |
| `runtime/resources/policy.py` | Background rendition suitability rules |
| `runtime/resources/quality.py` | Subtitle-safe-region readability sampling and bounded background darkening selection |
| `runtime/resources/resolve.py` | Background retrieval, probing, fallback, normalization, and frozen treatment execution |
| `runtime/resources/registry.py` | Provider-backed registry ingestion |
| `runtime/resources/validate.py` | Registry and selected-background validation |
| `runtime/transform/synth.py` | Narration synthesis backends |
| `runtime/transform/align.py` | Word-level narration alignment |
| `runtime/transform/semantic.py` | Deterministic mapping of planner punchline/emphasis text onto aligned narration words |
| `runtime/transform/compose.py` | 1080x1920 visual/audio composition |
| `runtime/transform/process.py` | Synthesis, alignment, active-word focus, semantic punchline styling, and composition entry point |
| `runtime/transform/verify.py` | Final media integrity verification |
| `runtime/output/access.py` | OAuth refresh and pinned-channel read-only preflight |
| `runtime/output/execute.py` | Recovery-first publication orchestration |
| `runtime/output/transfer.py` | Upload request construction and insertion fence |
| `runtime/output/state.py` | Immutable intent/upload recovery state |
| `runtime/output/progress.py` | Append-only liveness evidence and fail-closed current-attempt START reconstruction for GitHub partial reruns |
| `runtime/output/verify.py` | Exact remote publication-state verification |
| `runtime/output/receipt.py` | Immutable verified receipt finalization |
| `runtime/profile/config.py` | Shared production policy constants |
| `runtime/observe.py` | Stateless external-account observation and bounded analytics collection |
| `runtime/state_sink.py` | Validated write-back of the latest observation snapshot to canonical private state |
| `runtime/exercise.py` | Public Dry Run production-equivalent exercise |
| `runtime/errors.py` | Stable public error identifiers |

## Public error codes

| Code | Meaning | First owner check |
| --- | --- | --- |
| `E_START_001` | Execution-start heartbeat validation or private start-evidence write failed | Dispatch intent, opaque inputs, private-state token/repository, and `content/recovery/starts/` write-back |
| `E_PREPARE_001` | Runtime preparation failed | Container/source extraction and pinned image |
| `E_LOAD_001` | Exact private input load failed | `batch_id`, `source_sha`, token scope, and allowlisted paths |
| `E_EXEC_001` | One or more execution stages failed | Private diagnostic record, then immutable recovery state |
| `E_FINALIZE_001` | Completion or diagnostic finalization failed | Private repository write permission and concurrent state |
| `E_VERIFY_001` | Verification did not complete | Durable upload evidence and remote processing state |
| `E_STATE_001` | Private write-back was unavailable | Token contents permission and target branch |
| `E_AUTH_001` | External credential preflight failed | Environment credentials and pinned channel identity |
| `E_RESOURCE_001` | Required resource could not be resolved | Registry entry, rendition health, and provider access |

Execution failures write detailed traces to:
`youtube-shorts-bot/content/diagnostics/<batch_id>/<run_id>-<attempt>.json`.

Public logs intentionally retain only stage, item ordinal, stable error code, and aggregate counts. Canonical requests, schedules, content IDs, result receipts, analytics, and recovery records remain private.

## Dry Run stage aliases

| Public alias | Owner meaning |
| --- | --- |
| `s01` | Representative 24-item batch construction, shared orchestration, and failure-isolation fixture |
| `s02` | Production-render smoke exercise entered |
| `s02a` | Identity/font/emoji resource failure during render smoke |
| `s02b` | Generic FFmpeg/command failure during render smoke |
| `s02c` | Caption/card/pill/frame layout or rendering failure |
| `s02d` | Render metadata failure |
| `s02e` | Render-smoke assertion failure |
| `s02f` | Required render-smoke file missing |
| `s02g` | Required render-smoke data key missing |
| `s02h` | Render-smoke runtime error |
| `s02i` | Render-smoke `SystemExit` |
| `s02j` | Synthetic local background-generation subprocess failed |
| `s02k` | Caption-contrast subprocess failed |
| `s02l` | Other render subprocess failed |
| `s02m` | Rendered-frame extraction subprocess failed |
| `s02n` | Canonical `transform/verify.py` subprocess failed |
| `s02x` | Unclassified render-smoke exception |
| `s03` | Narration backend and approved-voice exercise |
| `s04` | Word alignment plus rendered active-word and semantic-punchline caption exercise |
| `s05` | Dry Run exercise completed |

## Public environment aliases

| Public alias | Private environment secret |
| --- | --- |
| `RUNTIME_AUTH_A` | `YOUTUBE_CLIENT_ID` |
| `RUNTIME_AUTH_B` | `YOUTUBE_CLIENT_SECRET` |
| `RUNTIME_AUTH_C` | `YOUTUBE_REFRESH_TOKEN` |
| `RUNTIME_SOURCE_KEY` | `PEXELS_API_KEY` |

These aliases change only the names repeated in public Actions logs. Secret values and integration semantics are unchanged.

## Manual recovery identity

A manual recovery batch ID hashes the immutable item identities together with `github.run_id`. A new manual trigger therefore gets a new immutable completion namespace, while reruns of the same workflow run retain the same batch ID. GitHub partial reruns get a new run-attempt identity; when prepare is not rerun, `runtime/output/progress.py` may create the missing current-attempt START only from exactly one prior matching START plus the unchanged immutable dispatch intent. Durable per-item upload records remain the duplicate-publication authority.

## 1080p, readability and voice contract

- `resources/policy.py` / private `media/background_policy.py`: effective post-crop rendition gate; 1080×1920 target; maximum 1.05× enlargement.
- `resources/quality.py`: samples 12 frames across the used segment's subtitle-safe region and chooses the bounded soft darkening strength.
- `resources/resolve.py`: keeps the reusable normalized master treatment-agnostic, then applies the immutable schema-v5 segment/playback treatment to the job-local input.
- `transform/compose.py`: 1080×1920/30, H.264 High CRF 19, yuv420p/BT.709, AAC-LC 48 kHz, scaled design and subtitle treatment.
- `guard/schema.py`: schema v5 is current for newly authored requests; schema v4 remains executable for staged migration/operator recovery. Both retain frozen lead gender/tone/voice and planner-authored punchline validation through the shared legacy view.
- `E_RESOURCE_001`: physical rendition/readability/preflight failure. Inspect the private diagnostic record for requested IDs, attempted rendition and underlying reason.

Voice map: female natural/general `af_heart`; female expressive `af_bella`; male natural/general `am_echo`; male expressive `am_fenrir`.

## Word-synchronised caption focus and semantic punchlines

- `transform/align.py` remains the timing authority. It performs deterministic forced alignment against the generated narration and requires at least 0.90 coverage before aligned captions are accepted.
- `transform/process.py` keeps each existing natural caption phrase fully visible while the currently spoken word receives active-word focus. The base caption remains white with the existing dark outline/shadow and caption-safe background protection.
- Adjacent words shorter than 120 ms may be grouped into a single active unit when their gap is at most 40 ms. A rapid unit is capped at three words to reduce flicker without turning the caption into a large highlighted phrase.
- Planner-authored `story.punchline` metadata is validated before execution. `transform/semantic.py` maps the exact punchline and optional emphasis text onto real aligned narration words; the runtime does not infer a punchline from audio position or heuristics.
- Semantic punchline styling is an additional aligned-caption layer. It is visually distinct from ordinary active-word focus while preserving the existing phrase geometry, safe margins, handle, subscribe treatment, and opening-card lifecycle.
- `CAPTION_WORD_HIGHLIGHT_ENABLED` controls active-word focus and `CAPTION_SEMANTIC_EMPHASIS_ENABLED` controls semantic emphasis; both default to the production-enabled path.
- If alignment is unavailable, malformed, incomplete, or below the existing coverage threshold, `process.py` preserves the existing estimated-caption fallback rather than inventing semantic timing or losing captions.
- Render metadata records alignment coverage, active-word focus, semantic-emphasis application, punchline match status, punchline word count, and emphasis word count.
- Daily and Ad-hoc execution do not have separate caption implementations: both converge through `engine/pipeline.py` into `transform/process.py`, so the same alignment/highlighting/semantic/fallback behaviour applies to both paths.
- The public Dry Run uses real Kokoro narration plus real alignment and renders a production-equivalent visual preview. It verifies active-word focus, semantic-emphasis pixels, caption safe margins, opening-card disappearance, handle/subscribe visibility, narration presence, and canonical render verification without performing a production upload.
