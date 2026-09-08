import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from validate_content import validate_request_data


def valid_request():
    return {
        "schema_version": 2,
        "content_id": "wd-20260908T161000-boss-overtime-a7c42f",
        "channel": {"name": "Wacky Dramas", "handle": "@WACKYDRAMAS"},
        "story": {
            "category": "WORKPLACE",
            "story_type": "BACKFIRE",
            "hook": "My boss demanded unpaid overtime. It backfired.",
            "script": "I thought the request was strange, so I asked for it in writing. HR noticed.",
            "card_emojis": ["💼", "😤", "📧", "😳", "🔥"],
        },
        "narration": {"engine": "kokoro", "voice": "af_heart", "speed": 1.75},
        "visual": {
            "background_primary_id": "satisfying-001",
            "background_backup_id": "satisfying-002",
        },
        "youtube": {
            "title": "My Boss Demanded Unpaid Overtime — It Backfired #Shorts",
            "description": "An original Wacky Dramas story.",
            "hashtags": ["#shorts", "#storytime", "#wackydramas"],
            "category_id": "24",
            "made_for_kids": False,
        },
    }


class RequestSchemaTests(unittest.TestCase):
    def test_valid_request_passes(self):
        self.assertEqual(validate_request_data(valid_request()), [])

    def test_old_field_fails(self):
        data = valid_request()
        data["setup"] = "obsolete"
        self.assertTrue(any("unexpected" in x or "forbidden" in x for x in validate_request_data(data)))

    def test_wrong_brand_fails(self):
        data = valid_request()
        data["channel"]["handle"] = "@WACKYINSIGHTS"
        self.assertTrue(validate_request_data(data))

    def test_primary_backup_must_differ(self):
        data = valid_request()
        data["visual"]["background_backup_id"] = data["visual"]["background_primary_id"]
        self.assertTrue(any("must differ" in x for x in validate_request_data(data)))


if __name__ == "__main__":
    unittest.main()
