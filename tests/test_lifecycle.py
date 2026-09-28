import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline
from lifecycle import audit_lifecycle


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def blob(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


class LifecycleAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for path in (
            "content/requests",
            "content/executions",
            "content/executions/evidence",
            "content/results",
            "data",
        ):
            (self.root / path).mkdir(parents=True, exist_ok=True)
        self.history = []

    def tearDown(self):
        self.temp.cleanup()

    def add_request(self, digit, *, request_digit=None, duplicate_path=None):
        cid = "wd-" + digit * 24
        rid = "rq-" + (request_digit or digit) * 24
        item = {
            "content_id": cid,
            "publication": {"publish_at": f"2030-01-0{int(digit)}T00:00:00Z"},
        }
        request = {"request_version": 2, "request_id": rid, "items": [item]}
        raw = encoded(request)
        path = self.root / "content/requests" / (duplicate_path or f"{rid}.json")
        path.write_bytes(raw)
        return cid, rid, item, raw

    def add_execution(self, cid, rid, item, request_raw, *, execution_digit=None):
        digit = execution_digit or cid[3]
        eid = "ex-" + digit * 24
        execution = {
            "execution_version": 2,
            "execution_id": eid,
            "request_id": rid,
            "content_id": cid,
            "request_path": f"content/requests/{rid}.json",
            "request_source_sha": digit * 40,
            "request_blob_sha": blob(request_raw),
            "item_blob_sha": blob(encoded(item)),
            "state": "prepared",
        }
        (self.root / "content/executions" / f"{eid}.json").write_bytes(encoded(execution))
        return eid, execution

    def add_upload(self, execution, video_id, *, version=2):
        cid = execution["content_id"]
        directory = self.root / "content/executions/evidence" / cid
        directory.mkdir(parents=True, exist_ok=True)
        if version == 2:
            identity = {
                key: execution[key]
                for key in (
                    "execution_id",
                    "content_id",
                    "request_id",
                    "request_path",
                    "request_source_sha",
                    "request_blob_sha",
                    "item_blob_sha",
                )
            }
        else:
            identity = {
                "content_id": cid,
                "request_path": f"content/requests/{cid}.json",
                "request_blob_sha": execution["item_blob_sha"],
                "source_commit_sha": execution["request_source_sha"],
            }
        upload = {
            "evidence_version": version,
            "record_type": "upload",
            **identity,
            "youtube_video_id": video_id,
        }
        (directory / "upload.json").write_bytes(encoded(upload))

    def add_result(self, cid, eid, publish_at, video_id):
        result = {
            "result_version": 2,
            "content_id": cid,
            "execution_id": eid,
            "status": "scheduled",
            "youtube_video_id": video_id,
            "visibility": "private",
            "verified": True,
            "publish_at": publish_at,
        }
        (self.root / "content/results" / f"{cid}.json").write_bytes(encoded(result))
        self.history.append({"content_id": cid, "publish_at": publish_at})

    def build_matrix(self):
        expected = {}
        for digit in "12345":
            cid, rid, item, raw = self.add_request(digit)
            expected[digit] = cid
            if digit == "1":
                continue
            eid, execution = self.add_execution(cid, rid, item, raw)
            if digit == "2":
                continue
            video = f"video00000{digit}"
            self.add_upload(execution, video, version=1 if digit == "5" else 2)
            if digit == "3":
                continue
            self.add_result(cid, eid, item["publication"]["publish_at"], video)

        duplicate, _rid, _item, _raw = self.add_request("6")
        self.add_request("6", request_digit="a", duplicate_path="rq-" + "a" * 24 + ".json")
        expected["6"] = duplicate

        malformed, rid, item, raw = self.add_request("7")
        _eid, execution = self.add_execution(malformed, rid, item, raw)
        directory = self.root / "content/executions/evidence" / malformed
        directory.mkdir(parents=True)
        (directory / "upload.json").write_text("{", encoding="utf-8")
        expected["7"] = malformed

        broken, rid, item, raw = self.add_request("8")
        eid, execution = self.add_execution(broken, rid, item, raw)
        self.add_upload(execution, "video000008")
        self.add_result(broken, eid, item["publication"]["publish_at"], "other000008")
        expected["8"] = broken
        (self.root / "data/history.json").write_bytes(encoded(self.history))
        return expected

    def snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.root.rglob("*")
            if path.is_file()
        }

    def test_classifies_matrix_deterministically_without_writes(self):
        ids = self.build_matrix()
        before = self.snapshot()

        first = audit_lifecycle(self.root)
        second = audit_lifecycle(self.root)

        self.assertEqual(first, second)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(1, first["audit_version"])
        self.assertEqual(
            {
                "request_only": 1,
                "execution_without_evidence": 1,
                "uploaded_without_result": 1,
                "complete": 1,
                "legacy_evidence_alias": 1,
                "invalid_cross_repository_relationship": 3,
            },
            first["counts"],
        )
        self.assertEqual(sorted(record["content_id"] for record in first["items"]), [record["content_id"] for record in first["items"]])
        status = {record["content_id"]: record["status"] for record in first["items"]}
        self.assertEqual("request_only", status[ids["1"]])
        self.assertEqual("execution_without_evidence", status[ids["2"]])
        self.assertEqual("uploaded_without_result", status[ids["3"]])
        self.assertEqual("complete", status[ids["4"]])
        self.assertEqual("legacy_evidence_alias", status[ids["5"]])
        for digit in "678":
            self.assertEqual("invalid_cross_repository_relationship", status[ids[digit]])
            self.assertTrue(status[ids[digit]])

    def test_cli_prints_json_or_writes_explicit_output_only(self):
        self.build_matrix()
        before = self.snapshot()
        stdout = io.StringIO()
        with patch.object(pipeline, "ROOT", self.root), patch(
            "sys.argv", ["pipeline.py", "audit-lifecycle"]
        ), contextlib.redirect_stdout(stdout):
            pipeline.main()
        self.assertEqual(1, json.loads(stdout.getvalue())["audit_version"])
        self.assertEqual(before, self.snapshot())

        output = Path(self.temp.name).parent / (Path(self.temp.name).name + "-audit.json")
        try:
            with patch.object(pipeline, "ROOT", self.root), patch(
                "sys.argv", ["pipeline.py", "audit-lifecycle", "--output", str(output)]
            ):
                pipeline.main()
            self.assertEqual(1, json.loads(output.read_text())["audit_version"])
            self.assertEqual(before, self.snapshot())
        finally:
            output.unlink(missing_ok=True)

    def test_classifies_original_v1_lifecycle_shapes(self):
        complete = "wd-" + "b" * 24
        incomplete = "wd-" + "c" * 24
        for cid in (complete, incomplete):
            request = {
                "request_version": 1,
                "content_id": cid,
                "visibility": "public",
            }
            raw = encoded(request)
            (self.root / "content/requests" / f"{cid}.json").write_bytes(raw)
            eid = "ex-" + cid[3] * 24
            execution = {
                "execution_version": 1,
                "execution_id": eid,
                "content_id": cid,
                "request_path": f"content/requests/{cid}.json",
                "request_source_sha": cid[3] * 40,
                "request_blob_sha": blob(raw),
                "state": "prepared",
            }
            (self.root / "content/executions" / f"{eid}.json").write_bytes(encoded(execution))
            if cid == complete:
                directory = self.root / "content/executions/evidence" / cid
                directory.mkdir(parents=True)
                upload = {
                    "evidence_version": 1,
                    "record_type": "upload",
                    "content_id": cid,
                    "request_path": execution["request_path"],
                    "request_blob_sha": execution["request_blob_sha"],
                    "source_commit_sha": execution["request_source_sha"],
                    "youtube_video_id": "abcdefghijk",
                }
                (directory / "upload.json").write_bytes(encoded(upload))
                result = {
                    "result_version": 1,
                    "content_id": cid,
                    "execution_id": eid,
                    "status": "published",
                    "youtube_video_id": "abcdefghijk",
                    "visibility": "public",
                    "verified": True,
                    "published_at": "2026-09-15T01:54:59Z",
                }
                (self.root / "content/results" / f"{cid}.json").write_bytes(encoded(result))
                self.history.append(
                    {"content_id": cid, "published_at": result["published_at"]}
                )
        (self.root / "data/history.json").write_bytes(encoded(self.history))

        report = audit_lifecycle(self.root)
        status = {item["content_id"]: item["status"] for item in report["items"]}

        self.assertEqual("legacy_evidence_alias", status[complete])
        self.assertEqual("execution_without_evidence", status[incomplete])
        self.assertEqual([], report["validation_errors"])


if __name__ == "__main__":
    unittest.main()
