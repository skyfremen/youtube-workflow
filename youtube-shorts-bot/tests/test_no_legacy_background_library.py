import unittest
from pathlib import Path


BOT_ROOT = Path(__file__).resolve().parents[1]
MEDIA_LIBRARY = BOT_ROOT / "media-library"


class NoLegacyBackgroundLibraryTests(unittest.TestCase):
    def test_only_current_background_registry_exists(self):
        current_registry = MEDIA_LIBRARY / "backgrounds.json"
        self.assertTrue(current_registry.is_file())
        background_registries = sorted(
            path.name for path in MEDIA_LIBRARY.glob("backgrounds*.json")
        )
        self.assertEqual(background_registries, ["backgrounds.json"])
        self.assertFalse((MEDIA_LIBRARY / "backgrounds-legacy-v5.json").exists())

    def test_current_validator_has_no_deleted_background_fallback(self):
        validator = (BOT_ROOT / "validation" / "validate_content.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "backgrounds-legacy-v5.json",
            "LEGACY_REGISTRY_PATH",
            "legacy_registry.load_registry",
        ):
            self.assertNotIn(forbidden, validator)

    def test_background_policy_documents_destructive_removal(self):
        strategy = (BOT_ROOT / "docs" / "background-media-strategy.md").read_text(
            encoding="utf-8"
        )
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(
            encoding="utf-8"
        )
        recovery = (BOT_ROOT / "docs" / "RECOVERY.md").read_text(encoding="utf-8")
        for text in (strategy, overview, recovery):
            self.assertNotIn("backgrounds-legacy-v5.json", text)
        self.assertIn("destructively removed", strategy)
        self.assertIn("only background registry", overview)
        self.assertIn("only one background registry", recovery)


if __name__ == "__main__":
    unittest.main()
