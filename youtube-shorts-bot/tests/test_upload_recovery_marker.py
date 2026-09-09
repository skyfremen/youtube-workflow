import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import upload


def _request():
    return {
        "content_id": "wd-test-tag-only-recovery",
        "youtube": {
            "title": "Test title",
            "description": "Viewer-facing description only",
            "hashtags": ["#Shorts", "#WackyDramas"],
            "category_id": "24",
            "made_for_kids": False,
        },
    }


def _identity():
    return {
        "content_id": "wd-test-tag-only-recovery",
        "request_blob_sha": "0123456789abcdef",
        "source_commit_sha": "fedcba9876543210",
    }


class TagRecoveryTests(unittest.TestCase):
    def test_upload_body_keeps_recovery_out_of_description_and_in_tags(self):
        with patch.object(upload, "marker_tag", side_effect=lambda content_id: "wd-id-" + content_id):
            body = upload.build_upload_body(_request(), identity=_identity())

        self.assertEqual(body["snippet"]["description"], "Viewer-facing description only\n\n#Shorts #WackyDramas")
        self.assertNotIn("content_id=", body["snippet"]["description"])
        self.assertNotIn("request_blob_sha=", body["snippet"]["description"])
        self.assertIn("wd-id-wd-test-tag-only-recovery", body["snippet"]["tags"])


    def test_find_existing_recovers_by_tag_with_clean_description(self):
        playlist_items = Mock()
        playlist_items.list.return_value.execute.return_value = {
            "items": [{"contentDetails": {"videoId": "AbCdEfGhI12"}}]
        }
        videos = Mock()
        videos.list.return_value.execute.return_value = {
            "items": [{
                "id": "AbCdEfGhI12",
                "snippet": {
                    "channelId": "UC_TEST",
                    "publishedAt": "2026-09-09T00:00:00Z",
                    "description": "Viewer-facing description only",
                    "tags": ["wd-id-wd-test-tag-only-recovery", "Shorts"],
                },
                "status": {"privacyStatus": "private"},
            }]
        }
        youtube = Mock()
        youtube.playlistItems.return_value = playlist_items
        youtube.videos.return_value = videos
        channel = {
            "id": "UC_TEST",
            "contentDetails": {"relatedPlaylists": {"uploads": "UU_TEST"}},
        }

        with patch.object(upload, "marker_tag", side_effect=lambda content_id: "wd-id-" + content_id):
            found = upload.find_existing_by_marker(
                youtube,
                _identity()["content_id"],
                identity=_identity(),
                channel=channel,
            )

        self.assertEqual(found["id"], "AbCdEfGhI12")
        self.assertNotIn("content_id=", found["snippet"]["description"])


    def test_find_existing_does_not_match_clean_description_without_tag(self):
        playlist_items = Mock()
        playlist_items.list.return_value.execute.return_value = {
            "items": [{"contentDetails": {"videoId": "AbCdEfGhI12"}}]
        }
        videos = Mock()
        videos.list.return_value.execute.return_value = {
            "items": [{
                "id": "AbCdEfGhI12",
                "snippet": {
                    "channelId": "UC_TEST",
                    "publishedAt": "2026-09-09T00:00:00Z",
                    "description": "Viewer-facing description only",
                    "tags": ["Shorts"],
                },
                "status": {"privacyStatus": "private"},
            }]
        }
        youtube = Mock()
        youtube.playlistItems.return_value = playlist_items
        youtube.videos.return_value = videos
        channel = {
            "id": "UC_TEST",
            "contentDetails": {"relatedPlaylists": {"uploads": "UU_TEST"}},
        }

        with patch.object(upload, "marker_tag", side_effect=lambda content_id: "wd-id-" + content_id):
            found = upload.find_existing_by_marker(
                youtube,
                _identity()["content_id"],
                identity=_identity(),
                channel=channel,
            )
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
