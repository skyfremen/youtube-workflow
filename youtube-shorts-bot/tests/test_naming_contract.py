import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
ARCH_TERM = "gro" + "wth"


class NamingContractTests(unittest.TestCase):
    def active_text_files(self):
        files = [REPO_ROOT / "README.md"]
        files += list(BOT_ROOT.glob("*.py"))
        files += list(BOT_ROOT.glob("*.md"))
        files += list((BOT_ROOT / "planner").glob("*.md"))
        files += list((BOT_ROOT / "tests").glob("*.py"))
        files += list(WORKFLOWS.glob("*.yml"))
        return [path for path in files if path.is_file()]

    def active_code_files(self):
        return [
            *BOT_ROOT.glob("*.py"),
            *(BOT_ROOT / "tests").glob("*.py"),
            *WORKFLOWS.glob("*.yml"),
        ]

    def active_markdown_files(self):
        return [
            REPO_ROOT / "README.md",
            *BOT_ROOT.glob("*.md"),
            *(BOT_ROOT / "planner").glob("*.md"),
        ]

    def test_no_stale_pre_refactor_identifiers_remain(self):
        retired = [
            "DAILY_" + ARCH_TERM.upper() + "_PROMPT.md",
            "daily-" + ARCH_TERM + "-batch.yml",
            ARCH_TERM + "_planner.py",
            ARCH_TERM + "_config.py",
            "youtube-shorts-dry-run.yml",
            "build-shorts-image.yml",
            "background-library-renditions.yml",
            "youtube-analytics.yml",
            "adhoc-story-private.yml",
            "verify_youtube_private.py",
            "auth_check.py",
            "[daily " + ARCH_TERM + "]",
            "Daily " + ARCH_TERM.title() + " Batch",
            "daily-" + ARCH_TERM,
            "private/unscheduled path",
            "private-upload policy",
        ]
        hits = []
        for path in self.active_text_files():
            # This test intentionally constructs retired tokens so it can forbid
            # them everywhere else without embedding the architecture term.
            if path == Path(__file__).resolve():
                continue
            text = path.read_text(encoding="utf-8")
            for token in retired:
                if token in text:
                    hits.append(f"{path.relative_to(REPO_ROOT)}: {token}")
        self.assertFalse(hits, "stale pre-refactor naming remains: " + "; ".join(hits))

    def test_architecture_term_is_absent_from_active_paths_and_code(self):
        path_hits = []
        for root in (BOT_ROOT, WORKFLOWS):
            for path in root.rglob("*"):
                if path.is_file() and ARCH_TERM in path.name.lower():
                    path_hits.append(str(path.relative_to(REPO_ROOT)))
        self.assertFalse(path_hits, "architecture term remains in active filenames: " + "; ".join(path_hits))

        source_hits = []
        for path in self.active_code_files():
            text = path.read_text(encoding="utf-8").lower()
            if ARCH_TERM in text:
                source_hits.append(str(path.relative_to(REPO_ROOT)))
        self.assertFalse(source_hits, "architecture term remains in active code/workflows: " + "; ".join(source_hits))

    def test_markdown_uses_term_only_for_business_purpose(self):
        technical_fragments = [
            ARCH_TERM + " planner",
            ARCH_TERM + " system",
            ARCH_TERM + " batch",
            ARCH_TERM + " workflow",
            ARCH_TERM + " request",
            ARCH_TERM + " receipt",
            ARCH_TERM + " schema",
            ARCH_TERM + " path",
            ARCH_TERM + " scoring",
            ARCH_TERM + " acceptance",
            ARCH_TERM + " funnel",
            "daily-" + ARCH_TERM,
            "daily " + ARCH_TERM,
            ARCH_TERM + "_",
        ]
        bad = []
        for path in self.active_markdown_files():
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                lower = line.lower()
                if ARCH_TERM not in lower:
                    continue
                if any(fragment in lower for fragment in technical_fragments):
                    bad.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
                    continue
                business_context = any(
                    marker in lower
                    for marker in ("subscriber", "qualified-view", "qualified public", "business-purpose", "business objective")
                )
                if not business_context:
                    bad.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
        self.assertFalse(bad, "term is used outside approved business-purpose language: " + "; ".join(bad))

    def test_business_objective_language_is_preserved(self):
        prompt = (BOT_ROOT / "planner" / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        overview = (BOT_ROOT / "SYSTEM_OVERVIEW.md").read_text(encoding="utf-8")
        self.assertIn("subscriber and qualified-view " + ARCH_TERM, prompt)
        self.assertIn("1,000 subscribers", prompt)
        self.assertIn("10 million qualified public Shorts views", prompt)
        self.assertIn("subscriber and qualified-view " + ARCH_TERM, overview)
        self.assertIn("business-purpose language only", overview)

    def test_planner_handoff_matches_current_contract(self):
        prompt = (BOT_ROOT / "planner" / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        batch = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        single = (WORKFLOWS / "single-production.yml").read_text(encoding="utf-8")

        for token in (
            "planning_engine.py",
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
        self.assertIn("youtube-shorts-bot/content/requests/*.json", batch)
        self.assertIn("youtube-shorts-bot/content/planning/*.json", batch)
        self.assertIn("youtube-shorts-bot/content/background-sourcing/*.json", batch)
        self.assertIn("payload.get('content_ids')", batch)
        self.assertIn("payload.get('final_selected')", batch)

        self.assertIn("name: Single Production", single)
        self.assertIn("!contains(github.event.head_commit.message, '[daily production]')", single)

    def test_execution_chain_uses_current_components(self):
        batch = (WORKFLOWS / "daily-production.yml").read_text(encoding="utf-8")
        single = (WORKFLOWS / "single-production.yml").read_text(encoding="utf-8")
        analytics = (WORKFLOWS / "analytics-collection.yml").read_text(encoding="utf-8")
        backgrounds = (WORKFLOWS / "background-management.yml").read_text(encoding="utf-8")
        image = (WORKFLOWS / "build-image.yml").read_text(encoding="utf-8")

        for token in (
            "validate_content.py",
            "auth_preflight.py",
            "media_resolver.py",
            "render_aligned.py",
            "verify_render.py",
            "publish.py --stage upload",
            "verify_publication.py",
            "finalize_receipt.py",
        ):
            self.assertIn(token, batch)

        for token in (
            "validate_content.py",
            "media_resolver.py",
            "render_aligned.py",
            "verify_render.py",
            "publish.py --stage upload",
            "verify_publication.py",
            "finalize_receipt.py",
        ):
            self.assertIn(token, single)

        self.assertIn("analytics_collection.py", analytics)
        self.assertIn("pexels_registry.py", backgrounds)
        self.assertIn("validate_media_library.py", backgrounds)
        self.assertIn("youtube-shorts-bot/Dockerfile", image)

    def test_analytics_evidence_contract_is_consistent(self):
        prompt = (BOT_ROOT / "planner" / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        collector = (BOT_ROOT / "analytics_collection.py").read_text(encoding="utf-8")
        config = (BOT_ROOT / "planning_config.py").read_text(encoding="utf-8")
        learning = (BOT_ROOT / "analytics_learning.py").read_text(encoding="utf-8")
        for text in (prompt, collector, config, learning):
            self.assertIn("analytics_evidence_count", text)
        self.assertIn("Do not substitute `video_count`, `published_video_count`, or `mature_video_count`", prompt)

    def test_single_story_contract_is_immediate_public(self):
        rules = (BOT_ROOT / "planner" / "STORY_RULES.md").read_text(encoding="utf-8")
        prompt = (BOT_ROOT / "planner" / "SINGLE_STORY_PROMPT.md").read_text(encoding="utf-8")
        workflow = (WORKFLOWS / "single-production.yml").read_text(encoding="utf-8")
        self.assertIn("immediate-public", rules)
        self.assertIn("immediate-public upload policy", prompt)
        self.assertIn("YOUTUBE_PRIVACY: public", workflow)


if __name__ == "__main__":
    unittest.main()
