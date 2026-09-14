import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
PLANNER = BOT_ROOT / "planning"
ARCH_TERM = "gro" + "wth"


def canonical_planner_text(prefix):
    return (PLANNER / f"{prefix}_PLANNER_PROMPT.md").read_text(encoding="utf-8") + "\n" + (PLANNER / f"{prefix}_PLANNER_RULES.md").read_text(encoding="utf-8")


class ArchitectureContractTests(unittest.TestCase):
    def test_supported_surface_has_required_workflows_and_no_retired_paths(self):
        actual = {path.name for path in WORKFLOWS.glob("*.yml")}
        required = {"adhoc-production.yml", "analytics-collection.yml", "automatic-recovery.yml", "background-management.yml", "daily-production.yml", "dry-run.yml"}
        self.assertTrue(required <= actual, f"missing workflows: {sorted(required - actual)}")
        self.assertFalse({"build-image.yml", "pipeline-validation.yml", "background-library.yml", "planner-execution.yml", "adhoc-request-dispatch.yml"} & actual)
        self.assertFalse((PLANNER / "execution_bridge.py").exists())
        for name in ("ranked_promotion.py", "pool_admission.py", "planner_core.py", "planner_precommit.py", "planner_profiles.py"):
            self.assertTrue((PLANNER / name).is_file())

    def test_growth_is_business_language_not_technical_architecture(self):
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")
        self.assertIn("subscriber and qualified-view " + ARCH_TERM, overview)
        self.assertIn("1,000 subscribers", overview)
        self.assertIn("10 million qualified public Shorts views", overview)

    def test_private_request_contract_is_schema_v7_with_v4_v5_v6_recovery(self):
        validator = (BOT_ROOT / "validation/validate_content.py").read_text(encoding="utf-8")
        continuous = (BOT_ROOT / "media/continuous_background.py").read_text(encoding="utf-8")
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")
        self.assertIn("SCHEMA_VERSION = 7", validator)
        self.assertIn("SUPPORTED_SCHEMA_VERSIONS = {4, 5, 6, 7}", validator)
        self.assertIn('CONCATENATED_FIT_TO_SHORT_MODE = "concatenated_fit_to_short"', continuous)
        self.assertIn('FIT_TO_SHORT_MODE = "fit_to_short"', continuous)
        self.assertIn('"background_primary_sequence"', validator)
        self.assertIn('"background_backup_sequence"', validator)
        self.assertIn("validate_background_registry_contract", validator)
        self.assertIn("is_selectable", validator)
        self.assertIn("Schema v7 is current", overview)
        for version in (6, 5, 4):
            self.assertIn(f"Schema v{version} remains executable", overview)

    def test_ad_hoc_prompt_uses_ranked_pool_immediate_public_path(self):
        planner = canonical_planner_text("ADHOC")
        profiles = (PLANNER / "planner_profiles.py").read_text(encoding="utf-8")
        adhoc = (WORKFLOWS / "adhoc-production.yml").read_text(encoding="utf-8")
        promotion = (PLANNER / "ranked_promotion.py").read_text(encoding="utf-8")
        self.assertIn("exactly **5**", planner)
        self.assertIn("immediate public", planner)
        for token in ("pool_size=5", "fixed_target_count=1", "scheduled_daily", "manual_on_demand"):
            self.assertIn(token, profiles)
        for token in ("planning-pools/adhoc", "planning.pool_admission adhoc", "planning.ranked_promotion adhoc", "planning.ranked_promotion verify-adhoc", "actions/workflows/single.yml/dispatches"):
            self.assertIn(token, adhoc)
        self.assertIn("verify_scheduled_adhoc_uniqueness", promotion)

    def test_heavy_execution_modules_are_public_only(self):
        for path in (BOT_ROOT / "media/media_resolver.py", BOT_ROOT / "publishing/auth_preflight.py", BOT_ROOT / "publishing/finalize_receipt.py", BOT_ROOT / "publishing/publish.py", BOT_ROOT / "publishing/verify_publication.py", BOT_ROOT / "Dockerfile", BOT_ROOT / "requirements.txt", WORKFLOWS / "build-image.yml"):
            self.assertFalse(path.exists(), f"obsolete private runtime copy remains: {path}")

    def test_planner_handoff_matches_daily_ranked_promotion(self):
        planner = canonical_planner_text("DAILY")
        batch = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        profiles = (PLANNER / "planner_profiles.py").read_text(encoding="utf-8")
        core = (PLANNER / "planner_core.py").read_text(encoding="utf-8")
        self.assertTrue((PLANNER / "planning_engine.py").is_file())
        self.assertIn("content/planning-pools/daily/YYYY-MM-DD/dp-<attempt-id>.json", planner)
        self.assertIn("chatgpt_ranked_pool", core)
        for token in ("planning.pool_admission daily", "planning.ranked_promotion daily", "actions/workflows/run.yml/dispatches", "python -m common.runtime_contract"):
            self.assertIn(token, batch)
        self.assertIn("pool_size=36", profiles)
        self.assertIn("normal_target_count=24", profiles)

    def test_docs_match_current_runtime_ownership_and_media_contract(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        overview = (BOT_ROOT / "docs" / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")
        recovery = (BOT_ROOT / "docs" / "RECOVERY.md").read_text(encoding="utf-8")
        runtime_map = (REPO_ROOT / "docs" / "private" / "runtime-map.md").read_text(encoding="utf-8")
        self.assertIn("public `production-runtime` repository owns", readme)
        self.assertIn("Schema v7 is current", overview)
        self.assertIn("Schema v7 is current", recovery)
        self.assertIn("historical immutable recovery", recovery)
        for text in (readme, overview, recovery, runtime_map):
            self.assertNotIn("720×1280", text)
            self.assertNotIn("720x1280", text)
        self.assertIn("1080×1920", overview)

    def test_execution_chain_uses_current_components(self):
        batch = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        self.assertIn("actions/workflows/run.yml/dispatches", batch)
        for token in ("media/media_resolver.py", "rendering/render_aligned.py", "publishing/verify_publication.py", "publishing/finalize_receipt.py"):
            self.assertNotIn(token, batch)

    def test_analytics_contract_is_current_and_consistent(self):
        runner = (PLANNER / "planning_runner.py").read_text(encoding="utf-8")
        collector = (BOT_ROOT / "analytics/analytics_collection.py").read_text(encoding="utf-8")
        learning = (BOT_ROOT / "analytics/analytics_learning.py").read_text(encoding="utf-8")
        self.assertIn("analytics_evidence_count", runner)
        self.assertIn("analytics_evidence_count", learning)
        self.assertIn("SUPPORTED_RECEIPT_SCHEMA_VERSIONS = {3, 4, 5, 6, 7}", collector)
        self.assertNotIn("analytics_epoch", collector)


if __name__ == "__main__":
    unittest.main()
