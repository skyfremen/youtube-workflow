import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
PLANNER = BOT_ROOT / "planning"
ARCH_TERM = "gro" + "wth"


class ArchitectureContractTests(unittest.TestCase):
    def test_supported_surface_is_exact(self):
        self.assertEqual(
            {path.name for path in WORKFLOWS.glob("*.yml")},
            {
                "analytics-collection.yml",
                "background-management.yml",
                "build-image.yml",
                "daily-production.yml",
                "dry-run.yml",
            },
        )
        self.assertEqual(
            {path.name for path in PLANNER.glob("*.md")},
            {"DAILY_PLANNER_PROMPT.md", "STORY_RULES.md"},
        )

    def test_growth_is_business_language_not_technical_architecture(self):
        path_hits = []
        for root in (BOT_ROOT, WORKFLOWS):
            for path in root.rglob("*"):
                if path.is_file() and ARCH_TERM in path.name.lower():
                    path_hits.append(str(path.relative_to(REPO_ROOT)))
        self.assertFalse(path_hits, "architecture term remains in filenames: " + "; ".join(path_hits))

        code_hits = []
        for path in [
            *BOT_ROOT.rglob("*.py"),
            *(BOT_ROOT / "tests").glob("*.py"),
            *WORKFLOWS.glob("*.yml"),
        ]:
            if path == Path(__file__).resolve():
                continue
            if ARCH_TERM in path.read_text(encoding="utf-8").lower():
                code_hits.append(str(path.relative_to(REPO_ROOT)))
        self.assertFalse(code_hits, "architecture term remains in code: " + "; ".join(code_hits))

        prompt = (PLANNER / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")
        for text in (prompt, overview):
            self.assertIn("subscriber and qualified-view " + ARCH_TERM, text)
            self.assertIn("1,000 subscribers", text)
            self.assertIn("10 million qualified public Shorts views", text)
        self.assertIn("business-purpose language only", overview)

    def test_request_and_publication_contract_is_schema_v3_only(self):
        validator = (BOT_ROOT / "validation/validate_content.py").read_text(encoding="utf-8")
        upload = (BOT_ROOT / "publishing/upload.py").read_text(encoding="utf-8")
        publish = (BOT_ROOT / "publishing/publish.py").read_text(encoding="utf-8")
        verify = (BOT_ROOT / "publishing/verify_publication.py").read_text(encoding="utf-8")
        finalize = (BOT_ROOT / "publishing/finalize_receipt.py").read_text(encoding="utf-8")
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")

        self.assertIn("SCHEMA_VERSION = 3", validator)
        self.assertNotIn("YOUTUBE_KEYS_V2", validator)
        self.assertNotIn("schema in {2, 3}", validator)
        self.assertIn('"privacyStatus": "private"', upload)
        self.assertIn('"publishAt": publish_at', upload)
        self.assertIn("Scheduled publication contract is required", upload)
        self.assertIn("Scheduled publication contract is required", publish)
        self.assertNotIn('"mode": "public"', upload)
        self.assertNotIn('"verified_private"', verify)
        self.assertNotIn('"verified_public"', verify)
        self.assertIn('"schema_version": 3', finalize)
        self.assertIn("Only schema-v3 requests can produce receipts", finalize)
        self.assertIn("Schema v3 is the only supported production request format", overview)

        forbidden = [
            "schema " + "v2",
            "schema-" + "v2",
            "source_" + "supports_intent",
            "legacy_" + "blackdetect",
            "legacy_" + "second_pass",
            "analytics_" + "epoch",
            "migration_" + "acceptance",
        ]
        files = [
            REPO_ROOT / "README.md",
            *BOT_ROOT.rglob("*.py"),
            *BOT_ROOT.rglob("*.md"),
            *PLANNER.glob("*.md"),
            *(BOT_ROOT / "tests").glob("*.py"),
            *WORKFLOWS.glob("*.yml"),
        ]
        hits = []
        for path in files:
            if path == Path(__file__).resolve():
                continue
            text = path.read_text(encoding="utf-8").lower()
            for token in forbidden:
                if token.lower() in text:
                    hits.append(f"{path.relative_to(REPO_ROOT)}: {token}")
        self.assertFalse(hits, "compatibility/reset terminology remains: " + "; ".join(hits))

    def test_render_verification_has_no_old_metadata_fallback(self):
        source = (BOT_ROOT / "rendering/verify_render.py").read_text(encoding="utf-8")
        self.assertIn("inline_blackdetect_max", source)
        self.assertIn("canonical inline blackdetect evidence is missing or failed", source)
        self.assertNotIn("legacy_blackdetect", source)
        self.assertNotIn("legacy_second_pass", source)

    def test_planner_handoff_matches_daily_production(self):
        prompt = (PLANNER / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        batch = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        for token in (
            "planning/planning_engine.py",
            "analytics_evidence_count",
            "daily-production.yml",
            "[daily production]",
            "`plan_date`",
            "`planning_mode`",
            "`final_selected`",
            "`content_ids`",
            "`logical_id`",
            "`required_by_content_ids`",
        ):
            self.assertIn(token, prompt)
        self.assertIn("name: Daily Production", batch)
        self.assertIn("contains(github.event.head_commit.message, '[daily production]')", batch)
        self.assertIn("payload.get('content_ids')", batch)
        self.assertIn("payload.get('final_selected')", batch)

    def test_execution_chain_uses_current_components(self):
        batch = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        for token in (
            "validation/validate_content.py",
            "publishing/auth_preflight.py",
            "media/media_resolver.py",
            "rendering/render_aligned.py",
            "rendering/verify_render.py",
            "publishing/publish.py --stage upload",
            "publishing/verify_publication.py",
            "publishing/finalize_receipt.py",
        ):
            self.assertIn(token, batch)

        analytics = (WORKFLOWS / "analytics-collection.yml").read_text(encoding="utf-8")
        backgrounds = (WORKFLOWS / "background-management.yml").read_text(encoding="utf-8")
        image = (WORKFLOWS / "build-image.yml").read_text(encoding="utf-8")
        self.assertIn("analytics/analytics_collection.py", analytics)
        self.assertIn("media/pexels_registry.py", backgrounds)
        self.assertIn("media/validate_media_library.py", backgrounds)
        self.assertIn("youtube-shorts-bot/Dockerfile", image)

    def test_analytics_contract_is_current_and_consistent(self):
        prompt = (PLANNER / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        collector = (BOT_ROOT / "analytics/analytics_collection.py").read_text(encoding="utf-8")
        learning = (BOT_ROOT / "analytics/analytics_learning.py").read_text(encoding="utf-8")
        model = (BOT_ROOT / "analytics" / "model.json").read_text(encoding="utf-8")
        for text in (prompt, collector, learning):
            self.assertIn("analytics_evidence_count", text)
        self.assertIn('"model_version": 1', model)
        self.assertNotIn("analytics_epoch", collector)
        self.assertNotIn("epoch.json", collector)
        self.assertIn(
            "Do not substitute `video_count`, `published_video_count`, or `mature_video_count`",
            prompt,
        )


if __name__ == "__main__":
    unittest.main()
