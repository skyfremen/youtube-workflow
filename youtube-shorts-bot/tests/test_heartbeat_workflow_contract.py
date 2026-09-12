# Regression gate for dispatch/start heartbeat workflow contracts.
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


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
        self.assertIn("RECOVERY_ACTIVE_GRACE_MINUTES: '240'", text)
        self.assertIn("RECOVERY_MAX_AUTOMATIC_ATTEMPTS: '3'", text)
        self.assertIn("no-start-retry", text)

        startup = re.search(r"RECOVERY_STARTUP_GRACE_MINUTES: '(\d+)'", text)
        active = re.search(r"RECOVERY_ACTIVE_GRACE_MINUTES: '(\d+)'", text)
        self.assertIsNotNone(startup)
        self.assertIsNotNone(active)
        startup_minutes = int(startup.group(1))
        active_minutes = int(active.group(1))

        # The public Daily workflow currently permits up to 20 + 180 + 20 = 220
        # minutes across prepare, units, and aggregate. The long grace must exceed
        # that full legitimate execution budget, while no-START recovery stays fast.
        self.assertEqual(startup_minutes, 25)
        self.assertGreater(active_minutes, 220)
        self.assertGreater(active_minutes, startup_minutes)


if __name__ == "__main__":
    unittest.main()
