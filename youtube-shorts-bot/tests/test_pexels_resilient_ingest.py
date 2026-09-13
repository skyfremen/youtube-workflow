import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media import pexels_resilient_ingest


def manifest_file():
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    payload = {
        "schema_version": 1,
        "plan_date": "2026-09-13",
        "provider": "Pexels",
        "candidates": [
            {"logical_id": "satisfying-px-1", "provider_asset_id": "1"},
            {"logical_id": "satisfying-px-2", "provider_asset_id": "2"},
            {"logical_id": "satisfying-px-3", "provider_asset_id": "3"},
        ],
    }
    json.dump(payload, handle)
    handle.close()
    return Path(handle.name)


class PexelsResilientIngestTests(unittest.TestCase):
    def test_bad_candidates_do_not_block_later_reserves(self):
        path = manifest_file()
        calls = iter(
            [
                ValueError("no production rendition"),
                {"added": ["satisfying-px-2"], "already_cached": []},
                {"added": [], "already_cached": ["satisfying-px-3"]},
            ]
        )

        def fake_ingest(*args, **kwargs):
            result = next(calls)
            if isinstance(result, Exception):
                raise result
            return result

        try:
            with patch(
                "media.pexels_resilient_ingest.pexels_registry.validate_sourcing_manifest",
                return_value=[],
            ), patch(
                "media.pexels_resilient_ingest.pexels_registry.ingest_manifest",
                side_effect=fake_ingest,
            ):
                result = pexels_resilient_ingest.ingest_resilient(path, "/tmp/test-registry.json")
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(result["candidate_count"], 3)
        self.assertEqual(result["accepted_count"], 2)
        self.assertEqual(result["rejected_count"], 1)
        self.assertEqual(result["added"], ["satisfying-px-2"])
        self.assertEqual(result["already_cached"], ["satisfying-px-3"])
        self.assertEqual(result["rejected"][0]["logical_id"], "satisfying-px-1")

    def test_identity_collision_remains_hard_failure(self):
        path = manifest_file()
        try:
            with patch(
                "media.pexels_resilient_ingest.pexels_registry.validate_sourcing_manifest",
                return_value=[],
            ), patch(
                "media.pexels_resilient_ingest.pexels_registry.ingest_manifest",
                side_effect=ValueError("Background sourcing identity collision: x"),
            ):
                with self.assertRaises(ValueError):
                    pexels_resilient_ingest.ingest_resilient(path, "/tmp/test-registry.json")
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
