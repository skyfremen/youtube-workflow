import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from growth_config import DAILY_PUBLISH_COUNT, RAW_CANDIDATE_COUNT
from growth_planner import (
    GrowthPlanError,
    analytics_weight,
    blend_scores,
    build_acceptance_fixture,
    editorial_score,
    evaluate,
    filter_candidates,
    hourly_slots,
    normalized_performance_score,
    score_semifinalist,
    select_diverse,
    similarity,
    title_score,
    weighted_score,
)
from growth_config import EDITORIAL_WEIGHTS, TITLE_WEIGHTS


class GrowthPlannerTests(unittest.TestCase):
    def test_acceptance_fixture_generates_at_least_120_raw_premises(self):
        raw, semifinalists = build_acceptance_fixture("2026-09-10")
        self.assertGreaterEqual(len(raw), RAW_CANDIDATE_COUNT)
        self.assertLessEqual(len(semifinalists), 36)
        self.assertEqual(len({x["candidate_id"] for x in raw}), len(raw))

    def test_malformed_and_duplicate_candidates_reject(self):
        raw, _ = build_acceptance_fixture("2026-09-10")
        malformed = dict(raw[1]); malformed.pop("premise")
        duplicate = dict(raw[2]); duplicate["candidate_id"] = raw[0]["candidate_id"]
        accepted, rejected = filter_candidates([raw[0], malformed, duplicate])
        self.assertEqual(len(accepted), 1)
        reasons = [x["reason"] for x in rejected]
        self.assertIn("malformed_candidate", reasons)
        self.assertIn("duplicate_candidate_id", reasons)

    def test_editorial_weighting_is_bounded_and_exact(self):
        candidate = {"editorial_components": {k: 100 for k in EDITORIAL_WEIGHTS}}
        self.assertEqual(editorial_score(candidate), 100.0)
        candidate["editorial_components"]["originality"] = 0
        expected = (sum(100 * w for k, w in EDITORIAL_WEIGHTS.items() if k != "originality") /
                    sum(EDITORIAL_WEIGHTS.values()))
        self.assertAlmostEqual(editorial_score(candidate), expected, places=3)
        candidate["editorial_components"]["curiosity_gap"] = 101
        with self.assertRaises(GrowthPlanError):
            editorial_score(candidate)

    def test_missing_optional_analytics_does_not_crash(self):
        self.assertIsNone(normalized_performance_score({}))
        self.assertEqual(analytics_weight(0), 0.0)
        self.assertEqual(blend_scores(82, None, analytics_weight(0)), 82.0)

    def test_analytics_influence_rises_with_sample_size_but_is_capped(self):
        weights = [analytics_weight(n) for n in (0, 3, 10, 30, 60, 500)]
        self.assertEqual(weights[0], 0.0)
        self.assertEqual(weights, sorted(weights))
        self.assertLessEqual(weights[-1], 0.75)
        self.assertGreater(blend_scores(60, 95, weights[4]), blend_scores(60, 95, weights[1]))

    def test_missing_metrics_are_renormalized_not_fabricated(self):
        score = normalized_performance_score({"average_percentage_viewed": 80, "likes_per_1000_views": 20})
        expected = (80 * 25 + 20 * 5) / 30
        self.assertAlmostEqual(score, expected, places=3)
        self.assertIsNone(normalized_performance_score({"average_percentage_viewed": None}))

    def test_untruthful_title_cannot_win(self):
        components = {k: 100 for k in TITLE_WEIGHTS}
        self.assertEqual(title_score({"truthful": False, "score_components": components}), 0.0)
        self.assertEqual(title_score({"truthful": True, "score_components": components}), 100.0)

    def test_semifinalist_requires_multiple_titles(self):
        _, semifinalists = build_acceptance_fixture("2026-09-10")
        candidate = dict(semifinalists[0])
        candidate["title_candidates"] = candidate["title_candidates"][:2]
        with self.assertRaises(GrowthPlanError):
            score_semifinalist(candidate)

    def test_near_duplicate_detection_uses_story_structure(self):
        a = {
            "premise": "My landlord kept my deposit after a leak he refused to repair",
            "conflict": "DEPOSIT_WITHHELD", "relationship_context": "tenant-landlord",
            "likely_payoff": "photos prove the damage predates me", "ending_style": "REVERSAL",
            "category": "PROPERTY", "protagonist_role": "TENANT", "antagonist_role": "LANDLORD",
        }
        b = {
            "premise": "A landlord refused to return my deposit for water damage he never fixed",
            "conflict": "DEPOSIT_WITHHELD", "relationship_context": "tenant-landlord",
            "likely_payoff": "old photos prove the damage was already there", "ending_style": "REVERSAL",
            "category": "PROPERTY", "protagonist_role": "TENANT", "antagonist_role": "LANDLORD",
        }
        self.assertGreater(similarity(a, b), 0.62)

    def test_recent_history_can_hard_reject_duplicate(self):
        raw, _ = build_acceptance_fixture("2026-09-10")
        candidate = raw[1]
        accepted, rejected = filter_candidates([candidate], recent=[dict(candidate)])
        self.assertFalse(accepted)
        self.assertTrue(any("near_duplicate" in x["reason"] for x in rejected))

    def test_diversity_prevents_category_and_conflict_flood(self):
        candidates = []
        for i in range(30):
            candidates.append({
                "candidate_id": f"x{i}", "final_score": 100 - i / 10,
                "category": "RELATIONSHIP" if i < 15 else f"CAT{i}",
                "conflict": "SAME" if i < 10 else f"C{i}",
                "selected_title_style": "DISCOVERY" if i < 12 else f"T{i}",
                "selection_class": "explore" if i % 6 == 0 else "exploit",
                "editorial_components": {"originality": 80},
                "premise": f"distinct premise tokens {i} unique{i}",
                "likely_payoff": f"payoff {i}",
            })
        selected, _ = select_diverse(candidates)
        self.assertLessEqual(sum(x["category"] == "RELATIONSHIP" for x in selected), 4)
        self.assertLessEqual(sum(x["conflict"] == "SAME" for x in selected), 2)
        self.assertLessEqual(sum(x["selected_title_style"] == "DISCOVERY" for x in selected), 3)

    def test_hourly_schedule_has_24_unique_singapore_slots(self):
        slots = hourly_slots("2026-09-10")
        self.assertEqual(len(slots), 24)
        self.assertEqual(len({x["publish_at"] for x in slots}), 24)
        self.assertTrue(slots[0]["local"].startswith("2026-09-10T00:00:00+08:00"))
        self.assertEqual(slots[0]["publish_at"], "2026-09-09T16:00:00Z")
        self.assertEqual(slots[-1]["publish_at"], "2026-09-10T15:00:00Z")

    def test_full_cold_start_dry_run_selects_at_most_24_without_analytics(self):
        raw, semifinalists = build_acceptance_fixture("2026-09-10")
        result = evaluate(raw, semifinalists, "2026-09-10", analytics_video_count=0)
        self.assertEqual(result["analytics_weight"], 0.0)
        self.assertLessEqual(result["final_selected"], DAILY_PUBLISH_COUNT)
        self.assertEqual(result["final_selected"], len(result["selected"]))
        self.assertEqual(len({x["publication"]["publish_at"] for x in result["selected"]}), result["final_selected"])

    def test_partial_analytics_does_not_break_plan(self):
        raw, semifinalists = build_acceptance_fixture("2026-09-10")
        semifinalists[0]["analytics_metrics"] = {"average_percentage_viewed": 82}
        result = evaluate(raw, semifinalists, "2026-09-10", analytics_video_count=5)
        self.assertGreater(result["analytics_weight"], 0)
        self.assertLess(result["analytics_weight"], 0.75)


if __name__ == "__main__":
    unittest.main()
