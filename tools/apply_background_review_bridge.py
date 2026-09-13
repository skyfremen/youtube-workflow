from pathlib import Path


def replace_between(path, start, end, replacement):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"missing start marker in {path}: {start!r}")
    j = text.find(end, i)
    if j < 0:
        raise SystemExit(f"missing end marker in {path}: {end!r}")
    path.write_text(text[:i] + replacement.rstrip() + "\n\n" + text[j:], encoding="utf-8")


BACKGROUND_WORKFLOW = r'''name: Background Management

env:
  PYTHONPATH: youtube-shorts-bot

on:
  workflow_dispatch:
    inputs:
      review_request_id:
        description: Optional immutable discovery request ID to regenerate review evidence
        required: false
        type: string
  push:
    branches: [main]
    paths:
      - 'youtube-shorts-bot/content/background-sourcing/discovery-requests/*.json'
      - 'youtube-shorts-bot/content/background-sourcing/readiness/*.json'
      - 'youtube-shorts-bot/media-library/backgrounds.json'
      - 'youtube-shorts-bot/media/media_readiness.py'
      - 'youtube-shorts-bot/media/pexels_discovery.py'
      - 'youtube-shorts-bot/media/pexels_registry.py'
      - 'youtube-shorts-bot/media/pexels_resilient_ingest.py'
      - 'youtube-shorts-bot/media/background_policy.py'
      - 'youtube-shorts-bot/media/continuous_background.py'
      - 'youtube-shorts-bot/media/preview_review_materializer.py'
      - 'youtube-shorts-bot/docs/background-media-strategy.md'
      - '.github/workflows/background-management.yml'

concurrency:
  group: wacky-dramas-background-registry-maintenance-v2
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  maintain:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    env:
      PEXELS_API_KEY: ${{ secrets.PEXELS_API_KEY }}
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          fetch-depth: 0
          ref: main

      - name: Resolve maintenance action
        id: action
        shell: bash
        env:
          BEFORE_SHA: ${{ github.event.before }}
          REQUESTED_REVIEW_ID: ${{ inputs.review_request_id || '' }}
        run: |
          set -euo pipefail
          action=audit
          manifest=''
          discovery_request=''
          discovery_output=''
          review_output=''
          review_artifact=''
          review_index=''
          request_id=''

          set_review_fields() {
            request_id="$(basename "${discovery_output}" .json)"
            review_output="/tmp/wacky-background-review/${request_id}"
            review_artifact="background-review-evidence-${request_id}-${GITHUB_RUN_ID}"
            review_index="youtube-shorts-bot/content/background-sourcing/review-evidence/${request_id}-run-${GITHUB_RUN_ID}.json"
          }

          if [ "${GITHUB_EVENT_NAME}" = "workflow_dispatch" ] && [ -n "${REQUESTED_REVIEW_ID}" ]; then
            if [[ ! "${REQUESTED_REVIEW_ID}" =~ ^dr-[A-Za-z0-9-]{8,96}$ ]]; then
              echo '::error::review_request_id has invalid format.'
              exit 1
            fi
            discovery_output="youtube-shorts-bot/content/background-sourcing/discovery-results/${REQUESTED_REVIEW_ID}.json"
            test -f "${discovery_output}" || { echo '::error::Requested discovery result does not exist.'; exit 1; }
            action=review
            set_review_fields
          elif [ "${GITHUB_EVENT_NAME}" = "push" ]; then
            changed="$(git diff --name-status "${BEFORE_SHA}" "${GITHUB_SHA}")"
            mapfile -t readiness_files < <(printf '%s\n' "${changed}" | awk '$1 == "A" && $2 ~ /^youtube-shorts-bot\/content\/background-sourcing\/readiness\/[A-Za-z0-9._-]+\.json$/ {print $2}')
            mapfile -t discovery_files < <(printf '%s\n' "${changed}" | awk '$1 == "A" && $2 ~ /^youtube-shorts-bot\/content\/background-sourcing\/discovery-requests\/[A-Za-z0-9._-]+\.json$/ {print $2}')
            if [ "${#readiness_files[@]}" -gt 1 ] || [ "${#discovery_files[@]}" -gt 1 ]; then
              echo '::error::One push may add at most one readiness manifest and one discovery request.'
              exit 1
            fi
            if [ "${#readiness_files[@]}" -eq 1 ] && [ "${#discovery_files[@]}" -eq 1 ]; then
              echo '::error::Do not add a readiness manifest and discovery request in the same push.'
              exit 1
            fi
            if [ "${#readiness_files[@]}" -eq 1 ]; then
              action=replenish
              manifest="${readiness_files[0]}"
            elif [ "${#discovery_files[@]}" -eq 1 ]; then
              action=discover
              discovery_request="${discovery_files[0]}"
              base="$(basename "${discovery_request}")"
              discovery_output="youtube-shorts-bot/content/background-sourcing/discovery-results/${base}"
              set_review_fields
            fi
          fi

          # A code/config change or manual audit can backfill the newest discovery
          # result that has never received a GitHub-to-ChatGPT review artifact.
          if [ "${action}" = "audit" ]; then
            while IFS= read -r candidate; do
              [ -n "${candidate}" ] || continue
              candidate_id="$(basename "${candidate}" .json)"
              if ! compgen -G "youtube-shorts-bot/content/background-sourcing/review-evidence/${candidate_id}-run-*.json" >/dev/null; then
                action=review
                discovery_output="${candidate}"
                set_review_fields
                break
              fi
            done < <(find youtube-shorts-bot/content/background-sourcing/discovery-results \
              -maxdepth 1 -type f -name 'dr-*.json' -print 2>/dev/null | sort -r)
          fi

          echo "action=${action}" >> "${GITHUB_OUTPUT}"
          echo "manifest=${manifest}" >> "${GITHUB_OUTPUT}"
          echo "discovery_request=${discovery_request}" >> "${GITHUB_OUTPUT}"
          echo "discovery_output=${discovery_output}" >> "${GITHUB_OUTPUT}"
          echo "request_id=${request_id}" >> "${GITHUB_OUTPUT}"
          echo "review_output=${review_output}" >> "${GITHUB_OUTPUT}"
          echo "review_artifact=${review_artifact}" >> "${GITHUB_OUTPUT}"
          echo "review_index=${review_index}" >> "${GITHUB_OUTPUT}"

      - name: Require Pexels API key
        if: steps.action.outputs.action == 'replenish' || steps.action.outputs.action == 'discover'
        shell: bash
        run: |
          set -euo pipefail
          test -n "${PEXELS_API_KEY}" || { echo '::error::PEXELS_API_KEY is required.'; exit 1; }

      - name: Discover long production-suitable Pexels candidates
        if: steps.action.outputs.action == 'discover'
        env:
          REQUEST: ${{ steps.action.outputs.discovery_request }}
          OUTPUT: ${{ steps.action.outputs.discovery_output }}
        run: python -m media.pexels_discovery --request "${REQUEST}" --output "${OUTPUT}"

      - name: Filter already-approved candidates from review transport
        if: steps.action.outputs.action == 'discover' || steps.action.outputs.action == 'review'
        id: review_source
        env:
          OUTPUT: ${{ steps.action.outputs.discovery_output }}
        shell: bash
        run: |
          set -euo pipefail
          filtered="/tmp/pending-review-${{ steps.action.outputs.request_id }}.json"
          python - "${OUTPUT}" "${filtered}" <<'PY'
          import json
          import sys
          from pathlib import Path

          discovery_path = Path(sys.argv[1])
          filtered_path = Path(sys.argv[2])
          discovery = json.loads(discovery_path.read_text(encoding='utf-8'))
          registry = json.loads(Path('youtube-shorts-bot/media-library/backgrounds.json').read_text(encoding='utf-8'))
          approved = {
              str(item.get('provider_asset_id') or '')
              for item in registry.get('assets', [])
              if item.get('status') == 'active'
              and item.get('verified') is True
              and str(item.get('provider_asset_id') or '').isdigit()
          }
          pending = [
              item for item in discovery.get('candidates', [])
              if str(item.get('provider_asset_id') or '') not in approved
          ]
          filtered_doc = dict(discovery)
          filtered_doc['candidates'] = pending
          filtered_doc['candidate_count'] = len(pending)
          filtered_doc['review_transport_filter'] = {
              'source_candidate_count': len(discovery.get('candidates', [])),
              'already_approved_provider_ids': sorted(approved),
              'pending_candidate_count': len(pending),
              'rule': 'Transport optimization only; approval remains derived from the active registry and ChatGPT review.',
          }
          filtered_path.write_text(json.dumps(filtered_doc, indent=2) + '\n', encoding='utf-8')
          print(json.dumps({
              'source_candidates': len(discovery.get('candidates', [])),
              'pending_candidates': len(pending),
          }))
          PY
          echo "path=${filtered}" >> "${GITHUB_OUTPUT}"

      - name: Materialize exact-source review contact sheets
        if: steps.action.outputs.action == 'discover' || steps.action.outputs.action == 'review'
        env:
          REVIEW_SOURCE: ${{ steps.review_source.outputs.path }}
          REVIEW_OUTPUT: ${{ steps.action.outputs.review_output }}
        shell: bash
        run: |
          set -euo pipefail
          rm -rf "${REVIEW_OUTPUT}"
          python -m media.preview_review_materializer \
            --discovery-result "${REVIEW_SOURCE}" \
            --output-dir "${REVIEW_OUTPUT}" \
            --contact-sheets-only

      - name: Upload ChatGPT review evidence
        id: review_artifact
        if: steps.action.outputs.action == 'discover' || steps.action.outputs.action == 'review'
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2
        with:
          name: ${{ steps.action.outputs.review_artifact }}
          path: |
            ${{ steps.action.outputs.review_output }}/evidence-manifest.json
            ${{ steps.action.outputs.review_output }}/*/preview.jpg
            ${{ steps.action.outputs.review_output }}/*/contact-sheet.jpg
          if-no-files-found: error
          retention-days: 3
          compression-level: 6

      - name: Write immutable review evidence index
        if: steps.action.outputs.action == 'discover' || steps.action.outputs.action == 'review'
        env:
          REQUEST_ID: ${{ steps.action.outputs.request_id }}
          DISCOVERY_RESULT: ${{ steps.action.outputs.discovery_output }}
          REVIEW_OUTPUT: ${{ steps.action.outputs.review_output }}
          REVIEW_INDEX: ${{ steps.action.outputs.review_index }}
          ARTIFACT_ID: ${{ steps.review_artifact.outputs.artifact-id }}
          ARTIFACT_NAME: ${{ steps.action.outputs.review_artifact }}
          ARTIFACT_DIGEST: ${{ steps.review_artifact.outputs.artifact-digest }}
          ARTIFACT_URL: ${{ steps.review_artifact.outputs.artifact-url }}
        run: |
          python - <<'PY'
          import hashlib
          import json
          import os
          from pathlib import Path

          evidence_path = Path(os.environ['REVIEW_OUTPUT']) / 'evidence-manifest.json'
          evidence_bytes = evidence_path.read_bytes()
          evidence = json.loads(evidence_bytes)
          provider_ids = [
              str(item['provider_asset_id'])
              for item in evidence.get('evidence', [])
              if isinstance(item, dict) and item.get('motion', {}).get('contact_sheet')
          ]
          index = {
              'schema_version': 1,
              'request_id': os.environ['REQUEST_ID'],
              'discovery_result': os.environ['DISCOVERY_RESULT'],
              'workflow': 'Background Management',
              'workflow_run_id': int(os.environ['GITHUB_RUN_ID']),
              'workflow_run_attempt': int(os.environ['GITHUB_RUN_ATTEMPT']),
              'artifact_id': int(os.environ['ARTIFACT_ID']),
              'artifact_name': os.environ['ARTIFACT_NAME'],
              'artifact_digest': os.environ.get('ARTIFACT_DIGEST') or None,
              'artifact_url': os.environ.get('ARTIFACT_URL') or None,
              'artifact_retention_days': 3,
              'evidence_manifest_sha256': hashlib.sha256(evidence_bytes).hexdigest(),
              'evidence_count': int(evidence.get('evidence_count') or 0),
              'failure_count': int(evidence.get('failure_count') or 0),
              'contact_sheet_count': len(provider_ids),
              'provider_asset_ids_with_contact_sheet': provider_ids,
              'artifact_contents': [
                  'evidence-manifest.json',
                  '<provider_asset_id>/preview.jpg (when exact still transport succeeds)',
                  '<provider_asset_id>/contact-sheet.jpg',
              ],
              'rule': (
                  'Transport evidence only. GitHub generated representative JPEGs from the exact '
                  'provider asset; ChatGPT/Work remains the sole visual/editorial approval owner.'
              ),
          }
          output = Path(os.environ['REVIEW_INDEX'])
          output.parent.mkdir(parents=True, exist_ok=True)
          if output.exists():
              raise SystemExit(f'review evidence index is immutable and already exists: {output}')
          output.write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
          print(json.dumps(index, indent=2))
          PY

      - name: Commit discovery result and review evidence index
        if: steps.action.outputs.action == 'discover' || steps.action.outputs.action == 'review'
        shell: bash
        env:
          ACTION: ${{ steps.action.outputs.action }}
          OUTPUT: ${{ steps.action.outputs.discovery_output }}
          REVIEW_INDEX: ${{ steps.action.outputs.review_index }}
        run: |
          set -euo pipefail
          test -f "${OUTPUT}"
          test -f "${REVIEW_INDEX}"
          git config user.name github-actions[bot]
          git config user.email 41898282+github-actions[bot]@users.noreply.github.com
          if [ "${ACTION}" = "discover" ]; then
            git add "${OUTPUT}"
            message='[media discovery] add Pexels candidates and review evidence index'
          else
            message='[media review] add contact-sheet evidence index'
          fi
          git add "${REVIEW_INDEX}"
          git commit -m "${message}"
          git pull --rebase origin main
          git push origin HEAD:main

      - name: Ingest reviewed readiness manifest with reserve fallback
        if: steps.action.outputs.action == 'replenish'
        env:
          MANIFEST: ${{ steps.action.outputs.manifest }}
        run: python -m media.pexels_resilient_ingest --manifest "${MANIFEST}"

      - name: Validate active registry structure
        run: python youtube-shorts-bot/media/validate_media_library.py

      - name: Commit registry maintenance
        if: steps.action.outputs.action == 'replenish'
        shell: bash
        run: |
          set -euo pipefail
          if git diff --quiet -- youtube-shorts-bot/media-library/backgrounds.json; then
            echo 'Registry is already current.'
            exit 0
          fi
          git config user.name github-actions[bot]
          git config user.email 41898282+github-actions[bot]@users.noreply.github.com
          git add youtube-shorts-bot/media-library/backgrounds.json
          git commit -m '[media readiness] replenish continuous background registry'
          git pull --rebase origin main
          git push origin HEAD:main

      - name: Enforce readiness after persisted replenishment
        if: steps.action.outputs.action == 'replenish'
        run: python -m media.media_readiness audit --allow-not-ready

      - name: Report expected empty or insufficient state
        if: steps.action.outputs.action != 'replenish'
        run: python -m media.media_readiness audit --allow-not-ready
'''

Path('.github/workflows/background-management.yml').write_text(BACKGROUND_WORKFLOW, encoding='utf-8')

# Add a contact-sheet-only mode so the GitHub artifact remains lightweight.
materializer = Path('youtube-shorts-bot/media/preview_review_materializer.py')
text = materializer.read_text(encoding='utf-8')
text = text.replace(
    'When\n``--include-motion-evidence`` is supplied, ffmpeg also derives a compact\nrepresentative contact sheet and a short low-resolution motion sample from the\nexact ``preview_video_url`` recorded in the immutable discovery result.\n',
    'When ``--contact-sheets-only`` is supplied, FFmpeg derives compact JPEG contact sheets '
    'from the exact ``preview_video_url`` without creating motion-sample MP4 files. When '
    '``--include-motion-evidence`` is supplied, the short motion sample is also produced.\n',
    1,
)
start = text.index('def _materialize_motion_evidence(')
end = text.index('\n\ndef materialize(', start)
new_function = r'''def _materialize_motion_evidence(
    candidate,
    destination,
    frame_count,
    sample_seconds,
    video_input=None,
    include_motion_sample=True,
):
    video_url = _https_url(candidate.get("preview_video_url"), "preview_video_url")
    duration = _positive_float(candidate.get("duration_seconds"), "duration_seconds")
    fps = _positive_float(candidate.get("preview_video_fps") or 30.0, "preview_video_fps")
    timestamps = _representative_timestamps(duration, frame_count)
    frame_indices = sorted({max(0, int(round(timestamp * fps))) for timestamp in timestamps})
    if len(frame_indices) != frame_count:
        raise ValueError("representative frame timestamps did not map to unique frames")

    local_video = Path(video_input) if video_input is not None else None
    if local_video is not None:
        source_file = _file_evidence(local_video)
        ffmpeg_input = str(local_video)
        transport = "local_file"
    else:
        source_file = None
        ffmpeg_input = video_url
        transport = "direct_url"

    destination.mkdir(parents=True, exist_ok=True)
    select = "+".join(f"eq(n\\,{frame})" for frame in frame_indices)
    grid_columns = 3 if frame_count > 4 else 2
    grid_rows = (frame_count + grid_columns - 1) // grid_columns
    contact_sheet = destination / "contact-sheet.jpg"
    contact_filter = (
        f"select={select},"
        "setpts=N/FRAME_RATE/TB,"
        f"scale={DEFAULT_SAMPLE_WIDTH}:-2,"
        f"tile={grid_columns}x{grid_rows}:nb_frames={frame_count}:padding=4:margin=4"
    )
    _run_ffmpeg([
        "-i", ffmpeg_input, "-vf", contact_filter, "-frames:v", "1", "-q:v", "5",
        str(contact_sheet)
    ])

    result = {
        "source_url": video_url,
        "transport": transport,
        "source_duration_seconds": duration,
        "source_fps": fps,
        "representative_timestamps_seconds": timestamps,
        "contact_sheet": _file_evidence(contact_sheet),
    }
    if local_video is not None:
        result["source_input"] = source_file

    if include_motion_sample:
        sample_seconds = min(_positive_float(sample_seconds, "sample_seconds"), duration)
        sample_start = max(0.0, (duration - sample_seconds) / 2.0)
        motion_sample = destination / "motion-sample.mp4"
        _run_ffmpeg([
            "-ss", f"{sample_start:.3f}", "-i", ffmpeg_input,
            "-t", f"{sample_seconds:.3f}", "-vf", f"scale={DEFAULT_SAMPLE_WIDTH}:-2",
            "-r", "12", "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(motion_sample),
        ])
        result["motion_sample"] = {
            **_file_evidence(motion_sample),
            "start_seconds": round(sample_start, 3),
            "duration_seconds": round(sample_seconds, 3),
        }
    return result'''
text = text[:start] + new_function + text[end:]
text = text.replace(
    '    input_dir=None,\n):\n',
    '    input_dir=None,\n    contact_sheets_only=False,\n):\n',
    1,
)
text = text.replace(
    '                    video_input=local_video,\n                )\n',
    '                    video_input=local_video,\n                    include_motion_sample=not contact_sheets_only,\n                )\n',
    1,
)
text = text.replace(
    '        "motion_evidence_requested": bool(include_motion_evidence),\n',
    '        "motion_evidence_requested": bool(include_motion_evidence),\n'
    '        "contact_sheets_only": bool(contact_sheets_only),\n'
    '        "motion_sample_requested": bool(include_motion_evidence and not contact_sheets_only),\n',
    1,
)
text = text.replace(
    '    parser.add_argument(\n        "--include-motion-evidence",\n',
    '    parser.add_argument(\n'
    '        "--contact-sheets-only",\n'
    '        action="store_true",\n'
    '        help="Derive representative JPEG contact sheets without motion-sample MP4 files.",\n'
    '    )\n'
    '    parser.add_argument(\n        "--include-motion-evidence",\n',
    1,
)
text = text.replace(
    '    manifest = materialize(\n        args.discovery_result,\n        args.output_dir,\n        include_motion_evidence=args.include_motion_evidence,\n',
    '    motion_requested = bool(args.include_motion_evidence or args.contact_sheets_only)\n'
    '    manifest = materialize(\n        args.discovery_result,\n        args.output_dir,\n'
    '        include_motion_evidence=motion_requested,\n',
    1,
)
text = text.replace(
    '        input_dir=args.input_dir,\n    )\n',
    '        input_dir=args.input_dir,\n'
    '        contact_sheets_only=args.contact_sheets_only,\n'
    '    )\n',
    1,
)
text = text.replace(
    '    if args.include_motion_evidence and manifest["motion_evidence_count"] == 0:\n',
    '    if motion_requested and manifest["motion_evidence_count"] == 0:\n',
    1,
)
materializer.write_text(text, encoding='utf-8')

# Future discovery uses a smaller exact rendition for review transport while still
# requiring a separate production-suitable rendition.
discovery = Path('youtube-shorts-bot/media/pexels_discovery.py')
text = discovery.read_text(encoding='utf-8')
old = '''    renditions = renditions_from_video(video)\n    suitable = [item for item in renditions if rendition_is_production_suitable(item)]\n    if not suitable:\n        return None\n    suitable.sort(key=lambda item: (int(item["width"]) * int(item["height"]), float(item.get("fps") or 999), str(item.get("id") or "")))\n    preview_rendition = suitable[0]\n'''
new = '''    renditions = renditions_from_video(video)\n    suitable = [item for item in renditions if rendition_is_production_suitable(item)]\n    if not suitable:\n        return None\n    suitable.sort(key=lambda item: (int(item["width"]) * int(item["height"]), float(item.get("fps") or 999), str(item.get("id") or "")))\n\n    # Review transport only needs exact asset identity and enough pixels for a contact\n    # sheet. Prefer a small provider rendition while independently requiring at least\n    # one production-suitable rendition above.\n    review_renditions = [\n        item for item in renditions\n        if int(item.get("width") or 0) >= 360 and int(item.get("height") or 0) >= 360\n    ] or list(renditions)\n    review_renditions.sort(\n        key=lambda item: (\n            int(item.get("width") or 0) * int(item.get("height") or 0),\n            float(item.get("fps") or 999),\n            str(item.get("id") or ""),\n        )\n    )\n    preview_rendition = review_renditions[0]\n'''
if old not in text:
    raise SystemExit('pexels discovery rendition block drifted')
discovery.write_text(text.replace(old, new, 1), encoding='utf-8')

# Replace transport tests so the architecture is regression-protected.
test_path = Path('youtube-shorts-bot/tests/test_background_review_transport.py')
tests = r'''import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media.preview_review_materializer import (
    _https_url,
    _representative_timestamps,
    materialize,
)


class BackgroundReviewTransportContractTests(unittest.TestCase):
    def test_background_management_generates_private_review_artifact_without_approving(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        self.assertNotIn('PUBLIC_PRODUCTION_TOKEN', workflow)
        self.assertNotIn('verified_preview=true', workflow)
        self.assertIn('Materialize exact-source review contact sheets', workflow)
        self.assertIn('media.preview_review_materializer', workflow)
        self.assertIn('--contact-sheets-only', workflow)
        self.assertIn('actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02', workflow)
        self.assertIn('background-review-evidence-', workflow)
        self.assertIn('retention-days: 3', workflow)
        self.assertIn('Write immutable review evidence index', workflow)
        self.assertIn('content/background-sourcing/review-evidence/', workflow)
        self.assertIn('Ingest reviewed readiness manifest', workflow)

    def test_background_management_can_backfill_unindexed_discovery(self):
        workflow = Path('.github/workflows/background-management.yml').read_text(encoding='utf-8')
        self.assertIn('action=review', workflow)
        self.assertIn('newest discovery', workflow)
        self.assertIn('review_request_id', workflow)

    def test_materializer_builds_evenly_distributed_review_points(self):
        self.assertEqual(_representative_timestamps(60.0, 5), [10.0, 20.0, 30.0, 40.0, 50.0])

    def test_materializer_rejects_non_pexels_visual_transport(self):
        with self.assertRaises(ValueError):
            _https_url('https://example.com/video.mp4', 'preview_video_url')

    def test_image_failure_falls_through_to_exact_video_evidence(self):
        discovery = {
            'request_id': 'dr-test',
            'candidates': [{
                'provider_asset_id': '123',
                'source_page': 'https://www.pexels.com/video/example-123/',
                'preview_image_url': 'https://images.pexels.com/photos/123/pexels-photo-123.jpeg',
                'preview_video_url': 'https://videos.pexels.com/video-files/123/example.mp4',
                'duration_seconds': 60,
                'preview_video_fps': 30,
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'discovery.json'
            source.write_text(json.dumps(discovery), encoding='utf-8')
            motion = {
                'source_url': discovery['candidates'][0]['preview_video_url'],
                'contact_sheet': {'path': 'contact-sheet.jpg', 'bytes': 1, 'sha256': 'x'},
                'motion_sample': {'path': 'motion-sample.mp4', 'bytes': 1, 'sha256': 'y'},
            }
            with patch('media.preview_review_materializer._download', side_effect=RuntimeError('image blocked')):
                with patch('media.preview_review_materializer._materialize_motion_evidence', return_value=motion):
                    result = materialize(source, Path(tmp) / 'evidence', include_motion_evidence=True)
        self.assertEqual(result['evidence_count'], 1)
        self.assertEqual(result['image_failure_count'], 1)
        self.assertEqual(result['motion_evidence_count'], 1)

    def test_one_candidate_transport_failure_does_not_abort_remaining_candidates(self):
        discovery = {
            'request_id': 'dr-test',
            'candidates': [
                {'provider_asset_id': '123', 'source_page': 'https://www.pexels.com/video/example-123/', 'preview_image_url': 'https://images.pexels.com/photos/123/a.jpeg', 'preview_video_url': 'https://videos.pexels.com/video-files/123/a.mp4', 'duration_seconds': 60, 'preview_video_fps': 30},
                {'provider_asset_id': '456', 'source_page': 'https://www.pexels.com/video/example-456/', 'preview_image_url': 'https://images.pexels.com/photos/456/b.jpeg', 'preview_video_url': 'https://videos.pexels.com/video-files/456/b.mp4', 'duration_seconds': 60, 'preview_video_fps': 30},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'discovery.json'
            source.write_text(json.dumps(discovery), encoding='utf-8')
            def fake_download(url, destination, max_bytes):
                if '/123/' in url:
                    raise RuntimeError('candidate 123 blocked')
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b'x')
                return {'path': str(destination), 'bytes': 1, 'sha256': 'x'}
            with patch('media.preview_review_materializer._download', side_effect=fake_download):
                result = materialize(source, Path(tmp) / 'evidence', include_motion_evidence=False)
        self.assertEqual(result['evidence_count'], 1)
        self.assertEqual(result['failure_count'], 1)
        self.assertEqual(result['evidence'][0]['provider_asset_id'], '456')

    def test_staged_local_image_bypasses_blocked_python_network(self):
        discovery = {
            'request_id': 'dr-test',
            'candidates': [{
                'provider_asset_id': '123',
                'source_page': 'https://www.pexels.com/video/example-123/',
                'preview_image_url': 'https://images.pexels.com/photos/123/a.jpeg',
                'preview_video_url': 'https://videos.pexels.com/video-files/123/a.mp4',
                'duration_seconds': 60,
                'preview_video_fps': 30,
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'discovery.json'
            source.write_text(json.dumps(discovery), encoding='utf-8')
            staged = root / 'input' / '123' / 'preview.jpg'
            staged.parent.mkdir(parents=True)
            staged.write_bytes(b'exact-preview-pixels')
            with patch('media.preview_review_materializer._download', side_effect=RuntimeError('blocked')) as download:
                result = materialize(source, root / 'evidence', input_dir=root / 'input')
        download.assert_not_called()
        self.assertEqual(result['local_file_evidence_count'], 1)
        self.assertEqual(result['evidence'][0]['image']['transport'], 'local_file')

    def test_contact_sheets_only_skips_motion_sample(self):
        discovery = {
            'request_id': 'dr-test',
            'candidates': [{
                'provider_asset_id': '123',
                'source_page': 'https://www.pexels.com/video/example-123/',
                'preview_image_url': 'https://images.pexels.com/photos/123/a.jpeg',
                'preview_video_url': 'https://videos.pexels.com/video-files/123/a.mp4',
                'duration_seconds': 60,
                'preview_video_fps': 30,
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'discovery.json'
            source.write_text(json.dumps(discovery), encoding='utf-8')
            def fake_motion(candidate, destination, frame_count, sample_seconds, video_input=None, include_motion_sample=True):
                self.assertFalse(include_motion_sample)
                return {'source_url': candidate['preview_video_url'], 'transport': 'direct_url', 'contact_sheet': {'path': 'contact-sheet.jpg', 'bytes': 1, 'sha256': 'x'}}
            with patch('media.preview_review_materializer._download', side_effect=RuntimeError('image blocked')):
                with patch('media.preview_review_materializer._materialize_motion_evidence', side_effect=fake_motion):
                    result = materialize(source, Path(tmp) / 'evidence', include_motion_evidence=True, contact_sheets_only=True)
        self.assertTrue(result['contact_sheets_only'])
        self.assertFalse(result['motion_sample_requested'])
        self.assertEqual(result['motion_evidence_count'], 1)

    def test_shared_policy_keeps_editorial_ownership_in_chatgpt(self):
        policy = Path('youtube-shorts-bot/docs/background-media-strategy.md').read_text(encoding='utf-8')
        self.assertIn('private Background Management review-evidence artifact', policy)
        self.assertIn('review-evidence/<request_id>-run-<run_id>.json', policy)
        self.assertIn('contact-sheet.jpg', policy)
        self.assertIn('GitHub Actions must never set `verified_preview`', policy)
        self.assertIn('transport-only', policy)


if __name__ == '__main__':
    unittest.main()
'''
test_path.write_text(tests, encoding='utf-8')

# Add a regression test for the low-bandwidth review rendition.
discovery_tests = Path('youtube-shorts-bot/tests/test_pexels_discovery.py')
text = discovery_tests.read_text(encoding='utf-8')
if 'test_review_preview_prefers_small_exact_rendition' not in text:
    text += '''\n\ndef test_review_preview_prefers_small_exact_rendition():\n    video = _video(201, 90, width=3840, height=2160, file_width=3840, file_height=2160)\n    video["video_files"].insert(0, {\n        "id": 2011, "width": 640, "height": 360, "fps": 30,\n        "file_type": "video/mp4", "quality": "sd",\n        "link": "https://videos.pexels.com/video-files/201/review-640.mp4",\n    })\n    candidate = discovery._eligible_candidate(video, "city_motion", "city traffic")\n    assert candidate is not None\n    assert candidate["production_suitable_rendition_count"] == 1\n    assert candidate["preview_video_width"] == 640\n    assert candidate["preview_video_height"] == 360\n    assert candidate["preview_video_url"].endswith("review-640.mp4")\n'''
    discovery_tests.write_text(text, encoding='utf-8')

# Shared docs: GitHub provides transport; ChatGPT still approves.
strategy = Path('youtube-shorts-bot/docs/background-media-strategy.md')
text = strategy.read_text(encoding='utf-8')
lifecycle = r'''Daily and Ad-hoc share one readiness/replenishment path:

```text
audit -> REPLENISH -> immutable discovery request
      -> Background Management/Pexels API filters duration + rendition eligibility
      -> Background Management reads exact Pexels preview media
      -> FFmpeg generates small representative JPEG contact sheets
      -> private GitHub artifact + immutable review-evidence index
      -> ChatGPT/Work downloads that exact artifact through the GitHub connection
      -> ChatGPT inspects the JPEG pixels and assigns approval + semantic metadata
      -> immutable readiness manifest -> Background Management re-enriches/persists
      -> refresh main -> audit again -> PASS -> planning continues
```

Provider discovery is deliberately split from editorial review. `media.pexels_discovery` may use the GitHub-held `PEXELS_API_KEY` to fetch exact provider metadata and discard clips below the live atomic-duration minimum or without a production-suitable rendition. For review transport it records the smallest useful exact provider rendition, while production suitability remains independently required. Background Management may perform **transport-only** media work: read/download those exact URLs, derive JPEG contact sheets, upload a private artifact and persist an immutable artifact index. It must not set `verified_preview=true`, invent semantic tags/scores, approve/reject a source, or write reviewed assets directly to the registry. ChatGPT/Work remains the sole visual/editorial approval owner.

A discovery request is immutable under `content/background-sourcing/discovery-requests/`. Background Management writes the matching provider result under `content/background-sourcing/discovery-results/` and one or more immutable transport indexes under `content/background-sourcing/review-evidence/<request_id>-run-<run_id>.json`. Each index records the exact Background Management run and artifact identity, digest, evidence-manifest hash and provider IDs with contact sheets. Multiple run-scoped indexes allow safe evidence regeneration after artifact expiry without editing history.'''
start = text.index('Daily and Ad-hoc share one readiness/replenishment path:')
end = text.index('Readiness PASS requires', start)
text = text[:start] + lifecycle + '\n\n' + text[end:]
preview = r'''## Preview-review evidence

`verified_preview=true` means ChatGPT/Work reviewed **actual visual evidence for the exact Pexels source** before proposing it. GitHub transport success alone is never approval.

The preferred transport is the **private Background Management review-evidence artifact**. For each new discovery result, Background Management runs `media.preview_review_materializer --contact-sheets-only` against exact Pexels preview URLs and creates compact JPEG contact sheets. It uploads lightweight review evidence, not source video, as `background-review-evidence-<request_id>-<run_id>` with a short retention window, then commits `content/background-sourcing/review-evidence/<request_id>-run-<run_id>.json` containing exact workflow-run/artifact identity and evidence hashes.

Planner review order:

1. Read the immutable discovery result and newest matching run-scoped review-evidence index whose artifact is still available.
2. Through the authorized GitHub connection, list artifacts for the indexed `workflow_run_id`, require the indexed artifact ID/name/digest to match, and download that exact ZIP. GitHub connector delivery into ChatGPT/Work local storage is the canonical binary transfer bridge.
3. Extract the ZIP locally. Verify `evidence-manifest.json` against the index SHA-256 and confirm provider IDs/source URLs correspond to the immutable discovery result.
4. Inspect the actual `*/contact-sheet.jpg` pixels (and exact `*/preview.jpg` when useful). ChatGPT/Work alone decides approval, semantic tags, motion/readability judgment and scores.
5. Reject candidate-specific missing/unsuitable evidence and continue through reserves. Never convert transport success directly into `verified_preview=true`.

The workflow excludes provider IDs that are already active+verified in the registry from repeated artifact generation; this is transport optimization only. Future discovery uses a smaller exact provider rendition for contact-sheet generation while independently requiring a production-quality rendition for eventual production.

If an artifact is unavailable/expired, a new run-scoped artifact/index may be generated for the same immutable discovery result. Native exact-source provider inspection and ChatGPT-local exact download remain valid fallbacks, including `media.preview_review_materializer --input-dir` when another trustworthy transport stages exact bytes.

GitHub Actions may download/read exact provider media and derive contact sheets because that is **transport-only** processing. GitHub Actions must never set `verified_preview`, assign semantic metadata, approve/reject a source, create a readiness manifest, or otherwise perform ChatGPT-owned editorial judgment. Metadata, title, tags, duration, or artifact creation alone are not enough to approve a clip.

`EVIDENCE_ACCESS_BLOCKED` is valid only after available indexed private artifacts and every other trustworthy exact-source transport are unusable for the candidates still needed for readiness. A successful required Background Management evidence run with a missing/mismatched index or artifact is `REVIEW_EVIDENCE_TRANSPORT_FAILED`, an infrastructure/contract failure, not a creative rejection. If the matching evidence run is still legitimately pending beyond the shared bounded continuation window, use `DEFERRED_REPLENISHMENT`.

Background Management remains the hard technical admission boundary after ChatGPT review: it re-fetches official Pexels metadata/renditions and validates the reviewed readiness manifest before any asset becomes selectable.'''
start = text.index('## Preview-review evidence')
end = text.index('## New-production visual model', start)
strategy.write_text(text[:start] + preview + '\n\n' + text[end:], encoding='utf-8')

shared = r'''## Shared automatic background replenishment and continuation

`REPLENISH` is a recoverable planner state, not a terminal planner failure. Daily and Ad-hoc use this exact shared procedure before freezing final backgrounds or committing a ranked pool.

1. Consume the exact readiness total/category/duration deficits.
2. Inspect immutable discovery requests/results/readiness manifests, matching `content/background-sourcing/review-evidence/<request_id>-run-*.json` indexes, and Background Management runs. **Resume a compatible unfinished attempt instead of creating duplicates.**
3. If no compatible attempt exists, create exactly one immutable discovery request with the live schema and canonical `[media discovery]` convention.
4. Private Background Management owns deterministic provider discovery, exact-source **transport-only** review evidence generation and readiness persistence. It may read/download exact Pexels preview media, run FFmpeg to derive representative JPEG contact sheets, upload a private short-lived GitHub artifact, and commit an immutable run-scoped review-evidence index. It must never perform ChatGPT-owned approval, set `verified_preview`, assign semantic metadata/scores, or create the reviewed readiness manifest.
5. After triggering/finding the matching Background Management discovery/evidence run, poll/refresh for up to 10 minutes rather than returning merely because it is queued/in progress. Normal continuation requires the matching immutable discovery result and at least one matching run-scoped review-evidence index with an available artifact. Terminal workflow failure is infrastructure/authentication failure. A still-running required run at the bounded deadline is `DEFERRED_REPLENISHMENT`.
6. Review actual exact-source pixels. Prefer the newest usable indexed private Background Management artifact:
   - Read exact `workflow_run_id`, `artifact_id`, `artifact_name`, `artifact_digest`, and `evidence_manifest_sha256`; never guess a run/artifact.
   - Through the authorized GitHub connection, list the indexed run artifacts, verify identity/digest, download the exact ZIP and extract it locally. Connector-delivered artifact files are the canonical binary bridge and do not require local outbound internet.
   - Verify the extracted evidence-manifest hash and provider/source identity against the immutable discovery result.
   - Inspect actual `*/contact-sheet.jpg` pixels (and exact stills where useful). Artifact creation is transport evidence only; ChatGPT/Work remains the sole visual/editorial approval owner.
   - Reject candidate-specific missing/unsuitable evidence and continue remaining candidates/reserves.

   If an indexed artifact expired, regenerate a new run-scoped evidence artifact/index for the same immutable discovery result when possible. Native exact Pexels inspection, exact preview-image download, and exact preview-video staging remain fallbacks; `media.preview_review_materializer --input-dir` remains available for trustworthy staged bytes.

   `EVIDENCE_ACCESS_BLOCKED` is legal only after usable indexed private artifacts and all other trustworthy exact-source visual transports available to the run are unusable for the remaining candidates needed for readiness. A successful required Background Management evidence run with a missing/mismatched index/artifact is `REVIEW_EVIDENCE_TRANSPORT_FAILED`, not a creative/content failure.
7. Create exactly one immutable readiness manifest from visually approved candidates only. Never overwrite prior immutable state.
8. Commit the readiness manifest so Background Management performs canonical provider re-enrichment/persistence and reserve fallback.
9. Poll/refresh that required ingestion run for up to 10 minutes. Continue when the registry commit appears; terminal failure is infrastructure/authentication failure and a still-running job at the deadline is `DEFERRED_REPLENISHMENT`.
10. Refresh current `main`, apply drift policy, rerun `planner_contract` and `media_readiness`, and repeat replenishment if required. Candidate finalization begins only after `PASS`.

Do not bypass provider discovery, fabricate metadata, or move creative/editorial approval into GitHub Actions. Private GitHub Actions may perform deterministic provider/media **transport** work; ChatGPT/Work performs the visual decision.'''
replace_between(
    'docs/private/PLANNER_PROMPT.md',
    '## Shared automatic background replenishment and continuation',
    '## Shared precommit engine',
    shared,
)

profile_review = r'''Once a matching immutable discovery result exists, continue through visual review and readiness-manifest creation in the **same planner invocation**. Follow the shared artifact-first evidence contract in `docs/private/PLANNER_PROMPT.md` and `docs/background-media-strategy.md`:

1. Require a matching run-scoped `content/background-sourcing/review-evidence/<request_id>-run-*.json` produced by private Background Management. If the required evidence run is still legitimately building/uploading evidence, use the shared bounded continuation window rather than returning early.
2. Use the newest usable index's exact workflow-run and artifact ID/name/digest to retrieve `background-review-evidence-<request_id>-<run_id>` through the GitHub connection. Download/extract it locally, verify `evidence-manifest.json` against the indexed SHA-256 and immutable discovery result, then inspect the actual `*/contact-sheet.jpg` pixels. GitHub generated the frames but did **not** approve them; ChatGPT/Work owns approval and semantic metadata.
3. If an artifact is expired/unavailable or individual evidence is insufficient, regenerate a run-scoped evidence artifact when possible and exhaust native exact-source Pexels inspection plus exact local preview-image/video transfer, including `media.preview_review_materializer --input-dir` where applicable. Reject inaccessible candidates individually and continue reserves.
4. `EVIDENCE_ACCESS_BLOCKED` is legal only after usable private indexed artifacts plus all other trustworthy exact-source visual channels are unavailable for the remaining candidates needed for readiness. A successful required Background Management evidence run with a missing/mismatched artifact/index is `REVIEW_EVIDENCE_TRANSPORT_FAILED`, not a creative failure.
5. If too few candidates survive, continue the next immutable discovery attempt under the same deficits; never weaken `verified_preview`.

Do not bypass discovery results by guessing provider metadata. Private GitHub Actions may perform exact-source transport/download/FFmpeg contact-sheet generation, but must never set `verified_preview`, approve/reject candidates, assign semantic metadata, or author the readiness manifest. No separate manual seed/populate step is required.'''
replace_between(
    'youtube-shorts-bot/planning/ADHOC_PLANNER_PROMPT.md',
    'Once a matching immutable discovery result exists',
    '## Sequence background contract',
    profile_review,
)
replace_between(
    'youtube-shorts-bot/planning/DAILY_PLANNER_PROMPT.md',
    'Once a matching immutable discovery result exists',
    '## Sequence background contract',
    profile_review,
)

print('Background review artifact bridge patch applied.')
