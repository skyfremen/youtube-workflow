import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from finalize import build_receipt
from recovery_state import RecoveryBlocked, blob_sha
from test_recovery import fixture


class ResultReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.request, identity, record, item = fixture()
        self.path = Path(self.temp.name)/(self.request['content_id']+'.json')
        self.path.write_text(json.dumps(self.request))
        identity['request_blob_sha'] = blob_sha(self.path.read_bytes())
        record.update(identity)
        self.selection = {'background_asset_id': self.request['visual']['background_primary_id'], 'background_selection': 'primary'}
        self.render = {'content_id': self.request['content_id'], 'render_verified': True, 'narration_engine': 'kokoro',
                       'narration_voice': 'af_heart', 'narration_speed': 1.75, 'narration_seconds': 4.875,
                       'video_seconds': 5.233, 'resolution': '720x1280', 'fps': 30.0, 'video_codec': 'h264',
                       'audio_codec': 'aac', 'audio_stream_count': 1, 'test_mode': True}
        record.update({'background': self.selection, 'render': self.render})
        self.upload = {**identity, 'youtube_video_id': record['youtube_video_id'], 'youtube_url': 'https://www.youtube.com/watch?v='+record['youtube_video_id'],
                       'upload_evidence': record, 'uploaded_at': record['uploaded_at'], 'recovered': True,
                       'recovery_record_path': 'evidence', 'recovery_record_blob_sha': 'c'*40,
                       'verification': {**identity, 'passed': True, 'state': 'verified_private', 'privacy_status': 'private',
                                        'publish_at_absent': True, 'youtube_video_id': record['youtube_video_id'],
                                        'channel_id': record['expected_channel_id'], 'verified_at': '2026-09-08T17:08:24Z'}}
        p=patch('finalize.workflow_identity',return_value={'name':'Recovery','run_id':'20','run_attempt':'2','code_commit_sha':'d'*40});p.start();self.addCleanup(p.stop)

    def build(self): return build_receipt(self.path, self.request, self.upload, self.selection, self.render)

    def test_complete_measured_provenance(self):
        receipt=self.build()
        self.assertEqual(receipt['video_seconds'],5.233)
        self.assertEqual(receipt['renderer_source_commit'],'b'*40)
        self.assertEqual(receipt['verification_source_commit'],'d'*40)
        self.assertEqual(receipt['upload_workflow']['run_id'],'1')
        self.assertEqual(receipt['workflow_run_id'],'20')
        self.assertEqual(receipt['workflow_run_attempt'],'2')
        self.assertTrue(receipt['publish_at_absent'])
        self.assertEqual(receipt['audio_stream_count'],1)

    def test_private_label_without_verification_cannot_create_receipt(self):
        self.upload['privacy_status']='private';self.upload['verification']['passed']=False
        with self.assertRaises(RecoveryBlocked):self.build()

    def test_changed_request_cannot_create_receipt(self):
        self.path.write_text(self.path.read_text()+' ')
        with self.assertRaises(RecoveryBlocked):self.build()

    def test_wrong_video_or_channel_or_schedule_cannot_create_receipt(self):
        original=copy.deepcopy(self.upload)
        for key,value in [('youtube_video_id','other000000'),('channel_id','foreign'),('publish_at_absent',False)]:
            self.upload=copy.deepcopy(original);self.upload['verification'][key]=value
            with self.assertRaises(RecoveryBlocked):self.build()

    def test_unverified_or_changed_render_cannot_create_receipt(self):
        self.render['render_verified']=False
        with self.assertRaises(RecoveryBlocked):self.build()

    def test_failed_receipt_commit_then_rerun_preserves_one_immutable_receipt(self):
        import finalize
        from recovery_state import receipt_path, record_path, encoded_json
        from test_recovery import MemoryState
        from workflow_common import atomic_write_json
        identity={key:self.upload[key] for key in ('content_id','request_path','request_blob_sha','source_commit_sha')}
        state=MemoryState()
        stored=state.create(record_path(identity['content_id'],'upload'),self.upload['upload_evidence'])
        self.upload['recovery_record_blob_sha']=stored.sha
        out=Path(self.temp.name)/'output';out.mkdir()
        for name,data in [('upload_result.json',self.upload),('background_selection.json',self.selection),('render-metadata.json',self.render)]:
            atomic_write_json(out/name,data)
        real_create=state.create
        state.create=lambda path,data: (_ for _ in ()).throw(RecoveryBlocked('receipt commit failed'))
        with patch('finalize.GitHubState',return_value=state),patch('finalize.identity_for',return_value=identity),patch('finalize.OUTPUT_DIR',out),patch('sys.argv',['finalize','--request',str(self.path)]):
            with self.assertRaises(RecoveryBlocked):finalize.main()
            self.assertIsNone(state.load(receipt_path(identity['content_id'])))
            state.create=real_create
            finalize.main()
            original=encoded_json(state.load(receipt_path(identity['content_id'])).data)
            self.upload['verification']['verified_at']='2026-09-08T17:10:00Z'
            atomic_write_json(out/'upload_result.json',self.upload)
            finalize.main()
            self.assertEqual(original,encoded_json(state.load(receipt_path(identity['content_id'])).data))
            self.assertEqual(len(state.writes),2)  # one upload record plus one receipt


if __name__ == '__main__':unittest.main()
