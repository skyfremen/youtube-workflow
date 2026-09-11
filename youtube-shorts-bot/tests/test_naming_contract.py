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
                "adhoc-production.yml",
                "analytics-collection.yml",
                "automatic-recovery.yml",
                "background-management.yml",
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

    def test_private_request_contract_is_v4_with_v3_recovery(self):
        validator = (BOT_ROOT / "validation/validate_content.py").read_text(encoding="utf-8")
        upload = (BOT_ROOT / "publishing/upload.py").read_text(encoding="utf-8")
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")

        self.assertIn("SCHEMA_VERSION = 4", validator)
        self.assertIn("SUPPORTED_SCHEMA_VERSIONS = {3, 4}", validator)
        self.assertNotIn("YOUTUBE_KEYS_V2", validator)
        self.assertNotIn("schema in {2, 3}", validator)
        self.assertIn('\"privacyStatus\": \"private\"', upload)
        self.assertIn('\"publishAt\": publish_at', upload)
        self.assertIn("Scheduled publication contract is required", upload)
        self.assertNotIn('\"mode\": \"public\"', upload)
        self.assertIn("Schema v4 is the current production request format", overview)

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

    def test_heavy_execution_modules_are_public_only(self):
        paths = [
            BOT_ROOT / "media/media_resolver.py",
            BOT_ROOT / "publishing/auth_preflight.py",
            BOT_ROOT / "publishing/finalize_receipt.py",
            BOT_ROOT / "publishing/publish.py",
            BOT_ROOT / "publishing/verify_publication.py",
            BOT_ROOT / "Dockerfile",
            BOT_ROOT / "requirements.txt",
            WORKFLOWS / "build-image.yml",
        ]
        paths.extend((BOT_ROOT / "production").glob("*.py"))
        paths.extend((BOT_ROOT / "rendering").glob("*.py"))
        for path in paths:
            self.assertFalse(path.exists(), f"obsolete private runtime copy remains: {path}")

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
        self.assertIn("actions/workflows/run.yml/dispatches", batch)
        self.assertIn("python -m common.runtime_contract", batch)
        self.assertIn("'batch_id': os.environ['BATCH_ID']", batch)
        self.assertIn("'source_sha': os.environ['SOURCE_SHA']", batch)
        self.assertIn("'contract_hash': os.environ['CONTRACT_HASH']", batch)

    def test_execution_chain_uses_current_components(self):
        batch = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        self.assertIn("actions/workflows/run.yml/dispatches", batch)
        for token in (
            "media/media_resolver.py", "rendering/render_aligned.py",
            "publishing/verify_publication.py", "publishing/finalize_receipt.py",
        ):
            self.assertNotIn(token, batch)

        analytics = (WORKFLOWS / "analytics-collection.yml").read_text(encoding="utf-8")
        backgrounds = (WORKFLOWS / "background-management.yml").read_text(encoding="utf-8")
        self.assertIn("analytics/analytics_collection.py", analytics)
        self.assertIn("media/pexels_registry.py", backgrounds)
        self.assertIn("media/validate_media_library.py", backgrounds)
        self.assertFalse((WORKFLOWS / "build-image.yml").exists())
        self.assertFalse((BOT_ROOT / "Dockerfile").exists())
        self.assertFalse((BOT_ROOT / "requirements.txt").exists())

    def test_docs_match_current_runtime_ownership_and_media_contract(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")
        recovery = (BOT_ROOT / "docs" / "RECOVERY.md").read_text(encoding="utf-8")
        runtime_map = (REPO_ROOT / "docs" / "private" / "runtime-map.md").read_text(encoding="utf-8")

        self.assertNotIn("`build-image.yml`", readme)
        self.assertNotIn("`youtube-shorts-bot/Dockerfile`", readme)
        self.assertIn("public `production-runtime` repository owns", readme)
        self.assertIn("Schema v4 is the current production request format", overview)
        self.assertIn("schema-v4 daily path", recovery)
        for text in (readme, overview, recovery, runtime_map):
            self.assertNotIn("720×1280", text)
            self.assertNotIn("720x1280", text)
        self.assertIn("1080×1920", readme)
        self.assertIn("1080×1920", overview)
        self.assertIn("1080×1920", recovery)
        self.assertIn("1080x1920", runtime_map)

    def test_analytics_contract_is_current_and_consistent(self):
        prompt = (PLANNER / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        collector = (BOT_ROOT / "analytics/analytics_collection.py").read_text(encoding="utf-8")
        learning = (BOT_ROOT / "analytics/analytics_learning.py").read_text(encoding="utf-8")
        model = (BOT_ROOT / "analytics" / "model.json").read_text(encoding="utf-8")
        for text in (prompt, collector, learning):
            self.assertIn("analytics_evidence_count", text)
        self.assertIn('\"model_version\": 1', model)
        self.assertIn("SUPPORTED_RECEIPT_SCHEMA_VERSIONS = {3, 4}", collector)
        self.assertNotIn("analytics_epoch", collector)
        self.assertNotIn("epoch.json", collector)
        self.assertIn(
            "Do not substitute `video_count`, `published_video_count`, or `mature_video_count`",
            prompt,
        )


if __name__ == "__main__":
    unittest.main()
