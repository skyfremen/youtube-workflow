import unittest
from unittest.mock import patch

from planning import adhoc_precommit, daily_precommit, pool_admission


RULES_SHA = "1" * 40
POOL = {"planning_execution": {"rules_source_sha": RULES_SHA}}


class PoolAdmissionTests(unittest.TestCase):
    def test_adhoc_reuses_precommit_without_git_or_uniqueness(self):
        expected = {"status": "PASS"}
        with patch.object(adhoc_precommit, "validate_draft", return_value=expected) as validate:
            result = pool_admission.validate_committed_pool("adhoc", POOL, b"draft")
        self.assertIs(result, expected)
        validate.assert_called_once_with(
            POOL,
            RULES_SHA,
            raw_bytes=b"draft",
            check_checkout_head=False,
            check_uniqueness=False,
        )

    def test_daily_reuses_precommit_without_git_or_uniqueness(self):
        expected = {"status": "PASS"}
        with patch.object(daily_precommit, "validate_draft", return_value=expected) as validate:
            result = pool_admission.validate_committed_pool("daily", POOL, b"draft")
        self.assertIs(result, expected)
        validate.assert_called_once_with(
            POOL,
            RULES_SHA,
            raw_bytes=b"draft",
            check_checkout_head=False,
            check_uniqueness=False,
        )

    def test_missing_rules_identity_fails_closed(self):
        result = pool_admission.validate_committed_pool("adhoc", {}, b"draft")
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["commit_allowed"])
        self.assertIn("rules_source_sha", result["pool_errors"][0])


if __name__ == "__main__":
    unittest.main()
