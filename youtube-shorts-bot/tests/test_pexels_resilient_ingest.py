import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media import pexels_registry, pexels_resilient_ingest


def _candidate(provider_id):
    return {
        "logical_id": f"satisfying-px-{provider_id}",
        "provider_asset_id": str(provider_id),
        "source_page": f"https://www.pexels.com/video/test-{provider_id}/",
        "title": f"Test background {provider_id}",
        "visual_tags": ["test", "process"],
        "motion_type": "continuous-process",
        "motion_intensity": "high",
        "loopability_score": 90,
        "visual_satisfaction_score": 90,
        "caption_readability_score": 90,
        "verified_preview": True,
        "required_by_content_ids": ["readiness-test"],
    }


def manifest_file():
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    payload = {
        "schema_version": 1,
        "plan_date": "2026-09-13",
        "provider": "Pexels",
        "candidates": [_candidate(101), _candidate(102), _candidate(103)],
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
                {"added": ["satisfying-px-102"], "already_cached": []},
                {"added": [], "already_cached": ["satisfying-px-103"]},
            ]
        )

        def fake_ingest(manifest_path, *args, **kwargs):
            single = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            self.assertEqual(pexels_registry.validate_sourcing_manifest(single), [])
            self.assertEqual(len(single["candidates"]), 1)
            result = next(calls)
            if isinstance(result, Exception):
                raise result
            return result

        try:
            with patch(
                "media.pexels_resilient_ingest.pexels_registry.ingest_manifest",
                side_effect=fake_ingest,
            ):
                result = pexels_resilient_ingest.ingest_resilient(path, "/tmp/test-registry.json")
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(result["candidate_count"], 3)
        self.assertEqual(result["accepted_count"], 2)
        self.assertEqual(result["rejected_count"], 1)
        self.assertEqual(result["added"], ["satisfying-px-102"])
        self.assertEqual(result["already_cached"], ["satisfying-px-103"])
        self.assertEqual(result["rejected"][0]["logical_id"], "satisfying-px-101")

    def test_identity_collision_remains_hard_failure(self):
        path = manifest_file()
        try:
            with patch(
                "media.pexels_resilient_ingest.pexels_registry.ingest_manifest",
                side_effect=ValueError("Background sourcing identity collision: x"),
            ):
                with self.assertRaises(ValueError):
                    pexels_resilient_ingest.ingest_resilient(path, "/tmp/test-registry.json")
        finally:
            path.unlink(missing_ok=True)

    def test_unexpected_programming_error_is_not_swallowed(self):
        path = manifest_file()
        try:
            with patch(
                "media.pexels_resilient_ingest.pexels_registry.ingest_manifest",
                side_effect=KeyError("unexpected bug"),
            ):
                with self.assertRaises(KeyError):
                    pexels_resilient_ingest.ingest_resilient(path, "/tmp/test-registry.json")
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
