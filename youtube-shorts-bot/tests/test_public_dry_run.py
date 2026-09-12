import unittest

from validation.public_dry_run import (
    PublicDryRunError,
    correlation_id,
    select_correlated_run,
)


class PublicDryRunTests(unittest.TestCase):
    def test_correlation_id_is_stable_and_opaque(self):
        value = correlation_id('12345', '2', 'a' * 40)
        self.assertRegex(value, r'^dr_[0-9a-f]{24}$')
        self.assertEqual(value, correlation_id('12345', '2', 'a' * 40))
        self.assertNotEqual(value, correlation_id('12345', '3', 'a' * 40))

    def test_selects_only_new_run_with_matching_job_correlation(self):
        runs = [
            {'id': 10, 'event': 'workflow_dispatch', 'head_sha': 'a' * 40},
            {'id': 11, 'event': 'workflow_dispatch', 'head_sha': 'a' * 40},
        ]
        selected = select_correlated_run(
            runs,
            before_ids={10},
            expected_sha='a' * 40,
            correlation='dr_' + '1' * 24,
            jobs_by_run={11: [{'name': 'dry-run-dr_' + '1' * 24}]},
        )
        self.assertEqual(selected['id'], 11)

    def test_rejects_correlated_run_on_wrong_sha(self):
        with self.assertRaisesRegex(PublicDryRunError, 'E_DRY_PUBLIC_SHA'):
            select_correlated_run(
                [{'id': 11, 'event': 'workflow_dispatch', 'head_sha': 'b' * 40}],
                before_ids=set(),
                expected_sha='a' * 40,
                correlation='dr_' + '1' * 24,
                jobs_by_run={11: [{'name': 'dry-run-dr_' + '1' * 24}]},
            )

    def test_rejects_ambiguous_correlated_runs(self):
        runs = [
            {'id': 11, 'event': 'workflow_dispatch', 'head_sha': 'a' * 40},
            {'id': 12, 'event': 'workflow_dispatch', 'head_sha': 'a' * 40},
        ]
        jobs = {
            11: [{'name': 'dry-run-dr_' + '1' * 24}],
            12: [{'name': 'dry-run-dr_' + '1' * 24}],
        }
        with self.assertRaisesRegex(PublicDryRunError, 'E_DRY_PUBLIC_AMBIGUOUS'):
            select_correlated_run(
                runs,
                before_ids=set(),
                expected_sha='a' * 40,
                correlation='dr_' + '1' * 24,
                jobs_by_run=jobs,
            )


if __name__ == '__main__':
    unittest.main()
