import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
NODES = ('ComfyUI-Downloader', 'ComfyUI-GGUF', 'ComfyUI-VideoHelperSuite')


class ComfyBundledNodeTests(unittest.TestCase):
    def test_startup_seeds_missing_nodes_and_preserves_workspace_changes(self):
        script = (ROOT / 'scripts/comfy.sh').read_text()
        seed = script[script.index('# Seed bundled custom nodes'):script.index('# Point Comfy models')]
        with tempfile.TemporaryDirectory() as tmp:
            bundled = Path(tmp) / 'bundled'
            workspace = Path(tmp) / 'custom_nodes'
            workspace.mkdir()
            for node in NODES:
                (bundled / node).mkdir(parents=True)
                (bundled / node / 'revision').write_text('bundled')
            seed = seed.replace('/opt/pilot/bundled/comfy-custom-nodes', str(bundled))

            def run_seed():
                subprocess.run(['bash', '-eu', '-c', seed], check=True,
                               env={**os.environ, 'CUSTOM_NODES_DIR': str(workspace)})

            run_seed()
            for node in NODES:
                self.assertEqual((workspace / node / 'revision').read_text(), 'bundled')
            (workspace / NODES[0] / 'revision').write_text('user changes')
            (workspace / NODES[1]).rename(workspace / (NODES[1] + '.disabled'))
            (workspace / NODES[2]).rename(workspace / 'user-vhs')
            (workspace / NODES[2]).symlink_to(workspace / 'missing-target')
            run_seed()
            self.assertEqual((workspace / NODES[0] / 'revision').read_text(), 'user changes')
            self.assertFalse((workspace / NODES[1]).exists())
            self.assertEqual((workspace / (NODES[1] + '.disabled') / 'revision').read_text(), 'bundled')
            self.assertTrue((workspace / NODES[2]).is_symlink())
            self.assertFalse((workspace / 'missing-target').exists())

    def test_installer_bundles_nodes_and_installs_requirements_without_diffpipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            pilot = Path(tmp) / 'pilot'
            helpers = pilot / 'build/lib'
            helpers.mkdir(parents=True)
            log = Path(tmp) / 'pip.log'
            (helpers / 'python_venv.sh').write_text(
                'pip_install_in_venv() { printf "%s\\n" "$@" >> "$PIP_LOG"; }\n')
            checkout = helpers / 'git_checkout.sh'
            checkout.write_text('''#!/bin/bash
set -eu
mkdir -p "$2"
printf '%s' "$3" > "$2/revision"
printf 'dependency\n' > "$2/requirements.txt"
printf 'comfyui_manager==test\n' > "$2/manager_requirements.txt"
''')
            checkout.chmod(0o755)
            patch = pilot / 'build/patches/patch-comfy.sh'
            patch.parent.mkdir()
            patch.write_text('#!/bin/bash\nexit 0\n')
            patch.chmod(0o755)
            python = Path(tmp) / 'venvs/core/bin/python'
            python.parent.mkdir(parents=True)
            python.write_text('#!/bin/bash\ncat >/dev/null\n')
            python.chmod(0o755)
            script = (ROOT / 'scripts/build/install-comfy.sh').read_text()
            script = script.replace('/opt/pilot', str(pilot)).replace('/opt/venvs', str(Path(tmp) / 'venvs'))
            script = script.replace('/workspace', str(Path(tmp) / 'workspace')).replace('/tmp/comfy-req.txt', str(Path(tmp) / 'requirements.txt'))
            env = {**os.environ, 'PIP_LOG': str(log), 'INSTALL_DIFFPIPE': '0',
                   'COMFYUI_REF': 'core-pin', 'COMFYUI_MANAGER_REF': 'test',
                   'COMFYUI_DOWNLOADER_REF': 'downloader-pin', 'COMFYUI_GGUF_REF': 'gguf-pin',
                   'COMFYUI_VHS_REF': 'vhs-pin'}
            subprocess.run(['bash', '-eu', '-c', script], check=True, env=env)
            for node, pin in zip(NODES, ('downloader-pin', 'gguf-pin', 'vhs-pin')):
                self.assertEqual((pilot / 'bundled/comfy-custom-nodes' / node / 'revision').read_text(), pin)
            arguments = log.read_text().splitlines()
            self.assertIn(str(python.parent.parent), arguments)
            self.assertIn(str(pilot / 'config/core-constraints.txt'), arguments)
            for node in NODES[1:]:
                self.assertIn(str(pilot / 'repos/ComfyUI/custom_nodes' / node / 'requirements.txt'), arguments)
