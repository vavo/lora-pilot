import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StartupPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        self.workspace = self.root / 'workspace'
        (self.workspace / 'config').mkdir(parents=True)
        self.default = self.root / 'supervisord.conf'
        self.default.write_text((ROOT / 'supervisor/supervisord.conf').read_text())
        self.capture = self.root / 'capture.json'
        supervisor = self.root / 'supervisord'
        supervisor.write_text(
            f'#!{sys.executable}\nimport json, os, sys\n'
            f'with open({str(self.capture)!r}, "w") as f:\n'
            ' json.dump({"args": sys.argv[1:], "config": os.environ.get("SUPERVISOR_CONFIG_PATH"),'
            ' "venv": os.environ.get("COMFY_VENV_PATH")}, f)\n'
        )
        supervisor.chmod(0o755)
        # Relocate only image-owned absolute paths; execute real bootstrap logic.
        for name in ('start.sh', 'bootstrap.sh'):
            source = (ROOT / 'scripts' / name).read_text()
            source = source.replace('/opt/pilot', str(self.bundle))
            source = source.replace('/etc/supervisor/supervisord.conf', str(self.default))
            source = source.replace('/opt/venvs/core/bin/python', shlex.quote(sys.executable))
            source = source.replace('/usr/bin/supervisord', str(supervisor))
            (self.bundle / name).write_text(source)
        (self.bundle / 'service-autostart-apply.py').write_text(
            (ROOT / 'scripts/service-autostart-apply.py').read_text()
        )
        self.env = os.environ.copy()
        for name in ('SUPERVISOR_CONFIG_PATH', 'COMFY_VENV_PATH', 'SERVICE_AUTOSTART_CONFIG_PATH'):
            self.env.pop(name, None)
        self.env.update(WORKSPACE_ROOT=str(self.workspace), HOME=str(self.root / 'home'),
                        SERVICE_UPDATES_BOOT_RECONCILE='0')

    def start(self):
        return subprocess.run(['bash', str(self.bundle / 'start.sh')], env=self.env,
                              capture_output=True, text=True)

    def test_fresh_bundle_sync_is_quiet_and_preserves_unchanged_user_copy(self):
        for relative in ('apps/Portal', 'docs'):
            source = self.bundle / relative
            source.mkdir(parents=True)
            (source / 'example.txt').write_text('bundled')
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('No such file or directory', result.stderr)
        for relative in ('apps/Portal', 'docs'):
            target = self.workspace / relative
            self.assertEqual((target / 'example.txt').read_text(), 'bundled')
            self.assertTrue((target / '.bundle-sync-sha').is_file())
            (target / 'example.txt').write_text('user edit')
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('No such file or directory', result.stderr)
        for relative in ('apps/Portal', 'docs'):
            self.assertEqual((self.workspace / relative / 'example.txt').read_text(), 'user edit')

    def test_default_config_is_used_without_override(self):
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.capture.read_text())['args'], ['-n', '-c', str(self.default)])

    def test_persisted_config_command_and_venv_survive_two_starts(self):
        custom = self.workspace / 'config' / 'custom supervisor.conf'
        command = "command=/bin/bash -lc '/workspace/comfy.sh'"
        custom.write_text(self.default.read_text().replace(
            "command=/bin/bash -lc '/opt/pilot/comfy.sh'", command))
        secrets = self.workspace / 'config' / 'secrets.env'
        secrets.write_text(f'export SUPERVISOR_CONFIG_PATH={shlex.quote(str(custom))}\n'
                           'export COMFY_VENV_PATH=/workspace/venvs/comfy\n')
        for _ in range(2):
            result = self.start()
            self.assertEqual(result.returncode, 0, result.stderr)
            captured = json.loads(self.capture.read_text())
            self.assertEqual(captured['args'], ['-n', '-c', str(custom)])
            self.assertEqual(captured['config'], str(custom))
            self.assertEqual(captured['venv'], '/workspace/venvs/comfy')
            self.assertIn(command, custom.read_text())
            self.assertIn('SUPERVISOR_CONFIG_PATH=', secrets.read_text())

    def test_missing_override_does_not_fall_back_to_default(self):
        self.env['SUPERVISOR_CONFIG_PATH'] = str(self.root / 'missing.conf')
        result = self.start()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Supervisor config is missing or unreadable', result.stderr)
        self.assertFalse(self.capture.exists())
