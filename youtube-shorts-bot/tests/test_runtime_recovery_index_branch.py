import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import urllib.request
from pathlib import Path


class PublicRecoveryIndexBranchTests(unittest.TestCase):
    def test_public_branch_recovery_suite(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            archive = temp / "runtime.tgz"
            request = urllib.request.Request(
                "https://api.github.com/repos/skyfremen/production-runtime/tarball/work%2Frecovery-index-20260912",
                headers={"Accept": "application/vnd.github+json"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                archive.write_bytes(response.read())
            extract = temp / "src"
            extract.mkdir()
            with tarfile.open(archive, "r:gz") as package:
                package.extractall(extract)
            roots = [path for path in extract.iterdir() if path.is_dir()]
            self.assertEqual(len(roots), 1)
            root = roots[0]
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "py_compile",
                    "runtime/output/state.py",
                    "runtime/output/transfer.py",
                    "tests/test_state.py",
                    "tests/test_transfer_recovery.py",
                ],
                cwd=root,
                check=True,
            )
            env = dict(os.environ)
            env["PYTHONPATH"] = os.pathsep.join(
                [str(root / "runtime"), str(root / "tests")]
            )
            for pattern in ("test_state.py", "test_transfer_recovery.py"):
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests",
                        "-p",
                        pattern,
                        "-v",
                    ],
                    cwd=root,
                    env=env,
                    check=True,
                )


if __name__ == "__main__":
    unittest.main()
