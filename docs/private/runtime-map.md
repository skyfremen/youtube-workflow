# Public Runtime Owner Map

This owner-only map explains the generic public surface. It is a debugging aid, not a second source of truth.

## Module responsibilities

| Public path | Owner responsibility |
| --- | --- |
| `runtime/core.py` | One-batch coordinator, bounded worker execution, generic public summary, and failure capture |
| `runtime/transport.py` | Exact-revision private input fetch, allowlisted state transport, completion and diagnostic write-back |
| `runtime/base/contract.py` | Shared immutable request identity and output contract |
| `runtime/engine/batch.py` | Batch membership, ordering, uniqueness, and schedule-slot validation |
| `runtime/engine/pipeline.py` | Bounded internal concurrency and per-item failure isolation |
| `runtime/engine/check.py` | Production-equivalent local test harness |
| `runtime/engine/benchmark.py` | Internal concurrency benchmark harness |
| `runtime/engine/evidence.py` | Test-only evidence export helper |
| `runtime/guard/request.py` | Immutable state guard |
| `runtime/guard/schema.py` | Canonical request schema and branding/publication validation |
| `runtime/resources/policy.py` | Background rendition suitability rules |
| `runtime/resources/select.py` | Registry shortlist and recency rules |
| `runtime/resources/resolve.py` | Background retrieval, probing, fallback, and normalization |
| `runtime/resources/registry.py` | Provider-backed registry ingestion |
| `runtime/resources/validate.py` | Registry and selected-background validation |
| `runtime/transform/synth.py` | Narration synthesis backends |
| `runtime/transform/align.py` | Word-level narration alignment |
| `runtime/transform/compose.py` | 720x1280 visual/audio composition |
| `runtime/transform/process.py` | Synthesis, alignment, and composition entry point |
| `runtime/transform/verify.py` | Final media integrity verification |
| `runtime/output/access.py` | OAuth refresh and pinned-channel read-only preflight |
| `runtime/output/execute.py` | Recovery-first publication orchestration |
| `runtime/output/transfer.py` | Upload request construction and insertion fence |
| `runtime/output/state.py` | Immutable intent/upload recovery state |
| `runtime/output/verify.py` | Exact remote publication-state verification |
| `runtime/output/receipt.py` | Immutable verified receipt finalization |
| `runtime/profile/config.py` | Shared production policy constants |
| `runtime/exercise.py` | Public Check production-equivalent exercise |
| `runtime/errors.py` | Stable public error identifiers |

## Public error codes

| Code | Meaning | First owner check |
| --- | --- | --- |
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


## Check stage aliases

| Public alias | Owner meaning |
| --- | --- |
| `s01` | Representative batch construction and failure isolation |
| `s02` | Transformation smoke test |
| `s02a`–`s02i`, `s02x` | Transformation asset, encoding, layout, metadata, or classified exception |
| `s03` | Narration backend exercise |
| `s04` | Word-alignment exercise |
| `s05` | Check completed |

## Public environment aliases

| Public alias | Private environment secret |
| --- | --- |
| `RUNTIME_AUTH_A` | `YOUTUBE_CLIENT_ID` |
| `RUNTIME_AUTH_B` | `YOUTUBE_CLIENT_SECRET` |
| `RUNTIME_AUTH_C` | `YOUTUBE_REFRESH_TOKEN` |
| `RUNTIME_SOURCE_KEY` | `PEXELS_API_KEY` |

These aliases change only the names repeated in public Actions logs. Secret values and integration semantics are unchanged.

## Manual recovery identity

A manual recovery batch ID hashes the immutable item identities together with `github.run_id`. A new manual trigger therefore gets a new immutable completion namespace, while reruns of the same workflow run retain the same batch ID. Durable per-item upload records remain the duplicate-publication authority.


## 1080p, readability and voice contract

- `resources/policy.py` / private `media/background_policy.py`: effective post-crop rendition gate; 1080×1920 target; maximum 1.05× enlargement.
- `resources/quality.py`: samples 12 frames across the used segment's subtitle-safe region and chooses the bounded soft darkening strength.
- `transform/compose.py`: 1080×1920/30, H.264 High CRF 19, yuv420p/BT.709, AAC-LC 48 kHz, scaled design and subtitle treatment.
- `guard/schema.py`: schema-v4 frozen lead gender/tone/voice validation; schema-v3 remains accepted only for recovery.
- `E_RESOURCE_001`: physical rendition/readability/preflight failure. Inspect the private diagnostic record for requested IDs, attempted rendition and underlying reason.

Voice map: female natural/general `af_heart`; female expressive `af_bella`; male natural/general `am_echo`; male expressive `am_fenrir`.
