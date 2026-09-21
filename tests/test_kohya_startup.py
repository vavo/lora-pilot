import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class KohyaStartupTests(unittest.TestCase):
    def test_launcher_uses_built_dependencies_without_runtime_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / 'repos/kohya_ss'
            repo.mkdir(parents=True)
            requirements = repo / 'requirements_pytorch_windows.txt'
            requirements.write_text('upstream requirements\n')
            marker = repo / 'runtime-install-attempted'
            (repo / 'kohya_gui.py').write_text(
                'import argparse\nfrom pathlib import Path\n'
                'parser = argparse.ArgumentParser()\n'
                'parser.add_argument("--noverify", action="store_true")\n'
                'parser.add_argument("--listen")\nparser.add_argument("--server_port")\n'
                'args = parser.parse_args()\n'
                'if not args.noverify: Path("runtime-install-attempted").touch()\n'
                'print(args.listen, args.server_port)\n'
            )
            (repo / 'transformers.py').write_text('CLIPFeatureExtractor = Dinov2WithRegistersConfig = object\n')
            launcher = Path(__file__).resolve().parents[1] / 'scripts/kohya.sh'
            script = launcher.read_text().replace('/opt/pilot', str(root)).replace('/opt/venvs/kohya/bin/python', sys.executable)
            result = subprocess.run(['bash', '-c', script], cwd=repo, capture_output=True, text=True,
                                    env=dict(os.environ, WORKSPACE_ROOT=str(root / 'workspace'), KOHYA_PORT='6667'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('0.0.0.0 6667', result.stdout)
            self.assertFalse(marker.exists())
            self.assertEqual(requirements.read_text(), 'upstream requirements\n')
