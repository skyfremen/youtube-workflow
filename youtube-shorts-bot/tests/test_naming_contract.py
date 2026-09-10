import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


class NamingContractTests(unittest.TestCase):
    def active_text_files(self):
        files = [REPO_ROOT / "README.md"]
        files += list(BOT_ROOT.glob("*.py"))
        files += list(BOT_ROOT.glob("*.md"))
        files += list((BOT_ROOT / "planner").glob("*.md"))
        files += list((BOT_ROOT / "tests").glob("*.py"))
        files += list(WORKFLOWS.glob("*.yml"))
        return [path for path in files if path.is_file()]

    def test_no_stale_pre_refactor_identifiers_remain(self):
        # Build retired tokens in pieces so this test does not match itself.
        retired = [
            "DAILY_" + "GROWTH_PROMPT.md",
            "daily-" + "growth-batch.yml",
            "growth_" + "planner.py",
            "growth_" + "config.py",
            "youtube-" + "shorts-dry-run.yml",
            "build-" + "shorts-image.yml",
            "background-" + "library-renditions.yml",
            "youtube-" + "analytics.yml",
            "adhoc-" + "story-private.yml",
            "verify_" + "youtube_private.py",
            "auth_" + "check.py",
            "[daily " + "growth]",
            "Daily " + "Growth Batch",
            "daily-" + "growth",
            "private/" + "unscheduled path",
            "private-" + "upload policy",
        ]
        hits = []
        for path in self.active_text_files():
            if path == Path(__file__).resolve():
                continue
            text = path.read_text(encoding="utf-8")
            for token in retired:
                if token in text:
                    hits.append(f"{path.relative_to(REPO_ROOT)}: {token}")
        self.assertFalse(hits, "stale pre-refactor naming remains: " + "; ".join(hits))

    def test_planner_handoff_matches_current_contract(self):
        prompt = (BOT_ROOT / "planner" / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("planning_engine.py", prompt)
        self.assertIn("analytics_evidence_count", prompt)
        self.assertIn("daily-production.yml", prompt)
        self.assertIn("[daily production]", prompt)

    def test_single_story_contract_is_immediate_public(self):
        rules = (BOT_ROOT / "planner" / "STORY_RULES.md").read_text(encoding="utf-8")
        prompt = (BOT_ROOT / "planner" / "SINGLE_STORY_PROMPT.md").read_text(encoding="utf-8")
        workflow = (WORKFLOWS / "single-production.yml").read_text(encoding="utf-8")
        self.assertIn("immediate-public", rules)
        self.assertIn("immediate-public upload policy", prompt)
        self.assertIn("YOUTUBE_PRIVACY: public", workflow)


if __name__ == "__main__":
    unittest.main()
