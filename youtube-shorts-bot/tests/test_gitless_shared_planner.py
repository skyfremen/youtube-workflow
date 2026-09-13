import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from media.media_readiness import MIN_SELECTABLE_ASSETS, REQUIRED_CATEGORY_MINIMUMS
from validation.validate_content import SCHEMA_VERSION


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent
MANIFEST_PATH = BOT_ROOT / "planning" / "PLANNER_MATERIALIZATION.json"
SOURCE_ADHOC_POOL = (
    BOT_ROOT
    / "content"
    / "planning-pools"
    / "adhoc"
    / "ap-20260913-manual-110400-a01.json"
)
RULES_SHA = "1" * 40


def _run(root, *args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "youtube-shorts-bot")
    return subprocess.run(
        [sys.executable, *args],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _upgrade_request_to_v7(request):
    request = copy.deepcopy(request)
    request["schema_version"] = SCHEMA_VERSION
    request["visual"] = {
        "background_mode": "concatenated_fit_to_short",
        "background_primary_sequence": [
            {"background_id": f"satisfying-{index:03d}", "segment_start_seconds": 0.0, "segment_duration_seconds": 80.0}
            for index in (1, 2, 3)
        ],
        "background_backup_sequence": [
            {"background_id": f"satisfying-{index:03d}", "segment_start_seconds": 0.0, "segment_duration_seconds": 80.0}
            for index in (4, 5, 6)
        ],
    }
    return request


def _upgrade_adhoc_pool_to_v7(pool):
    pool = copy.deepcopy(pool)
    pool["planning_execution"]["rules_source_sha"] = RULES_SHA
    for item in pool["ranked_candidates"]:
        item["request"] = _upgrade_request_to_v7(item["request"])
    return pool


def _ready_asset(asset_id, category, counter):
    return {
        "id": asset_id,
        "type": "video",
        "title": f"Gitless atomic test asset {counter}",
        "source": "Pexels",
        "source_page": f"https://www.pexels.com/video/gitless-{100000 + counter}/",
        "direct_url": f"https://videos.pexels.com/gitless-{counter:03d}.mp4",
        "creator": None,
        "license": "Pexels License",
        "commercial_use": True,
        "attribution_required": False,
        "verified": True,
        "last_verified_at": "2026-09-13T00:00:00+08:00",
        "status": "active",
        "orientation": "vertical",
        "visual_tags": [category, "continuous", "process"],
        "motion_type": "continuous_process",
        "motion_intensity": "high",
        "visual_satisfaction_score": 100,
        "loopability_score": 100,
        "caption_readability_score": 100,
        "has_embedded_text": False,
        "has_watermark": False,
        "retention_category": category,
        "duration_seconds": 300.0,
        "renditions": [
            {
                "id": f"test-r-{counter:03d}",
                "width": 1080,
                "height": 1920,
                "fps": 30.0,
                "file_type": "video/mp4",
                "direct_url": f"https://videos.pexels.com/gitless-{counter:03d}.mp4",
            }
        ],
    }


def _ready_registry_for_pool(pool):
    requested_ids = []
    for item in pool["ranked_candidates"]:
        visual = item["request"]["visual"]
        for slot in ("primary", "backup"):
            for segment in visual[f"background_{slot}_sequence"]:
                asset_id = segment["background_id"]
                if asset_id not in requested_ids:
                    requested_ids.append(asset_id)

    category_plan = []
    for category, minimum in REQUIRED_CATEGORY_MINIMUMS.items():
        category_plan.extend([category] * minimum)
    while len(category_plan) < MIN_SELECTABLE_ASSETS:
        category_plan.append("satisfying_process")

    asset_ids = list(requested_ids)
    counter = 0
    while len(asset_ids) < MIN_SELECTABLE_ASSETS:
        counter += 1
        synthetic = f"satisfying-{500 + counter:03d}"
        if synthetic not in asset_ids:
            asset_ids.append(synthetic)

    assets = [
        _ready_asset(asset_id, category_plan[index], index + 1)
        for index, asset_id in enumerate(asset_ids[:MIN_SELECTABLE_ASSETS])
    ]
    return {"schema_version": 3, "assets": assets}


def _daily_pool_from_adhoc(adhoc_pool):
    template = copy.deepcopy(adhoc_pool["ranked_candidates"][0]["request"])
    plan_date = "2099-01-01"
    slots = [f"2098-12-31T{16 + hour:02d}:00:00Z" for hour in range(8)]
    slots += [f"2099-01-01T{hour:02d}:00:00Z" for hour in range(16)]
    ranked = []
    for index in range(1, 37):
        request = copy.deepcopy(template)
        request["content_id"] = f"wd-20990101T000000-daily-c{index:05d}"
        request["publication"] = {
            "mode": "scheduled",
            "timezone": "Asia/Singapore",
            "publish_at": None,
        }
        request["planning"]["plan_date"] = plan_date
        ranked.append(
            {
                "rank": index,
                "candidate_id": f"daily-c{index:02d}",
                "request": request,
            }
        )
    return {
        "schema_version": 1,
        "pool_type": "daily",
        "pool_id": "dp-20990101-a01",
        "plan_date": plan_date,
        "planning_mode": "normal_next_day",
        "target_count": 24,
        "publication_slots": slots,
        "planning_execution": {
            "editorial_selection_owner": "chatgpt",
            "planning_method": "chatgpt_ranked_pool",
            "rules_source_sha": RULES_SHA,
            "ranked_candidate_ids": [f"daily-c{index:02d}" for index in range(1, 37)],
        },
        "ranked_candidates": ranked,
    }


class GitlessSharedPlannerTests(unittest.TestCase):
    def test_manifest_materialization_runs_both_profiles_without_repository_metadata(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            required = (
                manifest["shared_required_python_files"]
                + manifest["shared_required_data_files"]
            )
            for relative in required:
                source = REPO_ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)

            self.assertFalse((root / ".git").exists())
            self.assertFalse(
                (root / "youtube-shorts-bot" / "planning" / "ranked_promotion.py").exists()
            )
            self.assertFalse(
                (root / "youtube-shorts-bot" / "publishing" / "upload.py").exists()
            )
            self.assertFalse(
                (root / "youtube-shorts-bot" / "planning" / "daily_precommit.py").exists()
            )
            self.assertFalse(
                (root / "youtube-shorts-bot" / "planning" / "adhoc_precommit.py").exists()
            )

            contract = _run(root, "-m", "planning.planner_contract")
            self.assertEqual(contract.returncode, 0, contract.stderr or contract.stdout)
            contract_json = json.loads(contract.stdout)
            self.assertEqual(
                contract_json["profiles"]["daily"]["shared_contract_fingerprint"],
                contract_json["profiles"]["adhoc"]["shared_contract_fingerprint"],
            )
            self.assertEqual(contract_json["request_schema_version"], SCHEMA_VERSION)

            readiness = _run(
                root,
                "-m",
                "media.media_readiness",
                "audit",
                "--allow-not-ready",
            )
            self.assertEqual(readiness.returncode, 0, readiness.stderr or readiness.stdout)
            self.assertEqual(json.loads(readiness.stdout)["status"], "REPLENISH")

            adhoc_pool = _upgrade_adhoc_pool_to_v7(
                json.loads(SOURCE_ADHOC_POOL.read_text(encoding="utf-8"))
            )
            registry_path = root / "youtube-shorts-bot" / "media-library" / "backgrounds.json"
            registry_path.write_text(
                json.dumps(_ready_registry_for_pool(adhoc_pool), indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )

            ready = _run(
                root,
                "-m",
                "media.media_readiness",
                "audit",
                "--allow-not-ready",
            )
            self.assertEqual(ready.returncode, 0, ready.stderr or ready.stdout)
            self.assertEqual(json.loads(ready.stdout)["status"], "PASS")

            adhoc_path = root / "adhoc-pool.json"
            adhoc_path.write_text(
                json.dumps(adhoc_pool, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            adhoc = _run(
                root,
                "-m",
                "planning.planner_precommit",
                "--profile",
                "adhoc",
                "--pool",
                str(adhoc_path),
                "--rules-source-sha",
                RULES_SHA,
            )
            self.assertEqual(adhoc.returncode, 0, adhoc.stderr or adhoc.stdout)
            self.assertEqual(json.loads(adhoc.stdout)["valid_candidates"], 5)

            daily_pool = _daily_pool_from_adhoc(adhoc_pool)
            daily_path = root / "daily-pool.json"
            daily_path.write_text(
                json.dumps(daily_pool, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            daily = _run(
                root,
                "-m",
                "planning.planner_precommit",
                "--profile",
                "daily",
                "--pool",
                str(daily_path),
                "--rules-source-sha",
                RULES_SHA,
            )
            self.assertEqual(daily.returncode, 0, daily.stderr or daily.stdout)
            self.assertEqual(json.loads(daily.stdout)["valid_candidates"], 36)


if __name__ == "__main__":
    unittest.main()
