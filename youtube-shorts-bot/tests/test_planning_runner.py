import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
sys.path.insert(0, str(BASE))

from planning.planning_engine import build_acceptance_fixture, evaluate, filter_candidates
from planning.planning_runner import execute


def canonical_planner_text(prefix):
    planning = BASE / "planning"
    return (
        (planning / f"{prefix}_PLANNER_PROMPT.md").read_text(encoding="utf-8")
        + "\n"
        + (planning / f"{prefix}_PLANNER_RULES.md").read_text(encoding="utf-8")
    )


class PlanningRunnerTests(unittest.TestCase):
    def _evaluation_payload(self):
        raw, semifinalists = build_acceptance_fixture("2026-09-10")
        return {
            "raw_candidates": raw,
            "semifinalists": semifinalists,
            "plan_date": "2026-09-10",
            "recent": [],
            "analytics_evidence_count": 0,
        }

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
        self.assertRegex(envelope["execution"]["source_sha"], r"^[0-9a-f]{40}$")

    def test_candidate_evaluation_scores_but_does_not_choose_winners(self):
        envelope = execute("candidate-evaluation", self._evaluation_payload())
        result = envelope["result"]
        self.assertGreater(len(result["evaluated_candidates"]), 1)
        self.assertNotIn("selected", result)
        self.assertNotIn("final_selected", result)
        self.assertIn(
            "planning.planning_engine.score_semifinalist",
            envelope["execution"]["entry_points"],
        )

    def test_chatgpt_choice_is_validated_without_substitution(self):
        evaluated = execute("candidate-evaluation", self._evaluation_payload())["result"]["evaluated_candidates"]
        chosen = [evaluated[1]["candidate_id"]]
        envelope = execute(
            "validate-selection",
            {
                "evaluated_candidates": evaluated,
                "selected_candidate_ids": chosen,
                "selection_limit": 1,
                "plan_date": "2026-09-10",
            },
        )
        result = envelope["result"]
        self.assertEqual(result["selection_owner"], "chatgpt")
        self.assertEqual(result["selected_candidate_ids"], chosen)
        self.assertEqual(
            {item["candidate_id"] for item in result["validated_selected"]},
            set(chosen),
        )
        self.assertEqual(result["final_selected"], 1)

    def test_invalid_chatgpt_choice_fails_instead_of_replacing_it(self):
        evaluated = execute("candidate-evaluation", self._evaluation_payload())["result"]["evaluated_candidates"]
        with self.assertRaises(ValueError):
            execute(
                "validate-selection",
                {
                    "evaluated_candidates": evaluated,
                    "selected_candidate_ids": ["not-an-eligible-candidate"],
                    "selection_limit": 1,
                    "plan_date": "2026-09-10",
                },
            )

    def test_legacy_final_select_remains_recovery_compatible(self):
        payload = self._evaluation_payload()
        envelope = execute("final-select", payload)
        expected = evaluate(
            payload["raw_candidates"],
            payload["semifinalists"],
            "2026-09-10",
            analytics_video_count=0,
            recent=[],
        )
        self.assertEqual(
            [item["candidate_id"] for item in envelope["result"]["selected"]],
            [item["candidate_id"] for item in expected["selected"]],
        )

    def test_positive_analytics_evidence_without_model_fails_closed(self):
        payload = self._evaluation_payload()
        payload["analytics_evidence_count"] = 5
        with self.assertRaises(ValueError):
            execute("candidate-evaluation", payload)

    def test_cli_failure_removes_stale_output(self):
        runner = BASE / "planning" / "planning_runner.py"
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            input_path = tmp / "input.json"
            output_path = tmp / "output.json"
            input_path.write_text(json.dumps({"raw_candidates": []}), encoding="utf-8")
            output_path.write_text("stale", encoding="utf-8")
            env = dict(os.environ)
            env["PYTHONPATH"] = str(BASE)
            proc = subprocess.run(
                [sys.executable, str(runner), "--stage", "raw-filter", "--input", str(input_path), "--output", str(output_path)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(output_path.exists())
            self.assertIn("failed closed", proc.stderr + proc.stdout)

    def test_prompts_make_chatgpt_rank_and_author_complete_candidates(self):
        for prompt in (canonical_planner_text("DAILY"), canonical_planner_text("ADHOC")):
            lower = prompt.lower()
            self.assertIn("chatgpt", lower)
            self.assertIn("rank", lower)
            self.assertIn("chatgpt_ranked_pool", lower)
            self.assertIn("must not", lower)
            self.assertIn("creatively", lower)
            self.assertIn("background", lower)
            self.assertIn("treatment", lower)


if __name__ == "__main__":
    unittest.main()
