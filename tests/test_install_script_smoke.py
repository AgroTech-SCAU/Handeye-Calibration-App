from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class InstallScriptSmokeTests(unittest.TestCase):
    def test_install_has_visible_stages_and_finishes_with_fake_downloads(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            app = Path(folder) / "app"
            app.mkdir()
            shutil.copy2(ROOT / "install.sh", app / "install.sh")
            (app / "requirements.txt").write_text("", encoding="utf-8")
            (app / ".venv" / "bin").mkdir(parents=True)
            (app / "scripts").mkdir()
            fake_bin = Path(folder) / "bin"
            fake_bin.mkdir()

            executable(
                app / ".venv" / "bin" / "python",
                "#!/usr/bin/env bash\n"
                "if [[ \"$*\" == *verify_core.py* ]]; then echo 'CORE INTEGRITY: PASS'; fi\n"
                "if [[ \"$*\" == *smoke_backend.py* ]]; then echo '[HandEye] backend smoke PASS'; fi\n"
                "exit 0\n",
            )
            executable(
                fake_bin / "npm",
                "#!/usr/bin/env bash\n"
                "if [ \"${1:-}\" = install ]; then mkdir -p node_modules/electron; printf 'x' > node_modules/electron/install.js; fi\n"
                "exit 0\n",
            )
            executable(
                fake_bin / "node",
                "#!/usr/bin/env bash\n"
                "if [ \"${1:-}\" = -p ]; then echo 22; exit 0; fi\n"
                "mkdir -p node_modules/electron/dist\n"
                "printf '#!/usr/bin/env bash\\nexit 0\\n' > node_modules/electron/dist/electron\n"
                "chmod +x node_modules/electron/dist/electron\n"
                "exit 0\n",
            )

            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
            result = subprocess.run(
                ["bash", "install.sh"],
                cwd=app,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=15,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("checking Python backend", result.stdout)
            self.assertIn("Node package install", result.stdout)
            self.assertIn("Electron binary download via mirror", result.stdout)
            self.assertIn("install complete", result.stdout)


if __name__ == "__main__":
    unittest.main()
