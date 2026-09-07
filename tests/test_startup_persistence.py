import configparser
import json
import os
from pathlib import Path
import shlex
import stat
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
            ' "venv": os.environ.get("COMFY_VENV_PATH"),'
            ' "supervisor_password": os.environ.get("SUPERVISOR_ADMIN_PASSWORD")}, f)\n'
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
        (self.bundle / 'bundle-sync.py').write_text((ROOT / 'scripts/bundle-sync.py').read_text())
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

    def test_mediapilot_sync_toggle_and_custom_workflow_survive_upgrade(self):
        source = self.bundle / 'apps/MediaPilot'
        source.mkdir(parents=True)
        (source / 'main.py').write_text('version one')
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.workspace / 'apps/MediaPilot'
        (target / 'comfy_upscale_workflow.json').write_text('custom workflow')
        (source / 'main.py').write_text('version two')
        self.env['MEDIAPILOT_SYNC_ON_BOOT'] = '0'
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / 'main.py').read_text(), 'version one')
        self.env['MEDIAPILOT_SYNC_ON_BOOT'] = '1'
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / 'main.py').read_text(), 'version two')
        self.assertEqual((target / 'comfy_upscale_workflow.json').read_text(), 'custom workflow')

    def test_default_config_is_used_without_override(self):
        result = self.start()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.capture.read_text())['args'], ['-n', '-c', str(self.default)])

    def test_credentials_remain_literal_across_repeated_boots(self):
        marker = self.root / 'must-not-execute'
        payload = f'$(touch {shlex.quote(str(marker))}) `touch {shlex.quote(str(marker))}`'
        values = {
            'JUPYTER_TOKEN': payload,
            'CODE_SERVER_PASSWORD': 'spaces \'single\' "double" \\backslash $HOME %value',
            'SUPERVISOR_ADMIN_PASSWORD': 'private-supervisor-password',
            'HF_TOKEN': "first line\n'quoted' " + payload + '\nlast line',
        }
        secrets = self.workspace / 'config/secrets.env'
        secrets.write_text("# user's persistent settings\nexport CUSTOM_SETTING='keep\nthis'\n" +
                           ''.join(f'export {key}={shlex.quote(value)}\n' for key, value in values.items()))
        for _ in range(3):
            result = self.start()
            self.assertEqual(result.returncode, 0, result.stderr)
            readback = subprocess.run(
                ['bash', '-c', 'source "$1"; exec "$2" -c "$3"', 'read-secrets',
                 str(secrets), sys.executable,
                 'import json, os; print(json.dumps(dict(os.environ)))'],
                env=self.env, capture_output=True, text=True)
            self.assertEqual(readback.returncode, 0, readback.stderr)
            actual = json.loads(readback.stdout)
            for key, value in values.items():
                self.assertEqual(actual[key], value)
            self.assertEqual(actual['CUSTOM_SETTING'], 'keep\nthis')
            self.assertIn("# user's persistent settings", secrets.read_text())
            self.assertEqual(stat.S_IMODE(secrets.stat().st_mode), 0o600)
            self.assertFalse(marker.exists())

    def test_generated_supervisor_password_is_exported_and_used_by_config(self):
        self.env.pop('SUPERVISOR_ADMIN_PASSWORD', None)
        previous = None
        for _ in range(2):
            result = self.start()
            self.assertEqual(result.returncode, 0, result.stderr)
            password = json.loads(self.capture.read_text())['supervisor_password']
            self.assertIsNotNone(password)
            self.assertRegex(password, r'^[0-9a-f]{64}$')
            config = configparser.ConfigParser(defaults={'ENV_SUPERVISOR_ADMIN_PASSWORD': password})
            config.read(self.default)
            self.assertEqual(config['inet_http_server']['password'], password)
            if previous is not None:
                self.assertEqual(password, previous)
            previous = password

    def test_secret_comments_and_line_continuations_preserve_other_settings(self):
        secrets = self.workspace / 'config/secrets.env'
        secrets.write_text('export HF_TOKEN=abc # trailing backslash \\\n'
                           'export CUSTOM_SETTING=keep\n'
                           'export JUPYTER_TOKEN=first\\\nsecond\n'
                           '# Windows path C:\\\n')
        for _ in range(2):
            result = self.start()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('export CUSTOM_SETTING=keep\n', secrets.read_text())
            self.assertIn('# Windows path C:\\\n', secrets.read_text())
            self.assertIn('export JUPYTER_TOKEN=firstsecond\n', secrets.read_text())

    def test_forced_mediapilot_defaults_keep_password_file_private(self):
        app_dir = self.workspace / 'apps/MediaPilot'
        app_dir.mkdir(parents=True)
        env_file = app_dir / '.env'
        env_file.write_text('MEDIAPILOT_ACCESS_PASSWORD=private-password\n')
        env_file.chmod(0o600)
        self.env['MEDIAPILOT_FORCE_ENV_DEFAULTS'] = '1'
        result = subprocess.run(
            ['bash', '-c', 'umask 022; source "$1"', 'bootstrap', str(self.bundle / 'bootstrap.sh')],
            env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(env_file.stat().st_mode), 0o600)
        self.assertIn('MEDIAPILOT_ACCESS_PASSWORD=private-password\n', env_file.read_text())
        self.assertIn(f'MEDIAPILOT_OUTPUT_DIR={self.workspace}/outputs/comfy\n', env_file.read_text())

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
