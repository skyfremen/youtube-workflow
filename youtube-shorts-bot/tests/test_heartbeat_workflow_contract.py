# Regression gate for dispatch/start heartbeat workflow contracts.
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT.parent / ".github" / "workflows"


class HeartbeatWorkflowContractTests(unittest.TestCase):
    def test_dispatch_evidence_wraps_all_public_dispatches(self):
        for name in ("daily-production.yml", "adhoc-production.yml", "automatic-recovery.yml"):
            text = (WORKFLOWS / name).read_text(encoding="utf-8")
            for required in (
                "recovery/evidence.py prepare",
                "recovery/evidence.py accept",
                "recovery/evidence.py fail",
                "'dispatch_id': os.environ['DISPATCH_ID']",
            ):
                self.assertIn(required, text)
            self.assertLess(text.index("recovery/evidence.py prepare"), text.index("-X POST"))
            self.assertGreater(text.index("recovery/evidence.py accept"), text.index("-X POST"))

    def test_recovery_cadence_and_graces_are_explicit(self):
        text = (WORKFLOWS / "automatic-recovery.yml").read_text(encoding="utf-8")
        self.assertIn("workflows: ['Daily Production', 'Ad-hoc Production']", text)
        self.assertIn("cron: '17,47 * * * *'", text)
        self.assertIn("RECOVERY_STARTUP_GRACE_MINUTES: '25'", text)
        self.assertIn("RECOVERY_ACTIVE_GRACE_MINUTES: '210'", text)
        self.assertIn("RECOVERY_MAX_AUTOMATIC_ATTEMPTS: '3'", text)
        self.assertIn("no-start-retry", text)


if __name__ == "__main__":
    unittest.main()
