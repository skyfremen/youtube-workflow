import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from recovery_state import RecoveryBlocked, Stored, blob_sha, encoded_json, record_path, GitHubState
from upload import execute_upload, build_upload_body, recover_record, find_existing_by_marker, authorize_fresh_upload
from verify_publication import verify_video, RETRY_DELAYS
from publish import prepare
from test_request_schema import valid_request

VID = 'vUTeNhM0UH8'
CHANNEL = {'id': 'UCvrq2m9G4yrwPfL_X-QPzMA', 'snippet': {'title': 'Wacky Dramas'},
           'contentDetails': {'relatedPlaylists': {'uploads': 'uploads'}}}


class MemoryState:
    def __init__(self):
        self.records = {}
        self.writes = []

    def load(self, path):
        if path in self.records:
            data = self.records[path]
            return Stored(copy.deepcopy(data), blob_sha(encoded_json(data)))

    def create(self, path, data):
        prior = self.load(path)
        if prior:
            if prior.data != data:
                raise RecoveryBlocked('immutable')
            return prior
        self.records[path] = copy.deepcopy(data)
        self.writes.append(path)
        return Stored(copy.deepcopy(data), blob_sha(encoded_json(data)), True, 'c' * 40)


def fixture():
    request = valid_request()
    identity = {'content_id': request['content_id'], 'request_path': 'youtube-shorts-bot/content/requests/' + request['content_id'] + '.json',
                'request_blob_sha': 'a' * 40, 'source_commit_sha': 'b' * 40}
    record = {'schema_version': 1, 'record_type': 'upload', **identity, 'youtube_video_id': VID,
              'expected_channel_id': CHANNEL['id'], 'created_at': '2026-09-08T16:50:00Z',
              'uploaded_at': '2026-09-08T16:50:40Z', 'background': {}, 'render': {},
              'upload_workflow': {'name': 'Original', 'run_id': '1', 'run_attempt': '1', 'code_commit_sha': 'b' * 40},
              'upload_body': build_upload_body(request, identity=identity),
              'association': {'kind': 'youtube_insert_response', 'response': {'id': VID}}}
    item = {'id': VID, 'snippet': {**record['upload_body']['snippet'], 'channelId': CHANNEL['id'], 'publishedAt': '2026-09-08T16:50:40Z'},
            'status': {'privacyStatus': 'public', 'uploadStatus': 'processed'}}
    return request, identity, record, item


def client_for(items):
    client = Mock()
    client.channels.return_value.list.return_value.execute.return_value = {'items': [CHANNEL]}
    client.videos.return_value.list.return_value.execute.side_effect = [{'items': x} for x in items]
    return client


class VerificationTests(unittest.TestCase):
    def test_missing_tags_do_not_break_durable_video_id_recovery(self):
        request, identity, record, item = fixture()
        item['snippet'].pop('tags')
        result = verify_video(client_for([[item]]), request, identity, record, sleep=Mock())
        self.assertTrue(result['passed'])
        self.assertEqual(result['observed_marker_tags'], [])

    def test_original_long_tag_is_still_recognized(self):
        request, identity, record, item = fixture()
        item['snippet']['tags'] = ['wd-id-' + identity['content_id']]
        result = verify_video(client_for([[item]]), request, identity, record, sleep=Mock())
        self.assertEqual(result['observed_marker_tags'], item['snippet']['tags'])

    def test_not_visible_then_processing_then_ready(self):
        request, identity, record, item = fixture()
        pending = copy.deepcopy(item)
        pending['status']['uploadStatus'] = 'uploaded'
        sleep = Mock()
        result = verify_video(client_for([[], [pending], [item]]), request, identity, record, sleep=sleep)
        self.assertEqual(result['attempts'], 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(result['state'], 'verified_public')

    def test_historical_private_upload_still_verifies_from_durable_evidence(self):
        request, identity, record, item = fixture()
        record['upload_body']['status']['privacyStatus'] = 'private'
        item['status']['privacyStatus'] = 'private'
        result = verify_video(client_for([[item]]), request, identity, record, sleep=Mock())
        self.assertEqual(result['state'], 'verified_private')
        self.assertEqual(result['privacy_status'], 'private')

    def test_read_delay_is_bounded(self):
        request, identity, record, item = fixture()
        sleep = Mock()
        with self.assertRaisesRegex(RecoveryBlocked, 'bounded'):
            verify_video(client_for([[] for _ in RETRY_DELAYS]), request, identity, record, sleep=sleep)
        self.assertEqual(sleep.call_count, len(RETRY_DELAYS) - 1)

    def test_real_mismatches_fail_without_retry(self):
        for field, value in [('private', None), ('unlisted', None), ('publishAt', None), ('publishAt', ''),
                             ('publishAt', '2099-01-01T00:00:00Z'), ('id', 'another0000'), ('owner', 'foreign'),
                             ('title', 'Other story'), ('description', 'Changed'), ('failed', None)]:
            with self.subTest(field=field, value=value):
                request, identity, record, item = fixture()
                if field in {'private', 'unlisted'}: item['status']['privacyStatus'] = field
                elif field == 'publishAt': item['status'][field] = value
                elif field == 'id': item['id'] = value
                elif field == 'owner': item['snippet']['channelId'] = value
                elif field in {'title', 'description'}: item['snippet'][field] = value
                else: item['status']['uploadStatus'] = 'failed'
                sleep = Mock()
                with self.assertRaises(RecoveryBlocked):
                    verify_video(client_for([[item]]), request, identity, record, sleep=sleep)
                sleep.assert_not_called()

    def test_wrong_request_evidence_fails_before_api_read(self):
        request, identity, record, item = fixture()
        record['request_blob_sha'] = 'f' * 40
        client = Mock()
        with self.assertRaises(RecoveryBlocked): verify_video(client, request, identity, record)
        client.channels.assert_not_called()


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        for module in ('upload', 'publish'):
            p = patch(module + '.OUTPUT_DIR', Path(self.temp.name)); p.start(); self.addCleanup(p.stop)
        p = patch('upload.source_supports_intent', return_value=True);p.start();self.addCleanup(p.stop)
        p = patch('upload.workflow_identity', return_value={'name': 'Upload', 'run_id': '2', 'run_attempt': '1', 'code_commit_sha': 'b' * 40});p.start();self.addCleanup(p.stop)
        self.request, self.identity, self.record, self.item = fixture()
        self.state = MemoryState()

    def execute(self):
        return execute_upload(self.request, Path(self.temp.name)/'video.mp4', state=self.state, identity=self.identity,
                              channel=CHANNEL, selection={}, render_meta={}, youtube=Mock())

    @patch('upload.find_existing_by_marker', return_value=None)
    @patch('upload.upload_new', return_value={'id': VID})
    def test_normal_rerun_reuses_id_and_calls_insert_once(self, insert, lookup):
        first, recovered = self.execute()
        second, recovered_again = self.execute()
        self.assertFalse(recovered)
        self.assertTrue(recovered_again)
        self.assertEqual(first.data['youtube_video_id'], second.data['youtube_video_id'])
        self.assertEqual(first.data['upload_body']['status']['privacyStatus'], 'public')
        insert.assert_called_once()
        self.assertEqual(len(self.state.writes), 2)

    @patch('upload.find_existing_by_marker', return_value=None)
    @patch('upload.upload_new', side_effect=TimeoutError('response lost'))
    def test_lost_response_and_invisible_metadata_fence_all_future_uploads(self, insert, lookup):
        with self.assertRaises(RecoveryBlocked): self.execute()
        with self.assertRaises(RecoveryBlocked): self.execute()
        insert.assert_called_once()
        self.assertIn(record_path(self.identity['content_id'], 'intent'), self.state.records)

    @patch('upload.upload_new', side_effect=TimeoutError('response lost'))
    def test_lost_response_recovers_later_without_another_insert(self, insert):
        with patch('upload.find_existing_by_marker', return_value=None):
            with self.assertRaises(RecoveryBlocked): self.execute()
        with patch('upload.find_existing_by_marker', return_value=self.item):
            stored, recovered = self.execute()
        self.assertTrue(recovered)
        self.assertEqual(stored.data['youtube_video_id'], VID)
        insert.assert_called_once()

    @patch('upload.find_existing_by_marker', return_value=None)
    @patch('upload.upload_new')
    def test_intent_write_failure_prevents_upload(self, insert, lookup):
        self.state.create = Mock(side_effect=RecoveryBlocked('GitHub unavailable'))
        with self.assertRaises(RecoveryBlocked): self.execute()
        insert.assert_not_called()

    @patch('upload.find_existing_by_marker', return_value=None)
    @patch('upload.upload_new', return_value={'id': VID})
    def test_upload_record_commit_failure_is_recovered_from_intent(self, insert, lookup):
        real_create = self.state.create
        def fail_upload(path, data):
            if path.endswith('/upload.json'): raise RecoveryBlocked('write response lost')
            return real_create(path, data)
        self.state.create = fail_upload
        with self.assertRaises(RecoveryBlocked): self.execute()
        self.state.create = real_create
        lookup.return_value = self.item
        stored, recovered = self.execute()
        self.assertTrue(recovered)
        self.assertEqual(stored.data['youtube_video_id'], VID)
        insert.assert_called_once()

    @patch('upload.upload_new')
    def test_recovery_only_without_record_cannot_upload(self, insert):
        with self.assertRaisesRegex(RecoveryBlocked, 'Recovery-only'):
            prepare(self.request, self.identity, self.state, Mock(), CHANNEL, True)
        insert.assert_not_called()

    @patch('upload.find_existing_by_marker', return_value=None)
    def test_old_request_without_evidence_cannot_upload(self, lookup):
        with patch('upload.source_supports_intent', return_value=False):
            with self.assertRaisesRegex(RecoveryBlocked, 'predates'):
                authorize_fresh_upload(Mock(), self.state, self.identity, CHANNEL)

    def test_multiple_marker_matches_fail_closed(self):
        other = copy.deepcopy(self.item); other['id'] = 'another0000'
        client = client_for([[self.item, other]])
        client.playlistItems.return_value.list.return_value.execute.return_value = {
            'items': [{'contentDetails': {'videoId': VID}}, {'contentDetails': {'videoId': 'another0000'}}]}
        with self.assertRaisesRegex(RecoveryBlocked, 'Multiple'):
            find_existing_by_marker(client, self.identity['content_id'], identity=self.identity, channel=CHANNEL)

    def test_inventory_truncation_is_not_absence(self):
        client = Mock()
        client.playlistItems.return_value.list.return_value.execute.return_value = {
            'items': [{'contentDetails': {'videoId': VID}}], 'nextPageToken': 'more'}
        with self.assertRaisesRegex(RecoveryBlocked, 'inventory limit'):
            find_existing_by_marker(client, self.identity['content_id'], max_videos=1, channel=CHANNEL)

    def test_github_evidence_cannot_be_overwritten(self):
        state = object.__new__(GitHubState)
        state.load = Mock(return_value=Stored(self.record, 'a'*40))
        state.api = Mock()
        changed = copy.deepcopy(self.record);changed['youtube_video_id'] = 'other000000'
        with self.assertRaisesRegex(RecoveryBlocked, 'Immutable'):
            state.create(record_path(self.identity['content_id'], 'upload'), changed)
        state.api.assert_not_called()

    def test_github_state_cannot_write_requests_or_code(self):
        for path in ('youtube-shorts-bot/render.py', self.identity['request_path'], '.github/workflows/example.yml'):
            with self.assertRaises(RecoveryBlocked): GitHubState.allowed(path)


if __name__ == '__main__': unittest.main()
