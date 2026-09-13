import json
import unittest
from pathlib import Path

from planning import adhoc_precommit, daily_precommit
from planning.planner_contract import build_contract
from planning.planner_profiles import (
    ADHOC,
    DAILY,
    PlannerProfile,
    assert_profiles_do_not_override_shared_contract,
)


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent
MANIFEST = BOT_ROOT / "planning" / "PLANNER_MATERIALIZATION.json"


class SharedPlannerArchitectureTests(unittest.TestCase):
    def test_daily_and_adhoc_share_one_contract_fingerprint(self):
        contract = build_contract()
        profiles = contract["profiles"]
        self.assertEqual(
            profiles["daily"]["shared_contract_fingerprint"],
            profiles["adhoc"]["shared_contract_fingerprint"],
        )
        self.assertEqual(
            profiles["daily"]["shared_contract_fingerprint"],
            contract["shared_contract_fingerprint"],
        )
        self.assertEqual(contract["shared_implementation"]["precommit"], "planning.planner_precommit")
        self.assertEqual(contract["shared_implementation"]["drift_classification"], "planning.planner_drift")

    def test_profiles_cannot_own_shared_validation_contracts(self):
        self.assertTrue(assert_profiles_do_not_override_shared_contract())
        fields = set(PlannerProfile.__dataclass_fields__)
        for forbidden in (
            "schema", "semantic", "background", "voice", "narration",
            "punchline", "media_readiness", "request_validator",
        ):
            self.assertFalse(
                any(forbidden in field for field in fields),
                f"shared contract leaked into profile field containing {forbidden}",
            )

    def test_profiles_contain_only_expected_mode_differences(self):
        self.assertEqual(DAILY.pool_size, 36)
        self.assertEqual(ADHOC.pool_size, 5)
        self.assertEqual(DAILY.publication_template["mode"], "scheduled")
        self.assertEqual(ADHOC.publication_template["mode"], "immediate")
        self.assertEqual(ADHOC.fixed_target_count, 1)
        self.assertEqual(DAILY.normal_target_count, 24)

    def test_legacy_precommit_modules_are_thin_shared_engine_wrappers(self):
        self.assertEqual(daily_precommit.SHARED_ENGINE_MODULE, "planning.planner_precommit")
        self.assertEqual(adhoc_precommit.SHARED_ENGINE_MODULE, "planning.planner_precommit")
        self.assertEqual(daily_precommit.PROFILE, "daily")
        self.assertEqual(adhoc_precommit.PROFILE, "adhoc")

    def test_connector_fallback_excludes_downstream_modules(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        shared = set(manifest["shared_required_python_files"])
        self.assertEqual(manifest["materialization_mode"], "shared_plus_selected_profile")
        self.assertEqual(len(shared), 19)
        self.assertIn("youtube-shorts-bot/planning/materialization_verify.py", shared)
        self.assertIn("youtube-shorts-bot/planning/planner_contract_base.py", shared)
        self.assertIn("youtube-shorts-bot/media/continuous_background.py", shared)
        self.assertIn("youtube-shorts-bot/validation/validate_content_v5.py", shared)
        self.assertNotIn("youtube-shorts-bot/planning/ranked_promotion.py", shared)
        self.assertNotIn("youtube-shorts-bot/publishing/upload.py", shared)
        self.assertNotIn("youtube-shorts-bot/planning/daily_precommit.py", shared)
        self.assertNotIn("youtube-shorts-bot/planning/adhoc_precommit.py", shared)
        self.assertFalse(any(path.endswith("/__init__.py") for path in shared))
        for profile in ("daily", "adhoc"):
            entry = manifest["profile_required_files"][profile]
            self.assertEqual(entry["python_files"], [])
            self.assertEqual(entry["data_files"], [])

    def test_git_is_preferred_without_becoming_a_hard_dependency(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["planner_bootstrap"]["preferred"], "git")
        self.assertEqual(manifest["planner_bootstrap"]["fallback"], "connector_materialization")
        self.assertTrue(manifest["git_checkout"]["preferred"])
        self.assertFalse(manifest["git_required"])
        self.assertFalse(manifest["git_executable_required"])
        self.assertFalse(manifest["checkout_required"])
        self.assertIn("GitHub Actions planner execution", manifest["forbidden_bootstrap_requirements"])
        self.assertIn("synthetic HEAD", manifest["forbidden_bootstrap_requirements"])
        self.assertFalse(manifest["immutable_cache"]["correctness_dependency"])

    def test_shared_prompt_is_canonical_for_bootstrap(self):
        shared = (REPO_ROOT / "docs" / "private" / "PLANNER_PROMPT.md").read_text(encoding="utf-8")
        daily = (BOT_ROOT / "planning" / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        adhoc = (BOT_ROOT / "planning" / "ADHOC_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("one planner", shared.lower())
        self.assertIn("planning.planner_precommit", shared)
        self.assertIn("planning.planner_drift", shared)
        self.assertIn("docs/private/PLANNER_PROMPT.md", daily)
        self.assertIn("docs/private/PLANNER_PROMPT.md", adhoc)
        self.assertIn("--profile daily", daily)
        self.assertIn("--profile adhoc", adhoc)

    def test_replenishment_visual_review_is_transport_adaptive(self):
        shared = (REPO_ROOT / "docs" / "private" / "PLANNER_PROMPT.md").read_text(encoding="utf-8")
        strategy = (BOT_ROOT / "docs" / "background-media-strategy.md").read_text(encoding="utf-8")
        daily = (BOT_ROOT / "planning" / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        adhoc = (BOT_ROOT / "planning" / "ADHOC_PLANNER_PROMPT.md").read_text(encoding="utf-8")

        # GitHub may transport exact Pexels pixels, but ChatGPT/Work still owns the
        # visual/editorial decision. Local direct transport remains a fallback.
        self.assertIn("private Background Management artifact", shared)
        self.assertIn("Connector-delivered artifact files", shared)
        self.assertIn("ChatGPT/Work remains the sole visual/editorial approval owner", shared)
        self.assertIn("preview_review_materializer --input-dir", shared)
        self.assertIn("EVIDENCE_ACCESS_BLOCKED", shared)
        self.assertIn("REVIEW_EVIDENCE_TRANSPORT_FAILED", shared)
        self.assertIn("DEFERRED_REPLENISHMENT", shared)

        self.assertIn("private Background Management review-evidence artifact", strategy)
        self.assertIn("GitHub connector delivery", strategy)
        self.assertIn("contact-sheet.jpg", strategy)
        self.assertIn("--input-dir", strategy)
        self.assertIn("EVIDENCE_ACCESS_BLOCKED", strategy)
        self.assertIn("REVIEW_EVIDENCE_TRANSPORT_FAILED", strategy)
        self.assertIn("GitHub Actions must never set `verified_preview`", strategy)

        for profile_prompt in (daily, adhoc):
            self.assertIn("matching immutable discovery result exists", profile_prompt)
            self.assertIn("run-scoped", profile_prompt)
            self.assertIn("background-review-evidence-", profile_prompt)
            self.assertIn("contact-sheet.jpg", profile_prompt)
            self.assertIn("--input-dir", profile_prompt)
            self.assertIn("same planner invocation", profile_prompt)
            self.assertIn("EVIDENCE_ACCESS_BLOCKED", profile_prompt)
            self.assertIn("REVIEW_EVIDENCE_TRANSPORT_FAILED", profile_prompt)
            self.assertIn("ChatGPT/Work owns approval and semantic metadata", profile_prompt)


if __name__ == "__main__":
    unittest.main()
