import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

BOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOT))

from recovery.reconciliation_index import IndexConflict, bootstrap

CID = "wd-20990101T000000-index-a1b2c3"
VIDEO = "AbCdEfGh123"
CHANNEL = "UC_TEST"
IDENTITY = {
    "content_id": CID,
    "request_path": f"youtube-shorts-bot/content/requests/{CID}.json",
    "request_blob_sha": "a" * 40,
    "source_commit_sha": "b" * 40,
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def upload_record(video_id=VIDEO):
    return {
        "schema_version": 1,
        "record_type": "upload",
        **IDENTITY,
        "youtube_video_id": video_id,
        "expected_channel_id": CHANNEL,
    }


def receipt(video_id=VIDEO):
    return {
        "schema_version": 4,
        **IDENTITY,
        "youtube_video_id": video_id,
        "youtube_channel_id": CHANNEL,
        "verification_state": "verified_scheduled",
        "verification": {"passed": True},
    }


class ReconciliationIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "content" / "recovery").mkdir(parents=True)
        (self.root / "content" / "results").mkdir(parents=True)

    def seed_matching_evidence(self):
        write_json(
            self.root / "content" / "recovery" / CID / "upload.json",
            upload_record(),
        )
        write_json(
            self.root / "content" / "results" / f"{CID}.json",
            receipt(),
        )

    def test_bootstrap_is_repeatable_and_idempotent(self):
        self.seed_matching_evidence()
        first = bootstrap(
            self.root,
            write=True,
            cutover_source_commit_sha="c" * 40,
        )
        second = bootstrap(
            self.root,
            write=True,
            cutover_source_commit_sha="d" * 40,
        )
        self.assertEqual(first["mapping_count"], 1)
        self.assertEqual(first["created"], 1)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["reused"], 1)
        self.assertTrue(second["bootstrap_present"])
        mapping = json.loads(
            (self.root / "content" / "recovery" / "index" / f"{CID}.json").read_text()
        )
        self.assertEqual(mapping["youtube_video_id"], VIDEO)

    def test_upload_and_receipt_conflict_fails_closed(self):
        self.seed_matching_evidence()
        write_json(
            self.root / "content" / "results" / f"{CID}.json",
            receipt("ZyXwVuTsR10"),
        )
        with self.assertRaisesRegex(IndexConflict, "conflicting mapping"):
            bootstrap(self.root)

    def test_existing_index_conflict_is_never_overwritten(self):
        self.seed_matching_evidence()
        index = self.root / "content" / "recovery" / "index"
        write_json(
            index / f"{CID}.json",
            {
                **upload_record("ZyXwVuTsR10"),
                "record_type": "mapping",
            },
        )
        with self.assertRaisesRegex(IndexConflict, "existing index mapping conflicts"):
            bootstrap(
                self.root,
                write=True,
                cutover_source_commit_sha="c" * 40,
            )

    def test_verified_receipt_can_bootstrap_missing_upload_record(self):
        write_json(
            self.root / "content" / "results" / f"{CID}.json",
            receipt(),
        )
        report = bootstrap(
            self.root,
            write=True,
            cutover_source_commit_sha="c" * 40,
        )
        self.assertEqual(report["mapping_count"], 1)
        self.assertEqual(report["upload_record_count"], 0)
        self.assertEqual(report["verified_receipt_count"], 1)

    def test_repository_cutover_marker_is_complete_and_has_no_stale_mapping(self):
        report = bootstrap(BOT, write=False)
        self.assertEqual(report["mapping_count"], 0)
        self.assertEqual(report["conflicts"], 0)
        self.assertEqual(report["created"], 0)
        self.assertEqual(report["reused"], 0)
        self.assertTrue(report["bootstrap_present"])
        self.assertFalse(report["youtube_api_required"])

        marker_path = BOT / "content" / "recovery" / "index" / "bootstrap.json"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        self.assertEqual(marker["schema_version"], 1)
        self.assertEqual(marker["status"], "complete")
        self.assertEqual(marker["conflicts"], 0)
        self.assertEqual(marker["historical_mapping_count"], 0)
        self.assertEqual(marker["upload_record_count"], 0)
        self.assertEqual(marker["verified_receipt_count"], 0)
        self.assertEqual(marker["source"], "trusted_private_evidence")
        self.assertFalse(marker["youtube_api_required"])
        self.assertRegex(marker["cutover_source_commit_sha"], re.compile(r"^[0-9a-f]{40}$"))


if __name__ == "__main__":
    unittest.main()
