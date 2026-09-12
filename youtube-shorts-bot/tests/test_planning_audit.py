import unittest

from validation.planning_audit import (
    PlanningAuditError,
    classify_daily_changes,
    validate_plan_core,
)


class PlanningAuditTests(unittest.TestCase):
    parent_sha = "a" * 40
    implementation_sha = "b" * 64

    def execution(self, stage, input_char):
        entry_points = {
            "raw-filter": ["planning.planning_engine.filter_candidates"],
            "final-select": [
                "analytics.analytics_learning.score_candidate",
                "planning.planning_engine.evaluate",
            ],
        }
        return {
            "contract_version": 1,
            "stage": stage,
            "source_sha": self.parent_sha,
            "implementation_sha256": self.implementation_sha,
            "input_sha256": input_char * 64,
            "entry_points": entry_points[stage],
        }

    def plan(self, content_id="wd-20260912T200000-drama-cafe-a1b2c3"):
        return {
            "plan_date": "2026-09-13",
            "planning_mode": "normal_next_day",
            "final_selected": 1,
            "content_ids": [content_id],
            "planning_execution": {
                "raw_filter": self.execution("raw-filter", "c"),
                "final_selection": self.execution("final-select", "d"),
                "selected_candidate_ids": ["candidate-001"],
            },
        }

    def validate(self, plan=None, request_ids=None):
        plan = plan or self.plan()
        request_ids = request_ids or list(plan["content_ids"])
        return validate_plan_core(
            plan,
            "youtube-shorts-bot/content/planning/2026-09-13.json",
            request_ids,
            self.parent_sha,
            self.implementation_sha,
        )

    def test_valid_core_binds_audit_to_parent_and_runner_provenance(self):
        plan_date, content_ids = self.validate()
        self.assertEqual(plan_date, "2026-09-13")
        self.assertEqual(content_ids, self.plan()["content_ids"])

    def test_acceptance_test_or_adhoc_identity_cannot_enter_canonical_daily_plan(self):
        for content_id in (
            "wd-20260912T200000-acceptance-a1b2c3",
            "wd-20260912T200000-test-a1b2c3",
            "wd-20260912T200000-smoke-a1b2c3",
            "wd-20260912T200000-dryrun-a1b2c3",
            "wd-20260912T200000-adhoc-a1b2c3",
        ):
            with self.subTest(content_id=content_id), self.assertRaises(PlanningAuditError):
                self.validate(self.plan(content_id))

    def test_provenance_source_must_equal_content_commit_parent(self):
        plan = self.plan()
        plan["planning_execution"]["final_selection"]["source_sha"] = "e" * 40
        with self.assertRaises(PlanningAuditError):
            self.validate(plan)

    def test_provenance_implementation_hash_must_match_canonical_code(self):
        plan = self.plan()
        plan["planning_execution"]["raw_filter"]["implementation_sha256"] = "e" * 64
        with self.assertRaises(PlanningAuditError):
            self.validate(plan)

    def test_content_ids_must_exactly_match_same_commit_request_files(self):
        with self.assertRaises(PlanningAuditError):
            self.validate(request_ids=["wd-20260912T200000-other-a1b2c3"])

    def test_selected_candidate_count_and_uniqueness_are_enforced(self):
        plan = self.plan()
        plan["planning_execution"]["selected_candidate_ids"] = []
        with self.assertRaises(PlanningAuditError):
            self.validate(plan)

    def test_only_exact_canonical_plan_filename_is_accepted_by_commit_classifier(self):
        request = "youtube-shorts-bot/content/requests/wd-20260912T200000-drama-cafe-a1b2c3.json"
        good = [
            ("A", "youtube-shorts-bot/content/planning/2026-09-13.json"),
            ("A", request),
        ]
        plan, requests, sourcing = classify_daily_changes(good)
        self.assertEqual(plan, "youtube-shorts-bot/content/planning/2026-09-13.json")
        self.assertEqual(requests, [request])
        self.assertIsNone(sourcing)

        for bad_plan in (
            "youtube-shorts-bot/content/planning/2026-09-13-acceptance.json",
            "youtube-shorts-bot/content/planning/acceptance-2026-09-13.json",
        ):
            with self.subTest(path=bad_plan), self.assertRaises(PlanningAuditError):
                classify_daily_changes([("A", bad_plan), ("A", request)])

    def test_commit_classifier_rejects_mutation_or_unexpected_files(self):
        request = "youtube-shorts-bot/content/requests/wd-20260912T200000-drama-cafe-a1b2c3.json"
        with self.assertRaises(PlanningAuditError):
            classify_daily_changes([
                ("A", "youtube-shorts-bot/content/planning/2026-09-13.json"),
                ("M", request),
            ])
        with self.assertRaises(PlanningAuditError):
            classify_daily_changes([
                ("A", "youtube-shorts-bot/content/planning/2026-09-13.json"),
                ("A", request),
                ("A", "README.md"),
            ])


if __name__ == "__main__":
    unittest.main()
