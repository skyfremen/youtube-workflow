import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOT = ROOT / "youtube-shorts-bot"


class StaticCleanupAudit(unittest.TestCase):
    def test_report_cleanup_candidates(self):
        production = sorted(BOT.glob("*.py"))
        text_paths = [
            *production,
            *(BOT / "tests").glob("*.py"),
            *(BOT / "planner").glob("*.md"),
            *BOT.glob("*.md"),
            *(ROOT / ".github" / "workflows").glob("*.yml"),
        ]
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in text_paths)

        for path in production:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            used_names = {
                node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
            }
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    count = len(re.findall(rf"\b{re.escape(node.name)}\b", corpus))
                    if count <= 1:
                        print(f"ORPHAN_SYMBOL_CANDIDATE {path.name}:{node.lineno} {node.name} refs={count}")
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        local = alias.asname or alias.name.split(".")[0]
                        if local not in used_names:
                            print(f"UNUSED_IMPORT_CANDIDATE {path.name}:{node.lineno} {local}")

        suspect_fragments = (
            "compatib",
            "deprecated",
            "migration",
            "legacy",
            "fresh-start",
            "pre-launch",
            "prelaunch",
            "adhoc",
            "ad-hoc",
            "unscheduled",
            "old ",
            "todo",
            "fixme",
        )
        for path in text_paths:
            if path == Path(__file__).resolve():
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                lower = line.lower()
                if any(fragment in lower for fragment in suspect_fragments):
                    print(f"STALE_TERM_CANDIDATE {path.relative_to(ROOT)}:{line_no} {line.strip()}")

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
