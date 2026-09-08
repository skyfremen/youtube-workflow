# Private upload recovery and migration acceptance

The canonical request and result receipt remain immutable. `content/recovery/<content_id>/intent.json` and `upload.json` are append-only evidence, not requests, queue entries, or success receipts.

## Retry contract

1. Resolve the original request-addition commit and compare the current request bytes with that exact Git blob. Production executes current `main` code and records its separate code SHA.
2. Read the canonical receipt and upload record from GitHub before downloading media or rendering. A known video ID is restored directly from durable evidence. The authenticated channel must match pinned channel ID `UCvrq2m9G4yrwPfL_X-QPzMA`.
3. For a genuinely new request, enumerate the channel upload inventory before authorizing a first upload. An incomplete inventory, duplicate matches, missing credentials, inconsistent evidence, or an older request without imported evidence blocks uploading.
4. After render verification, create an immutable upload intent on `main` using a create-only GitHub Contents write. Only the attempt receiving the acknowledged creation may call `videos.insert`. The intent contains request/source identity, channel, exact upload metadata, original run/attempt/code SHA, measured render data, and selected background.
5. Capture the upload response locally immediately, then persist its video ID in the immutable upload record before verification. If any response or write is lost, the durable intent prohibits a new insert. Recovery may search the complete uploads playlist using the full request/blob description marker or either known tag format. No observable match is an unresolved state, never permission to upload again. Multiple matches require reconciliation.
6. Reverify the intended video through the authenticated owner on every run, including completed-receipt reruns: matching ID/channel, exact PRIVATE status, no `publishAt` key, expected title/description/category, processed status, and request association through the immutable upload-record blob. Tags are supplemental evidence; absence during propagation cannot defeat an already durable ID association. Bounded visibility/processing checks use six attempts with delays of 0, 2, 4, 8, 16 and 30 seconds. Real metadata/privacy mismatches fail immediately.
7. Only after verification passes, create the complete result receipt through a create-only GitHub write. An existing receipt is checked and reused without changing its bytes. Failed receipt commits retry verification and persistence against the same upload record.

For routine recovery, manually run **Wacky Dramas Ad-hoc Private Publish** on `main` with the existing `content_id` and `recovery_only=true`. The dedicated acceptance workflow is now manual-only and fixes the ID to the original acceptance request. Its default does not render or upload anything. An explicit `render_preview=true` on the canonical workflow is for debugging/migration and creates a separate preview artifact; it does not replace an existing YouTube video.

Never delete an intent to clear an ambiguous upload. Never set a force-reupload flag. For requests predating durable intents, import verified original workflow evidence; do not infer non-upload from a failed run. The original historical workflow definition remains on GitHub; use the current workflow's recovery entry point, not historical code versions.

## Original acceptance evidence

| Fact | Verified value |
| --- | --- |
| Content ID | `wd-20260909T004900-unpaid-overtime-c84f2a` |
| Request | `content/requests/wd-20260909T004900-unpaid-overtime-c84f2a.json` |
| Request blob | `8efe3f1a468445c7c18a0328d2780be47fe5a6b4` |
| Request/source and original renderer commit | `f6e3bdcbfd4368fde8e2e8b552d3915002727188` |
| Canonical video | `vUTeNhM0UH8` |
| Status | PRIVATE, processed, `publishAt` absent |
| Original upload run / job | `34253369477` / `102152963276`, attempt 1 |
| Diagnostics artifact | `10066917641`, SHA256 `381307ed1662652ddbf11a56a230388e65737c73d4f7b6a322ae925d3d42c4fb` |
| Owner API inspection run | `34255131587`, artifact `10067580327` |
| Recovery and receipt run | `34257076175`, attempt 1, job `102165478728` |
| Receipt commit | `5b5be52deb49305b2472ded1a923d52d281032a8` |
| Receipt blob | `281131c8729d9a616d3d44d61e04281c5ce71ee6` |
| Same-ID successful rerun | `34257076175`, attempt 2, job `102166241319` |
| Main dry run | `34257075730`: all 49 tests and zero-side-effect checks passed |
| Selected background | `satisfying-008`, primary |
| Narration | Kokoro `af_heart`, 1.75x, 4.875 seconds |
| Original file | 5.233 seconds, 720x1280, 30 fps, H.264, exactly one AAC stream; 456788 bytes |
| Test provenance | Migration acceptance excerpt, not a full production story |

The request blob is unchanged. GitHub lists exactly one commit for the result receipt. Attempt 2 reverified PRIVATE status, restored the same upload-record blob, and reused the exact receipt blob. The background-download, narration/render, upload and preview steps were all skipped. This recovery work made zero YouTube uploads and zero metadata changes.

## Marker failure diagnosis

The original verifier reported the full recovery tag missing approximately 0.6 seconds after the upload-response checkpoint. It retried an absent video but immediately failed an absent tag. The later read-only owner inspection returned the original full tag intact:

`wd-id-wd-20260909T004900-unpaid-overtime-c84f2a`

No metadata update was needed or performed during recovery. The original request used `videos.insert(part="snippet,status")` and `snippet.tags`; the subsequent read used the same parts. The API later returned the expected title, description, category and full tag. The evidence supports read-after-write metadata propagation, exposed by the verifier's premature terminal failure. The original failed run did not retain the complete API response, and the exact propagation interval is unknown. It is not evidence of a tag-length restriction: shortening the marker in an intervening external change also produced an immediate verification failure on a different request.

[YouTube documents a 500-character combined tag limit](https://developers.google.com/youtube/v3/docs/videos#snippet.tags), including separators and quote accounting. The repository's 30-character marker budget is a local choice, not a documented per-tag API limit. Recovery recognizes both the original long marker and the later compact marker. Durable GitHub intent/ID evidence removes dependence on either being immediately observable.

## Visual assessment and readiness

**Technical recovery and same-ID idempotency passed. Overall migration acceptance is not complete.**

The original preserved opening-card PNG contains dot fallbacks instead of emojis and a silently truncated hook. The actual YouTube thumbnail confirms horizontally clipped captions. These defects are already baked into `vUTeNhM0UH8`.

The renderer on `main` now fits the complete hook or fails explicitly, renders recognizable larger emojis at the font's supported bitmap size, and inserts measured caption line breaks within 104-pixel horizontal margins. It preserves the original logo, message-style comment icon, distinct like/comment counts, central captions, dark rounded handle pill and yellow Subscribe pill. A separate same-request preview from run `34257076175` attempt 1 was reviewed at 0.5, 1.2 and 2.3 seconds. The opening card is high and contained; the three-line long caption stays centered and clear of the card; the card is gone after two seconds; branding and Subscribe remain within the intended lower safe area. Background motion changes visibly across the frames and remains unobtrusive. The preview's measured frame rate is 30/1 for both nominal and average rates, with H.264 plus one AAC stream.

Preview artifact: `10068352464` (`wacky-dramas-visual-preview-34257076175-1`). Its MP4 SHA256 is `6dfe9d556abfd6a79a4be91f20d760d176902997474b0cf58582fd801107aa03`. This is a debug preview, not the canonical uploaded video. Its duration and narration excerpt match the original acceptance settings. Stream provenance proves only the narration input is mapped; no background audio is mapped or mixed. Auditory intelligibility has not been certified because this execution environment cannot consume audio input. A full 120–175-second production render has not been exercised by this five-second acceptance test.

The authenticated YouTube channel still reports `Wacky Insights` and `@wackyinsights`. Repository/video overlays are Wacky Dramas, but the live channel rename remains outstanding.

[YouTube does not support replacing a video's media under the same ID](https://support.google.com/youtube/answer/55770?hl=en). Fixing the existing video's baked-in captions/card would require a new upload. The original video is recoverable, and the user explicitly forbids a replacement acceptance upload in this case. Therefore no replacement request or upload was created, and no visual pass is claimed for the original video.

An unrelated concurrent commit, `325ec685bf4c7b9846937ae9b0acb58628abe5a1`, added `wd-20260909T010256-overtime-email-e4b91c` while this audit began. Its run `34254775751` uploaded `D7aDEZDreZ4` before failing the compact-tag verification. That request/video was not created, modified, rerun, or deleted by this recovery work. It remains separate from the canonical original acceptance ID.

The Daily Shorts Planner was observed disabled. No recurring, hourly, queue, series or background-audio path was introduced. Legacy disabled workflows were preserved. Dockerfile and runtime dependencies did not change; no GHCR rebuild was triggered. Routine successful and rerun jobs keep only lightweight evidence; the single MP4 artifact was explicitly for migration visual review.
