import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
PLANNER = BOT_ROOT / "planning"
ARCH_TERM = "gro" + "wth"


class ArchitectureContractTests(unittest.TestCase):
    def test_supported_surface_has_required_workflows_and_no_retired_paths(self):
        actual = {path.name for path in WORKFLOWS.glob("*.yml")}
        required = {
            "adhoc-production.yml",
            "analytics-collection.yml",
            "automatic-recovery.yml",
            "background-management.yml",
            "daily-production.yml",
            "dry-run.yml",
        }
        self.assertTrue(
            required <= actual, f"missing workflows: {sorted(required - actual)}"
        )
        self.assertFalse(
            {
                "build-image.yml",
                "pipeline-validation.yml",
                "background-library.yml",
                "planner-execution.yml",
                "adhoc-request-dispatch.yml",
            }
            & actual
        )
        self.assertEqual(
            {path.name for path in PLANNER.glob("*.md")},
            {
                "ADHOC_PLANNER_PROMPT.md",
                "DAILY_PLANNER_PROMPT.md",
                "STORY_RULES.md",
            },
        )
        self.assertFalse((PLANNER / "execution_bridge.py").exists())
        self.assertTrue((PLANNER / "ranked_promotion.py").is_file())
        self.assertFalse((BOT_ROOT / "docs/DAILY_PLANNER_V4_BASE.md").exists())
        self.assertFalse((BOT_ROOT / "docs/ADHOC_PLANNER_V4_BASE.md").exists())

    def test_growth_is_business_language_not_technical_architecture(self):
        path_hits = []
        for root in (BOT_ROOT, WORKFLOWS):
            for path in root.rglob("*"):
                if path.is_file() and ARCH_TERM in path.name.lower():
                    path_hits.append(str(path.relative_to(REPO_ROOT)))
        self.assertFalse(
            path_hits, "architecture term remains in filenames: " + "; ".join(path_hits)
        )

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
        self.assertFalse(
            code_hits, "architecture term remains in code: " + "; ".join(code_hits)
        )

        prompt = (PLANNER / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(
            encoding="utf-8"
        )
        for text in (prompt, overview):
            self.assertIn("subscriber and qualified-view " + ARCH_TERM, text)
            self.assertIn("1,000 subscribers", text)
            self.assertIn("10 million qualified public Shorts views", text)
        self.assertIn("business objective", overview.lower())

    def test_private_request_contract_is_schema_v5_with_v4_compatibility(self):
        validator = (BOT_ROOT / "validation/validate_content.py").read_text(
            encoding="utf-8"
        )
        legacy_validator = (BOT_ROOT / "validation/schema_v4.py").read_text(
            encoding="utf-8"
        )
        semantic = (BOT_ROOT / "validation/semantic.py").read_text(encoding="utf-8")
        upload = (BOT_ROOT / "publishing/upload.py").read_text(encoding="utf-8")
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("SCHEMA_VERSION = 5", validator)
        self.assertIn("SUPPORTED_SCHEMA_VERSIONS = {4, 5}", validator)
        self.assertIn('"background_primary_treatment"', validator)
        self.assertIn('"background_backup_treatment"', validator)
        self.assertIn('"segment_start_seconds"', validator)
        self.assertIn('"segment_duration_seconds"', validator)
        self.assertIn('"playback_rate"', validator)
        self.assertIn("math.isfinite", validator)
        self.assertIn("source duration is unknown", validator)
        self.assertIn("validate_background_registry_contract", validator)
        self.assertIn("production-suitable rendition", validator)
        self.assertIn('"punchline"', legacy_validator)
        self.assertIn("validate_punchline", legacy_validator)
        self.assertIn('"REVERSAL"', semantic)
        self.assertIn("MAX_EMPHASIS_WORDS = 5", semantic)
        self.assertNotIn("YOUTUBE_KEYS_V2", validator)
        self.assertNotIn("schema in {2, 3}", validator)
        self.assertIn('mode not in {"scheduled", "immediate"}', legacy_validator)
        self.assertIn(
            '"privacyStatus": "public" if mode == "immediate" else "private"',
            upload,
        )
        self.assertIn('status["publishAt"] = publish_at', upload)
        self.assertIn("Publication contract is required", upload)
        self.assertIn("Immediate publication requires publish_at=null", upload)
        self.assertNotIn('\"mode\": \"public\"', upload)
        self.assertIn("Schema v5", overview)
        self.assertIn("current", overview.lower())
        self.assertIn("Schema v4 remains executable", overview)

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
        self.assertFalse(
            hits, "compatibility/reset terminology remains: " + "; ".join(hits)
        )

    def test_ad_hoc_prompt_uses_ranked_pool_immediate_public_path(self):
        prompt = (PLANNER / "ADHOC_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        adhoc = (WORKFLOWS / "adhoc-production.yml").read_text(encoding="utf-8")
        promotion = (PLANNER / "ranked_promotion.py").read_text(encoding="utf-8")
        self.assertIn('"mode": "immediate"', prompt)
        self.assertIn('"publish_at": null', prompt)
        self.assertIn("privacyStatus: public", prompt)
        self.assertIn("exactly **5**", prompt)
        self.assertIn("scheduled_daily", prompt)
        self.assertIn("manual_on_demand", prompt)
        self.assertIn("[adhoc pool]", prompt)
        self.assertIn("planning-pools/adhoc", adhoc)
        self.assertIn("planning.ranked_promotion adhoc", adhoc)
        self.assertIn("planning.ranked_promotion verify-adhoc", adhoc)
        self.assertIn("private-adhoc-production-${{ github.ref }}", adhoc)
        self.assertIn("verify_scheduled_adhoc_uniqueness", promotion)
        self.assertIn("actions/workflows/single.yml/dispatches", adhoc)

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
            self.assertFalse(
                path.exists(), f"obsolete private runtime copy remains: {path}"
            )

    def test_planner_handoff_matches_daily_ranked_promotion(self):
        prompt = (PLANNER / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        batch = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        promotion = (PLANNER / "ranked_promotion.py").read_text(encoding="utf-8")

        for token in (
            "planning/planning_engine.py",
            "analytics_evidence_count",
            "daily-production.yml",
            "[daily pool] YYYY-MM-DD",
            "content/planning-pools/daily/YYYY-MM-DD/dp-<attempt-id>.json",
            "exactly 36",
            "first `target_count` candidates",
            "new immutable attempt",
            "chatgpt_ranked_pool",
        ):
            self.assertIn(token, prompt)
        self.assertIn("name: Daily Production", batch)
        self.assertIn("contains(github.event.head_commit.message, '[daily pool]')", batch)
        self.assertIn("planning-pools/daily/**/*.json", batch)
        self.assertIn("planning.ranked_promotion daily", batch)
        self.assertIn("Validate rebased canonical Daily production commit", batch)
        self.assertIn("Publish validated Daily production state", batch)
        self.assertLess(
            batch.index("python -m validation.planning_audit"),
            batch.index("Publish validated Daily production state"),
        )
        self.assertIn("actions/workflows/run.yml/dispatches", batch)
        self.assertIn("python -m common.runtime_contract", batch)
        self.assertIn("DAILY_POOL_SIZE = 36", promotion)
        self.assertIn("NORMAL_DAILY_TARGET = 24", promotion)
        self.assertIn("CATCH_UP_MIN_LEAD_MINUTES = 30", promotion)
        self.assertIn("'batch_id': os.environ['BATCH_ID']", batch)
        self.assertIn("'source_sha': os.environ['SOURCE_SHA']", batch)
        self.assertIn("'contract_hash': os.environ['CONTRACT_HASH']", batch)

    def test_execution_chain_uses_current_components(self):
        batch = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        self.assertIn("actions/workflows/run.yml/dispatches", batch)
        for token in (
            "media/media_resolver.py",
            "rendering/render_aligned.py",
            "publishing/verify_publication.py",
            "publishing/finalize_receipt.py",
        ):
            self.assertNotIn(token, batch)

        analytics = (WORKFLOWS / "analytics-collection.yml").read_text(
            encoding="utf-8"
        )
        backgrounds = (WORKFLOWS / "background-management.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("analytics/analytics_collection.py", analytics)
        self.assertIn("media/pexels_registry.py", backgrounds)
        self.assertIn("media/validate_media_library.py", backgrounds)
        self.assertFalse((WORKFLOWS / "build-image.yml").exists())
        self.assertFalse((BOT_ROOT / "Dockerfile").exists())
        self.assertFalse((BOT_ROOT / "requirements.txt").exists())

    def test_docs_match_current_runtime_ownership_and_media_contract(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(
            encoding="utf-8"
        )
        recovery = (BOT_ROOT / "docs" / "RECOVERY.md").read_text(encoding="utf-8")
        runtime_map = (REPO_ROOT / "docs" / "private" / "runtime-map.md").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("`build-image.yml`", readme)
        self.assertNotIn("`youtube-shorts-bot/Dockerfile`", readme)
        self.assertIn("public `production-runtime` repository owns", readme)
        self.assertIn("Schema v5", overview)
        self.assertIn("current", overview.lower())
        self.assertIn("schema-v5 daily path", recovery)
        for text in (readme, overview, recovery, runtime_map):
            self.assertNotIn("720×1280", text)
            self.assertNotIn("720x1280", text)
        self.assertIn("1080×1920", readme)
        self.assertIn("1080×1920", overview)
        self.assertIn("1080×1920", recovery)
        self.assertIn("1080x1920", runtime_map)

    def test_analytics_contract_is_current_and_consistent(self):
        prompt = (PLANNER / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        collector = (BOT_ROOT / "analytics/analytics_collection.py").read_text(
            encoding="utf-8"
        )
        learning = (BOT_ROOT / "analytics/analytics_learning.py").read_text(
            encoding="utf-8"
        )
        model = (BOT_ROOT / "analytics" / "model.json").read_text(encoding="utf-8")
        for text in (prompt, collector, learning):
            self.assertIn("analytics_evidence_count", text)
        self.assertIn('\"model_version\": 1', model)
        self.assertIn("SUPPORTED_RECEIPT_SCHEMA_VERSIONS = {3, 4, 5}", collector)
        self.assertIn('in {"scheduled", "immediate"}', collector)
        self.assertNotIn("analytics_epoch", collector)
        self.assertNotIn("epoch.json", collector)
        lower_prompt = prompt.lower()
        self.assertIn("do not substitute", lower_prompt)
        for token in ("video_count", "published_video_count", "mature_video_count"):
            self.assertIn(token, prompt)


if __name__ == "__main__":
    unittest.main()
