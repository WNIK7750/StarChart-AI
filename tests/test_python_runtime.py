import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SCRIPT = ROOT / "scripts" / "python-runtime.ps1"
POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")


class PythonRuntimeResolverTest(unittest.TestCase):
    def test_explicit_python_does_not_mix_another_venv_site_packages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_root = Path(temp_dir)
            foreign_site_packages = fake_root / ".venv" / "Lib" / "site-packages"
            foreign_site_packages.mkdir(parents=True)
            env = {
                **os.environ,
                "AI_NAV_PYTHON": sys.executable,
                "AI_NAV_RUNTIME_TEST_ROOT": str(fake_root),
            }
            command = (
                f". '{RUNTIME_SCRIPT}'; "
                "$null = Resolve-AiNavPython -Root $env:AI_NAV_RUNTIME_TEST_ROOT; "
                "Write-Output $env:PYTHONPATH"
            )

            result = subprocess.run(
                [
                    str(POWERSHELL),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("backend", result.stdout.strip())
            self.assertNotIn(str(foreign_site_packages), result.stdout)


if __name__ == "__main__":
    unittest.main()
