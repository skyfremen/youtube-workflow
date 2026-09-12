import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from validation import planning_audit
from validation.validate_content import SCHEMA_VERSION


class PlanningAuditV5Tests(unittest.TestCase):
    def test_current_schema_daily_request_passes_version_gate(self):
        self.assertEqual(SCHEMA_VERSION, 5)
        content_id = "wd-20990910T000000-drama-cafe-a1b2c3"
        relative = f"youtube-shorts-bot/content/requests/{content_id}.json"
        request = {
            "schema_version": SCHEMA_VERSION,
            "content_id": content_id,
            "planning": {"plan_date": "2099-09-10"},
            "publication": {
                "mode": "scheduled",
                "publish_at": "2099-09-09T16:00:00Z",
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / relative
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(request), encoding="utf-8")
            with mock.patch.object(planning_audit, "REPO_ROOT", root), mock.patch.object(
                planning_audit, "validate_request_data", return_value=[]
            ), mock.patch.object(
                planning_audit, "build_upload_body", return_value={}
            ):
                loaded = planning_audit._validate_requests(
                    "2099-09-10", [relative], [content_id]
                )
        self.assertEqual(loaded[content_id]["schema_version"], SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
