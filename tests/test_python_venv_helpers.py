import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / "scripts" / "build" / "lib" / "python_venv.sh"


class PythonVenvHelperTests(unittest.TestCase):
    def test_shared_core_site_packages_are_added_after_service_site_packages(self):
        script = textwrap.dedent(
            f"""
            set -euo pipefail
            export TMPDIR
            source "{HELPERS}"
            mkdir -p \\
              "$TMPDIR/core/bin" \\
              "$TMPDIR/core/lib/python3.11/site-packages" \\
              "$TMPDIR/service/bin" \\
              "$TMPDIR/service/lib/python3.11/site-packages"
            cat > "$TMPDIR/core/bin/python" <<'PY'
            #!/bin/sh
            echo "$TMPDIR/core/lib/python3.11/site-packages"
            PY
            cat > "$TMPDIR/service/bin/python" <<'PY'
            #!/bin/sh
            echo "$TMPDIR/service/lib/python3.11/site-packages"
            PY
            chmod +x "$TMPDIR/core/bin/python" "$TMPDIR/service/bin/python"
            core_site="$(site_packages_for_venv "$TMPDIR/core")"
            service_site="$(site_packages_for_venv "$TMPDIR/service")"
            add_shared_core_site_packages "$TMPDIR/service" "$TMPDIR/core"
            test -f "$service_site/99-lora-pilot-core-site.pth"
            grep -qx "$core_site" "$service_site/99-lora-pilot-core-site.pth"
            """
        )

        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                ["bash", "-lc", script],
                env={"TMPDIR": tmp, "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
