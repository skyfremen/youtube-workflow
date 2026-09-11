import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analytics import analytics_collection


class RawAnalyticsTests(unittest.TestCase):
    def test_aggregate_row_takes_precedence_over_recent_statistics(self):
        raw = {
            "aggregate": [
                {"video": "abc", "views": 90, "engagedViews": 70, "data_source": "aggregate"}
            ],
            "recent": [
                {"video": "abc", "views": 120, "engagedViews": None, "data_source": "recent_statistics"},
                {"video": "def", "views": 10, "engagedViews": None, "data_source": "recent_statistics"},
            ],
        }
        rows = analytics_collection.raw_rows_by_video(raw)
        self.assertEqual(rows["abc"]["views"], 90)
        self.assertEqual(rows["abc"]["data_source"], "aggregate")
        self.assertEqual(rows["def"]["views"], 10)

    def test_raw_snapshot_uses_capture_time_as_canonical_age_clock(self):
        payload = {
            "schema_version": 1,
            "captured_at": "2026-09-11T06:30:00Z",
            "window": {"start_date": "2026-06-13", "end_date": "2026-09-11"},
            "aggregate": [],
            "recent": [],
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "latest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(analytics_collection, "RAW_PATH", path):
                loaded, captured = analytics_collection.load_raw_snapshot()
        self.assertEqual(loaded["captured_at"], payload["captured_at"])
        self.assertEqual(captured.isoformat(), "2026-09-11T06:30:00+00:00")


if __name__ == "__main__":
    unittest.main()
