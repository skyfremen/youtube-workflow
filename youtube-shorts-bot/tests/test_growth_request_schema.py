import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from growth_config import EDITORIAL_WEIGHTS, TITLE_WEIGHTS
from upload import build_upload_body
from validate_content import validate_request_data

def scheduled_request():
    title = "My Boss Said the File Was Gone… Then IT Found the Backup #Shorts"
    def title_item(text, style, score): return {"title": text, "style": style, "truthful": True, "score": score, "score_components": {k: score for k in TITLE_WEIGHTS}}
    return {"schema_version":3,"content_id":"wd-20260910T000000-backup-proof-a7c42f","channel":{"name":"Wacky Dramas","handle":"@WACKYDRAMAS"},"story":{"category":"WORKPLACE","story_type":"BACKFIRE","hook":"The Backup He Forgot About","script":"My boss told the team the file had never existed. I opened the archived workspace and found the timestamped copy.","card_emojis":["💼","🗂️","😳","💾","🔥"]},"narration":{"engine":"kokoro","voice":"af_heart","speed":1.75},"visual":{"background_primary_id":"satisfying-001","background_backup_id":"satisfying-002"},"youtube":{"title":title,"description":"My boss said the file never existed—until the archived timestamp proved otherwise. Would you have confronted him?","hashtags":["#Shorts","#WackyDramas","#WorkplaceDrama","#Storytime"],"tags":["wacky dramas","workplace drama","boss story","office conflict","evidence backfire","storytime"],"category_id":"24","made_for_kids":False},"publication":{"mode":"scheduled","timezone":"Asia/Singapore","publish_at":"2099-09-09T16:00:00Z"},"planning":{"plan_date":"2099-09-10","editorial_score":88.0,"editorial_components":{k:88 for k in EDITORIAL_WEIGHTS},"analytics_score":None,"analytics_weight":0.0,"final_score":87.5,"title_candidates":[title_item(title,"HIDDEN_REVELATION",91),title_item("I Checked the Archive and Found the Proof #Shorts","DISCOVERY",86),title_item("It Looked Like a Normal File Error… Until I Saw the Timestamp #Shorts","NORMAL_TO_ABNORMAL",84),title_item("I Refused to Delete the Archive. Then My Boss Changed His Story #Shorts","DECISION_CONSEQUENCE",83),title_item("Hours Before the Audit, I Found the Missing Backup #Shorts","COUNTDOWN",82)],"selected_title_score":91.0,"hook_score":90.0,"selection_class":"exploit","selection_reason":"Strong contradiction, proof-driven escalation and clear reversal.","similarity":{"max_recent_similarity":0.21},"attributes":{"subtype":"EVIDENCE_BACKFIRE","conflict":"HIDDEN_FILE","primary_emotion":"INJUSTICE","protagonist_role":"EMPLOYEE","antagonist_role":"BOSS","opening_style":"CONTRADICTION","title_style":"HIDDEN_REVELATION","ending_style":"REVERSAL"},"target_duration_seconds":151}}

class GrowthRequestSchemaTests(unittest.TestCase):
    def test_schema_v3_scheduled_request_passes(self): self.assertEqual(validate_request_data(scheduled_request()), [])
    def test_schema_v3_requires_exact_singapore_schedule_contract(self):
        data=scheduled_request(); data["publication"]["timezone"]="UTC"; self.assertTrue(any("Asia/Singapore" in x for x in validate_request_data(data)))
    def test_schema_v3_title_must_be_truthful_and_present_in_competition(self):
        data=scheduled_request(); data["planning"]["title_candidates"][0]["truthful"]=False; self.assertTrue(any("must be truthful" in x for x in validate_request_data(data)))
        data=scheduled_request(); data["youtube"]["title"]="A Different Accurate Title #Shorts"; self.assertTrue(any("exactly match" in x for x in validate_request_data(data)))
    def test_schema_v3_rejects_uncontrolled_attribute(self):
        data=scheduled_request(); data["planning"]["attributes"]["opening_style"]="RANDOM_FREE_TEXT"; self.assertTrue(any("opening_style" in x for x in validate_request_data(data)))
    def test_schema_v3_requires_semantic_backend_tags(self):
        data=scheduled_request(); data["youtube"].pop("tags"); self.assertTrue(any("youtube missing fields: tags" in x for x in validate_request_data(data)))
        data=scheduled_request(); data["youtube"]["tags"]=["one","two","three"]; self.assertTrue(any("4-12" in x for x in validate_request_data(data)))
    def test_upload_body_contains_planned_tags_hashtags_and_hidden_marker(self):
        data=scheduled_request(); body=build_upload_body(data, require_future=False)
        tags=body["snippet"]["tags"]
        self.assertIn("wacky dramas", tags); self.assertIn("workplace drama", tags); self.assertIn("Shorts", tags); self.assertIn("WackyDramas", tags)
        self.assertTrue(tags[0].startswith("wd-id-")); self.assertEqual(len(tags), len({x.lower() for x in tags}))
    def test_description_gets_missing_hashtags_once(self):
        data=scheduled_request(); body=build_upload_body(data, require_future=False); description=body["snippet"]["description"]
        self.assertEqual(description.count("#WackyDramas"),1); self.assertIn("Would you have confronted him?",description)
    def test_scheduled_upload_body_is_private_with_exact_publish_at(self):
        data=scheduled_request()
        with patch("upload.datetime") as mocked_datetime:
            from datetime import datetime, timezone
            mocked_datetime.fromisoformat.side_effect=datetime.fromisoformat; mocked_datetime.now.return_value=datetime(2099,9,9,0,0,tzinfo=timezone.utc); body=build_upload_body(data)
        self.assertEqual(body["status"]["privacyStatus"],"private"); self.assertEqual(body["status"]["publishAt"],data["publication"]["publish_at"])
if __name__ == "__main__": unittest.main()
