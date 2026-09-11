import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from planning.planning_engine import build_acceptance_fixture, evaluate, filter_candidates
from planning.planning_runner import execute


class PlanningRunnerTests(unittest.TestCase):
    def test_raw_stage_returns_actual_canonical_filter_output(self):
        raw, _ = build_acceptance_fixture("2026-09-10")
        expected, rejected = filter_candidates(raw)
        envelope = execute("raw-filter", {"raw_candidates": raw, "recent": []})
        result = envelope["result"]

        self.assertEqual(
            [item["candidate_id"] for item in result["qualified_candidates"]],
            [item["candidate_id"] for item in expected],
        )
        self.assertEqual(result["hard_rejected"], len(rejected))
        self.assertEqual(
            envelope["execution"]["entry_points"],
            ["planning.planning_engine.filter_candidates"],
        )
        self.assertEqual(len(envelope["execution"]["implementation_sha256"]), 64)
        self.assertEqual(len(envelope["execution"]["input_sha256"]), 64)

    def test_final_stage_returns_actual_canonical_evaluate_output(self):
        raw, semifinalists = build_acceptance_fixture("2026-09-10")
        payload = {
            "raw_candidates": raw,
            "semifinalists": semifinalists,
            "plan_date": "2026-09-10",
            "recent": [],
            "analytics_evidence_count": 0,
        }
        envelope = execute("final-select", payload)
        expected = evaluate(
            raw, semifinalists, "2026-09-10", analytics_video_count=0, recent=[]
        )
        actual = envelope["result"]

        self.assertEqual(actual["final_selected"], expected["final_selected"])
        self.assertEqual(
            [item["candidate_id"] for item in actual["selected"]],
            [item["candidate_id"] for item in expected["selected"]],
        )
        self.assertEqual(
            [item["final_score"] for item in actual["selected"]],
            [item["final_score"] for item in expected["selected"]],
        )
        self.assertIn(
            "planning.planning_engine.evaluate",
            envelope["execution"]["entry_points"],
        )

    def test_positive_analytics_evidence_without_model_fails_closed(self):
        raw, semifinalists = build_acceptance_fixture("2026-09-10")
        with self.assertRaises(ValueError):
            execute(
                "final-select",
                {
                    "raw_candidates": raw,
                    "semifinalists": semifinalists,
                    "plan_date": "2026-09-10",
                    "analytics_evidence_count": 5,
                },
            )

    def test_cli_failure_removes_stale_output(self):
        runner = BASE / "planning" / "planning_runner.py"
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            input_path = tmp / "input.json"
            output_path = tmp / "output.json"
            input_path.write_text(json.dumps({"raw_candidates": []}), encoding="utf-8")
            output_path.write_text("stale", encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "--stage",
                    "raw-filter",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                cwd=BASE,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(output_path.exists())
            self.assertIn("failed closed", proc.stderr + proc.stdout)

    def test_prompt_requires_execution_not_equivalent_manual_arithmetic(self):
        prompt = (BASE / "planning" / "DAILY_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("planning/planning_runner.py", prompt)
        self.assertIn("actual returned result", prompt)
        self.assertIn("fail closed", prompt.lower())
        self.assertNotIn("or equivalent arithmetic", prompt)


if __name__ == "__main__":
    unittest.main()
