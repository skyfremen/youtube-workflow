import tempfile
import unittest
from pathlib import Path

from validation.public_dry_run import (
    PublicDryRunError,
    active_recovery_grace_minutes,
    daily_timeout_budget_minutes,
    validate_recovery_budget,
)


class RecoveryBudgetDriftTests(unittest.TestCase):
    def public_workflow(self, timeouts=(20, 180, 20)):
        return "\n".join(
            [
                "jobs:",
                "  prepare:",
                f"    timeout-minutes: {timeouts[0]}",
                "  units:",
                f"    timeout-minutes: {timeouts[1]}",
                "  aggregate:",
                f"    timeout-minutes: {timeouts[2]}",
            ]
        )

    def test_current_daily_budget_is_220_minutes(self):
        self.assertEqual(daily_timeout_budget_minutes(self.public_workflow()), 220)
        self.assertEqual(validate_recovery_budget(self.public_workflow(), 240), (220, 240))

    def test_grace_must_exceed_public_budget(self):
        with self.assertRaisesRegex(PublicDryRunError, 'E_DRY_RECOVERY_BUDGET'):
            validate_recovery_budget(self.public_workflow(), 220)
        with self.assertRaisesRegex(PublicDryRunError, 'E_DRY_RECOVERY_BUDGET'):
            validate_recovery_budget(self.public_workflow(), 210)

    def test_public_workflow_shape_drift_fails_closed(self):
        malformed = self.public_workflow() + "\n  extra:\n    timeout-minutes: 5\n"
        with self.assertRaisesRegex(PublicDryRunError, 'E_DRY_RECOVERY_BUDGET_SHAPE'):
            daily_timeout_budget_minutes(malformed)

    def test_private_active_grace_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'automatic-recovery.yml'
            path.write_text(
                "env:\n  RECOVERY_ACTIVE_GRACE_MINUTES: '240'\n",
                encoding='utf-8',
            )
            self.assertEqual(active_recovery_grace_minutes(path), 240)


if __name__ == '__main__':
    unittest.main()
