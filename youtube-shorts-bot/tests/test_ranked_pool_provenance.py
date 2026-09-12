import unittest
from unittest import mock

from validation import planning_audit


class RankedPoolProvenanceTests(unittest.TestCase):
    def plan(self):
        content_ids = [
            f"wd-20990102-story-{index:03d}"
            for index in range(1, 25)
        ]
        ranked = [f"candidate-{index:03d}" for index in range(1, 37)]
        return {
            "plan_date": "2099-01-02",
            "planning_mode": "normal_next_day",
            "final_selected": 24,
            "content_ids": content_ids,
            "planning_execution": {
                "editorial_selection_owner": "chatgpt",
                "planning_method": "chatgpt_ranked_pool",
                "rules_source_sha": "a" * 40,
                "candidate_pool_source_sha": "c" * 40,
                "ranked_candidate_ids": ranked,
                "selected_candidate_ids": ranked[:24],
            },
            "candidate_pool": {
                "source_sha": "c" * 40,
                "candidate_count": 36,
                "target_count": 24,
                "selected_ranks": list(range(1, 25)),
                "rejected_candidates": [],
            },
        }

    def validate(self, plan):
        with mock.patch.object(
            planning_audit, "_single_parent", return_value="a" * 40
        ), mock.patch.object(
            planning_audit, "_is_ancestor", return_value=True
        ):
            return planning_audit.validate_plan_core(
                plan,
                "youtube-shorts-bot/content/planning/2099-01-02.json",
                list(plan["content_ids"]),
                "b" * 40,
                "d" * 64,
            )

    def test_ranked_pool_provenance_passes_for_36_to_24_promotion(self):
        plan = self.plan()
        plan_date, content_ids = self.validate(plan)
        self.assertEqual(plan_date, "2099-01-02")
        self.assertEqual(len(content_ids), 24)

    def test_selected_candidate_order_must_preserve_chatgpt_rank(self):
        plan = self.plan()
        selected = plan["planning_execution"]["selected_candidate_ids"]
        selected[0], selected[1] = selected[1], selected[0]
        with self.assertRaises(planning_audit.PlanningAuditError):
            self.validate(plan)

    def test_ranked_pool_must_contain_exactly_36_candidate_ids(self):
        plan = self.plan()
        plan["planning_execution"]["ranked_candidate_ids"].pop()
        with self.assertRaises(planning_audit.PlanningAuditError):
            self.validate(plan)

    def test_pool_source_must_match_plan_promotion_metadata(self):
        plan = self.plan()
        plan["candidate_pool"]["source_sha"] = "e" * 40
        with self.assertRaises(planning_audit.PlanningAuditError):
            self.validate(plan)


if __name__ == "__main__":
    unittest.main()
