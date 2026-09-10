import copy
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from media.validate_media_library import load_registry, validate_request_backgrounds
from planning.planning_config import EDITORIAL_WEIGHTS, TITLE_WEIGHTS
from production.batch import order_requests, validate_explicit_batch, write_batch_files
from publishing.publish import scheduled_slot_guard
from publishing.upload import build_upload_body
from rendering import render
from validation.validate_content import validate_request_data


BASE = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE.parent
DAILY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "daily-production.yml"
DRY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "dry-run.yml"

FIXTURE_DATE = "2099-09-10"
FIXTURE_NOW = datetime(2099, 9, 9, 0, 0, tzinfo=timezone.utc)
FIXTURE_START_UTC = datetime(2099, 9, 9, 16, 0, tzinfo=timezone.utc)


def _title_candidate(title, style, score):
    return {
        "title": title,
        "style": style,
        "truthful": True,
        "score": score,
        "score_components": {key: score for key in TITLE_WEIGHTS},
    }


def synthetic_request(index):
    hour = index
    content_id = f"wd-20990910T{hour:02}0000-dry-run-d{index:05d}"
    title = f"Story {index + 1:02}: The Backup Exposed What Really Happened #Shorts"
    publish_at = (FIXTURE_START_UTC + timedelta(hours=index)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": 3,
        "content_id": content_id,
        "channel": {"name": "Wacky Dramas", "handle": "@WACKYDRAMAS"},
        "story": {
            "category": "WORKPLACE",
            "story_type": "BACKFIRE",
            "hook": "The Backup He Forgot About",
            "script": (
                f"My boss told everyone story {index + 1} had no proof. "
                "I opened the archived workspace and found the timestamped backup."
            ),
            "card_emojis": ["💼", "🗂️", "😳", "💾", "🔥"],
        },
        "narration": {"engine": "kokoro", "voice": "af_heart", "speed": 1.75},
        "visual": {
            "background_primary_id": "satisfying-001",
            "background_backup_id": "satisfying-002",
        },
        "youtube": {
            "title": title,
            "description": (
                "The archived timestamp changed the whole argument. "
                "Would you have confronted the person who denied it?"
            ),
            "hashtags": [
                "#Shorts",
                "#WackyDramas",
                "#WorkplaceDrama",
                "#Storytime",
            ],
            "tags": [
                "wacky dramas",
                "workplace drama",
                "boss story",
                "office conflict",
                "evidence backfire",
                "storytime",
            ],
            "category_id": "24",
            "made_for_kids": False,
        },
        "publication": {
            "mode": "scheduled",
            "timezone": "Asia/Singapore",
            "publish_at": publish_at,
        },
        "planning": {
            "plan_date": FIXTURE_DATE,
            "editorial_score": 88.0,
            "editorial_components": {key: 88 for key in EDITORIAL_WEIGHTS},
            "analytics_score": None,
            "analytics_weight": 0.0,
            "final_score": 87.5,
            "title_candidates": [
                _title_candidate(title, "HIDDEN_REVELATION", 91),
                _title_candidate(
                    f"Story {index + 1:02}: I Checked the Archive and Found the Proof #Shorts",
                    "DISCOVERY",
                    86,
                ),
                _title_candidate(
                    f"Story {index + 1:02}: It Looked Normal Until the Timestamp Appeared #Shorts",
                    "NORMAL_TO_ABNORMAL",
                    84,
                ),
                _title_candidate(
                    f"Story {index + 1:02}: I Kept the Archive and the Story Changed #Shorts",
                    "DECISION_CONSEQUENCE",
                    83,
                ),
                _title_candidate(
                    f"Story {index + 1:02}: Hours Before the Audit, I Found the Backup #Shorts",
                    "COUNTDOWN",
                    82,
                ),
            ],
            "selected_title_score": 91.0,
            "hook_score": 90.0,
            "selection_class": "exploit" if index < 19 else "explore",
            "selection_reason": (
                "Strong contradiction, proof-driven escalation and clear reversal."
            ),
            "similarity": {"max_recent_similarity": 0.21},
            "attributes": {
                "subtype": "EVIDENCE_BACKFIRE",
                "conflict": "HIDDEN_FILE",
                "primary_emotion": "INJUSTICE",
                "protagonist_role": "EMPLOYEE",
                "antagonist_role": "BOSS",
                "opening_style": "CONTRADICTION",
                "title_style": "HIDDEN_REVELATION",
                "ending_style": "REVERSAL",
            },
            "target_duration_seconds": 151,
        },
    }


def build_synthetic_batch(root):
    requests_dir = root / "content" / "requests"
    planning_dir = root / "content" / "planning"
    requests_dir.mkdir(parents=True)
    planning_dir.mkdir(parents=True)

    requests = []
    content_ids = []
    payloads = []
    for index in range(24):
        payload = synthetic_request(index)
        path = requests_dir / f"{payload['content_id']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        requests.append(str(path))
        content_ids.append(payload["content_id"])
        payloads.append(payload)

    planning_path = planning_dir / f"{FIXTURE_DATE}.json"
    planning_path.write_text(
        json.dumps(
            {
                "plan_date": FIXTURE_DATE,
                "final_selected": 24,
                "content_ids": content_ids,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return requests, str(planning_path), payloads


def validate_production_shaped_batch(root):
    requests, planning_path, payloads = build_synthetic_batch(root)
    batch = validate_explicit_batch(requests, [planning_path])
    ordered = order_requests(batch.requests)
    if len(ordered) != 24 or len(set(ordered)) != 24:
        raise AssertionError("Synthetic production batch did not resolve to exactly 24 unique requests")

    request_output = root / "batch-requests.txt"
    sourcing_output = root / "background-sourcing-manifests.txt"
    written = write_batch_files(
        batch,
        request_output=request_output,
        sourcing_output=sourcing_output,
    )
    if tuple(ordered) != tuple(written):
        raise AssertionError("Shared batch writer changed deterministic request ordering")
    if request_output.read_text(encoding="utf-8").splitlines() != list(ordered):
        raise AssertionError("Shared batch request output differs from resolved order")
    if sourcing_output.read_text(encoding="utf-8"):
        raise AssertionError("Synthetic fixture unexpectedly requires external background sourcing")

    registry = load_registry()
    stage_counts = {
        "schema": 0,
        "background": 0,
        "schedule_guard": 0,
        "upload_contract": 0,
        "upload_boundary_simulated": 0,
        "publication_boundary_simulated": 0,
        "receipt_boundary_simulated": 0,
        "analytics_boundary_simulated": 0,
    }

    payload_by_path = {path: payload for path, payload in zip(requests, payloads)}
    simulated_receipts = []
    for path in ordered:
        payload = payload_by_path[path]
        errors = validate_request_data(payload, request_path=path)
        if errors:
            raise AssertionError(f"Production request validation failed for {payload['content_id']}: {errors}")
        stage_counts["schema"] += 1

        validate_request_backgrounds(payload, registry)
        stage_counts["background"] += 1

        guard = scheduled_slot_guard(payload, now_utc=FIXTURE_NOW)
        if guard["skip"]:
            raise AssertionError(f"Synthetic future publication slot was incorrectly skipped: {guard}")
        stage_counts["schedule_guard"] += 1

        body = build_upload_body(payload, now_utc=FIXTURE_NOW)
        if body["status"]["privacyStatus"] != "private":
            raise AssertionError("Scheduled upload contract is no longer private-before-publish")
        if body["status"]["publishAt"] != payload["publication"]["publish_at"]:
            raise AssertionError("Scheduled upload contract changed immutable publish_at")
        stage_counts["upload_contract"] += 1

        # Explicit safe boundaries: production network/Git/receipt mutation is not invoked.
        fake_video_id = f"dry{payload['content_id'][-8:]}"[-11:]
        simulated_upload = {
            "content_id": payload["content_id"],
            "youtube_video_id": fake_video_id,
            "simulated": True,
        }
        stage_counts["upload_boundary_simulated"] += 1

        simulated_publication = {
            **simulated_upload,
            "publication_verified": True,
            "publish_at": payload["publication"]["publish_at"],
        }
        stage_counts["publication_boundary_simulated"] += 1

        simulated_receipts.append(
            {
                "schema_version": 3,
                **simulated_publication,
                "receipt_simulated": True,
            }
        )
        stage_counts["receipt_boundary_simulated"] += 1
        stage_counts["analytics_boundary_simulated"] += 1

    if any(value != 24 for value in stage_counts.values()):
        raise AssertionError(f"Not all 24 requests traversed the safe production sequence: {stage_counts}")
    if len(simulated_receipts) != 24:
        raise AssertionError("Boundary simulation did not produce one result per request")

    return ordered[0], stage_counts


def verify_failure_isolation_fixture(root):
    good = [synthetic_request(index) for index in range(24)]
    bad = copy.deepcopy(good[12])
    bad.pop("youtube")
    bad_path = root / f"{bad['content_id']}.json"
    bad_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    bad_errors = validate_request_data(bad, request_path=bad_path)
    if not bad_errors:
        raise AssertionError("Malformed per-video request was not rejected")
    for index, payload in enumerate(good):
        if index == 12:
            continue
        path = root / f"{payload['content_id']}.json"
        if validate_request_data(payload, request_path=path):
            raise AssertionError("A malformed synthetic neighbor contaminated an unrelated valid request")


def render_smoke(request_path, root):
    smoke_dir = root / "render-smoke"
    smoke_dir.mkdir()
    captions = smoke_dir / "captions.ass"
    text = "Dry run verifies the production caption and render verifier path."
    events = render.caption_events(
        text,
        [(text, 24000)],
        1.0,
        start_offset=0.10,
    )
    captions.write_text(render.build_ass_header() + "\n".join(events) + "\n", encoding="utf-8")

    output = smoke_dir / "short.mp4"
    cwd = os.getcwd()
    try:
        os.chdir(smoke_dir)
        duration, stderr = render.run_capture(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "info",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=720x1280:rate=30:duration=1.40",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=24000:duration=1.40",
                "-filter_complex",
                f"[0:v]subtitles='captions.ass',{render.BLACKDETECT_FILTER}[v]",
                "-map",
                "[v]",
                "-map",
                "1:a:0",
                "-t",
                "1.40",
                "-c:v",
                "libx264",
                "-preset",
                render.X264_PRESET,
                "-crf",
                str(render.X264_CRF),
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-movflags",
                "+faststart",
                "short.mp4",
            ]
        )
    finally:
        os.chdir(cwd)

    if not output.exists() or output.stat().st_size < 100000:
        raise AssertionError("Representative render smoke output is missing or too small")
    black_durations = [
        float(value)
        for value in re.findall(r"black_duration:([0-9]+(?:\.[0-9]+)?)", stderr)
    ]
    black_max = max(black_durations, default=0.0)
    if black_max >= render.BLACKDETECT_MAX_ALLOWED_SECONDS:
        raise AssertionError(f"Representative smoke render unexpectedly contains black video: {black_max}")

    (smoke_dir / "render-metadata.json").write_text(
        json.dumps(
            {
                "content_id": Path(request_path).stem,
                "video_seconds": 1.40,
                "inline_blackdetect_passed": True,
                "inline_blackdetect_max_duration_seconds": black_max,
                "dry_run_ffmpeg_seconds": duration,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(BASE),
            "STORY_OUTPUT_DIR": str(smoke_dir),
            "STORY_TEST_MODE": "true",
            "STORY_RENDER_MAX_SECONDS": "5",
            "VIDEO_WIDTH": "720",
            "VIDEO_HEIGHT": "1280",
            "VIDEO_FPS": "30",
        }
    )
    subprocess.run(
        [
            os.sys.executable,
            str(BASE / "rendering" / "verify_render.py"),
            "--request",
            request_path,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )
    verified = json.loads((smoke_dir / "render-metadata.json").read_text(encoding="utf-8"))
    if verified.get("render_verified") is not True:
        raise AssertionError("Canonical render verifier did not approve representative smoke output")
    return duration


def verify_workflow_drift_contract():
    daily = DAILY_WORKFLOW.read_text(encoding="utf-8")
    dry = DRY_WORKFLOW.read_text(encoding="utf-8")
    shared = "python youtube-shorts-bot/production/batch.py"
    if shared not in daily:
        raise AssertionError("Daily Production no longer invokes shared production batch orchestration")
    if "python youtube-shorts-bot/production/dry_run.py" not in dry:
        raise AssertionError("Dry Run no longer executes the production-equivalence harness")

    forbidden_dry = (
        "publishing/publish.py --stage upload",
        "publishing/verify_publication.py --request",
        "publishing/finalize_receipt.py --request",
        "media/pexels_registry.py ingest-manifest",
        "git push origin",
    )
    found = [token for token in forbidden_dry if token in dry]
    if found:
        raise AssertionError(f"Dry Run contains forbidden production side-effect path(s): {found}")


def main():
    verify_workflow_drift_contract()
    with tempfile.TemporaryDirectory(prefix="wacky-dramas-dry-run-") as temp:
        root = Path(temp)
        first_request, stage_counts = validate_production_shaped_batch(root)
        verify_failure_isolation_fixture(root)
        render_seconds = render_smoke(first_request, root)

    print(
        "Production-equivalence dry run passed: "
        "24 production-shaped requests used shared batch orchestration, production schema/media/"
        "schedule/upload-body logic, explicit safe side-effect boundaries, and one canonical "
        f"FFmpeg+verify_render smoke ({render_seconds:.3f}s encode)."
    )
    print("Stage counts:", json.dumps(stage_counts, sort_keys=True))


if __name__ == "__main__":
    main()
