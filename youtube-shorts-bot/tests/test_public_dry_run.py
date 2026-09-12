import inspect
import unittest
from pathlib import Path

from validation.public_dry_run import (
    PublicDryRunError,
    correlation_id,
    dispatch_and_verify,
    expected_sha,
    select_correlated_run,
)


ROOT = Path(__file__).resolve().parents[2]
DRY_RUN = ROOT / '.github/workflows/dry-run.yml'


class PublicDryRunTests(unittest.TestCase):
    def test_correlation_id_is_stable_and_opaque(self):
        value = correlation_id('12345', '2', 'a' * 40)
        self.assertRegex(value, r'^dr_[0-9a-f]{24}$')
        self.assertEqual(value, correlation_id('12345', '2', 'a' * 40))
        self.assertNotEqual(value, correlation_id('12345', '3', 'a' * 40))

    def test_expected_sha_is_fail_closed(self):
        self.assertEqual(expected_sha('a' * 40), 'a' * 40)
        for value in ('', 'main', 'A' * 40, 'a' * 39, 'a' * 41):
            with self.assertRaisesRegex(PublicDryRunError, 'E_DRY_PUBLIC_SHA'):
                expected_sha(value)

    def test_dispatch_uses_pre_resolved_sha_and_never_re_resolves_main(self):
        source = inspect.getsource(dispatch_and_verify)
        self.assertIn("PUBLIC_EXPECTED_SHA", source)
        self.assertNotIn("commits/main", source)

    def test_workflow_resolves_one_sha_for_parity_and_dispatch(self):
        text = DRY_RUN.read_text(encoding='utf-8')
        self.assertIn('id: public_runtime', text)
        self.assertIn("refs/heads/main", text)
        self.assertIn('PUBLIC_RUNTIME_SHA: ${{ steps.public_runtime.outputs.sha }}', text)
        self.assertIn('PUBLIC_EXPECTED_SHA: ${{ steps.public_runtime.outputs.sha }}', text)
        self.assertIn('git -C /tmp/production-runtime-contract fetch --quiet --depth 1 origin "${PUBLIC_RUNTIME_SHA}"', text)
        self.assertIn('test "$(git -C /tmp/production-runtime-contract rev-parse HEAD)" = "${PUBLIC_RUNTIME_SHA}"', text)
        self.assertNotIn('git clone --quiet --depth 1 https://github.com/skyfremen/production-runtime.git', text)

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
