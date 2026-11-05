import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pipeline as p


class YouTubeReadRetryTests(unittest.TestCase):
    def test_transient_read_failures_recover_without_losing_response(self):
        for error in (TimeoutError(), URLError(ConnectionResetError()),
                      HTTPError('https://example.test', 503, 'unavailable', {}, None),
                      HTTPError('https://example.test', 429, 'limited', {}, None)):
            with self.subTest(error=type(error).__name__), patch.object(
                p, 'urlopen', side_effect=[error, io.BytesIO(b'{"items":[{"id":"video1"}]}')]
            ), patch('time.sleep'):
                self.assertEqual(p.youtube_get('playlistItems', {'part': 'contentDetails'}, 'token'),
                                 {'items': [{'id': 'video1'}]})

    def test_exhausted_timeouts_preserve_nonrepairable_failure(self):
        with patch.object(p, 'urlopen', side_effect=TimeoutError()), patch('time.sleep') as delay:
            with self.assertRaises(p.VError) as caught:
                p.youtube_get('playlistItems', {}, 'token')
        self.assertEqual(caught.exception.code, 'YOUTUBE_QUERY_FAILED')
        self.assertEqual(caught.exception.field, 'playlistItems')
        self.assertEqual(caught.exception.observed, 'TimeoutError')
        self.assertFalse(caught.exception.repairable)
        self.assertEqual(delay.call_count, 2)

    def test_permanent_http_errors_do_not_retry(self):
        for status in (400, 401, 403, 404):
            with self.subTest(status=status), patch.object(p, 'urlopen', side_effect=[
                HTTPError('https://example.test', status, 'permanent', {}, None),
                io.BytesIO(b'{"items":[]}')
            ]), patch('time.sleep') as delay:
                with self.assertRaises(p.VError):
                    p.youtube_get('playlistItems', {}, 'token')
                delay.assert_not_called()

    def test_invalid_json_is_not_retried(self):
        with patch.object(p, 'urlopen', return_value=io.BytesIO(b'not json')), patch('time.sleep') as delay:
            with self.assertRaises(json.JSONDecodeError):
                p.youtube_get('playlistItems', {}, 'token')
            delay.assert_not_called()


if __name__ == '__main__':
    unittest.main()
