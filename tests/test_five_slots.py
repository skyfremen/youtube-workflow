import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pipeline as p

class FiveSlotTests(unittest.TestCase):
    def test_five_slots_allocate_next_day_after_last_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "slots.json"
            path.write_text(json.dumps({"timezone": "Asia/Singapore", "slots": ["03:00", "06:00", "12:00", "15:00", "18:00"]}))
            self.assertEqual(p.publish_slots(path), [(3,0),(6,0),(12,0),(15,0),(18,0)])
            with patch.object(p, "publish_slots", side_effect=lambda: p.publish_slots_original(path)), patch.object(p, "youtube_scheduled_slots", return_value=set()), patch.object(p, "request_publish_slots", return_value=set()):
                self.assertEqual(p.allocate_publish_slots(2, p.datetime(2030,1,1,17,0,tzinfo=p.SGT)), ["2030-01-01T10:00:00Z","2030-01-01T19:00:00Z"])

p.publish_slots_original = p.publish_slots
