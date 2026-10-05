import asyncio
import configparser
import sys
import tomllib
import fcntl
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import httpx
from apps.Portal.services import code_server as editor
from apps.Portal import app as portal

ROOT = Path(__file__).resolve().parents[1]


class EditorInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.root_name = f'code-server-{editor.VERSION}-linux-amd64'
        for target, value in [('SYSTEM_BINARY', self.workspace / 'system-code-server')]:
            mock = patch.object(editor, target, value); mock.start(); self.addCleanup(mock.stop)
        mock = patch.object(editor, 'architecture', return_value='amd64'); mock.start(); self.addCleanup(mock.stop)
        self.disk = patch.object(editor.shutil, 'disk_usage', return_value=Mock(free=4 * 1024**3))
        self.disk.start(); self.addCleanup(self.disk.stop)

    def archive(self, extra=None):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as bundle:
            content = b'#!/bin/sh\necho fixture\n'
            item = tarfile.TarInfo(self.root_name + '/bin/code-server')
            item.size = len(content); item.mode = 0o755
            bundle.addfile(item, io.BytesIO(content))
            if extra:
                bundle.addfile(extra)
        return data.getvalue()

    def install(self, archive=None, **kwargs):
        data = self.archive() if archive is None else archive
        with patch.object(editor, 'urlopen', return_value=io.BytesIO(data)) as request, \
             patch.dict(editor.CHECKSUMS, amd64=hashlib.sha256(data).hexdigest()), \
             patch.object(editor.subprocess, 'run', return_value=Mock(returncode=0, stdout='info Wrote default config file\n' + editor.VERSION)) as run:
            result = editor.install(self.workspace, Mock(), **kwargs)
        return result, request, run

    def test_install_is_atomic_persistent_and_preserves_all_editor_data(self):
        saved = self.workspace / 'code-server/extensions/user-extension'
        saved.parent.mkdir(parents=True); saved.write_text('keep')
        result, request, run = self.install()
        self.assertEqual(result, editor.VERSION)
        self.assertTrue(editor.binary(self.workspace).is_file())
        self.assertEqual(saved.read_text(), 'keep')
        self.assertFalse(list((self.workspace / 'apps').glob('.code-server-install-*')))
        self.assertIn('/coder/code-server/releases/download/v' + editor.VERSION, request.call_args.args[0])
        self.assertEqual(run.call_args.args[0][-1], '--version')
        with patch.object(editor, 'urlopen', side_effect=AssertionError('must not download')):
            self.assertEqual(editor.install(self.workspace, Mock()), 'Already installed')

    def test_existing_system_installation_is_preserved(self):
        editor.SYSTEM_BINARY.write_text('existing'); editor.SYSTEM_BINARY.chmod(0o755)
        with patch.object(editor, 'urlopen') as request:
            self.assertEqual(editor.install(self.workspace, Mock()), 'Already installed')
        request.assert_not_called()
        self.assertEqual(editor.binary(self.workspace), editor.SYSTEM_BINARY)

    def test_existing_incomplete_directory_and_symlink_are_never_replaced(self):
        target = self.workspace / 'apps/code-server'; target.mkdir(parents=True)
        saved = target / 'user-file'; saved.write_text('keep')
        with self.assertRaisesRegex(RuntimeError, 'left untouched'):
            self.install()
        self.assertEqual(saved.read_text(), 'keep')
        saved.unlink(); target.rmdir(); target.symlink_to(self.workspace / 'absent')
        with self.assertRaisesRegex(RuntimeError, 'left untouched'):
            self.install()
        self.assertTrue(target.is_symlink())

    def test_checksum_failure_never_extracts_or_executes_and_can_retry(self):
        with patch.object(editor, 'urlopen', return_value=io.BytesIO(self.archive())), \
             patch.object(editor.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'checksum'):
                editor.install(self.workspace, Mock())
        run.assert_not_called()
        self.assertIsNone(editor.binary(self.workspace))
        self.assertEqual(self.install()[0], editor.VERSION)

    def test_traversal_external_links_and_special_files_are_rejected(self):
        for name, kind, link in [
            ('../../escape', tarfile.REGTYPE, ''),
            (self.root_name + '/../../../../escape', tarfile.REGTYPE, ''),
            (self.root_name + '/link', tarfile.SYMTYPE, '/etc/passwd'),
            (self.root_name + '/link', tarfile.LNKTYPE, '../../outside'),
            (self.root_name + '/device', tarfile.CHRTYPE, ''),
        ]:
            with self.subTest(name=name, kind=kind):
                item = tarfile.TarInfo(name); item.type = kind; item.linkname = link
                with self.assertRaises((RuntimeError, tarfile.FilterError)):
                    self.install(self.archive(item))
                self.assertIsNone(editor.binary(self.workspace))

    def test_safe_relative_symlink_is_supported(self):
        item = tarfile.TarInfo(self.root_name + '/editor'); item.type = tarfile.SYMTYPE; item.linkname = 'bin/code-server'
        self.install(self.archive(item))
        self.assertEqual((self.workspace / 'apps/code-server/editor').read_bytes(), b'#!/bin/sh\necho fixture\n')

    def test_limits_deadline_and_disk_failure_do_not_publish(self):
        for setting in ('MAX_DOWNLOAD', 'MAX_UNPACKED', 'MAX_MEMBERS', 'INSTALL_TIMEOUT'):
            with self.subTest(setting=setting), patch.object(editor, setting, 0):
                with self.assertRaises(RuntimeError):
                    self.install()
                self.assertIsNone(editor.binary(self.workspace))
        with patch.object(editor.shutil, 'disk_usage', return_value=Mock(free=1)):
            with self.assertRaisesRegex(RuntimeError, 'free workspace'):
                self.install()

    def test_interrupted_download_and_failed_executable_are_retryable(self):
        for failure in (OSError('offline'), subprocess.TimeoutExpired('fixture', 30)):
            with patch.object(editor, '_download', side_effect=failure):
                with self.assertRaises(type(failure)):
                    editor.install(self.workspace, Mock())
            self.assertFalse(list((self.workspace / 'apps').glob('.code-server-install-*')))
        data = self.archive()
        with patch.object(editor, 'urlopen', return_value=io.BytesIO(data)), \
             patch.dict(editor.CHECKSUMS, amd64=hashlib.sha256(data).hexdigest()), \
             patch.object(editor.subprocess, 'run', return_value=Mock(returncode=0, stdout='wrong')):
            with self.assertRaisesRegex(RuntimeError, 'version check'):
                editor.install(self.workspace, Mock())
        self.assertIsNone(editor.binary(self.workspace))
        self.assertEqual(self.install()[0], editor.VERSION)

    def test_concurrent_process_cannot_install(self):
        apps = self.workspace / 'apps'; apps.mkdir()
        with (apps / '.code-server-install.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, 'already running'):
                self.install()
        self.assertIsNone(editor.binary(self.workspace))

    def test_launcher_uses_persistent_binary_and_existing_data_locations(self):
        self.install()
        executable = editor.binary(self.workspace)
        executable.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
        result = subprocess.run(['bash', str(ROOT / 'scripts/start-code-server.sh')],
                                env=dict(os.environ, WORKSPACE_ROOT=str(self.workspace)), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.workspace / 'code-server/extensions'), result.stdout)
        self.assertIn('--auth\npassword', result.stdout)


class EditorApiTests(unittest.TestCase):
    def setUp(self):
        mock = patch.object(portal, '_service_update_jobs', {}); mock.start(); self.addCleanup(mock.stop)
        mock = patch.object(editor, 'binary', return_value=None); mock.start(); self.addCleanup(mock.stop)

    def test_install_dispatch_is_allowlisted_and_duplicate_clicks_share_one_job(self):
        with patch.object(portal.threading, 'Thread') as thread:
            for name, status in [('unknown', 404), ('jupyter', 400)]:
                with self.assertRaises(portal.HTTPException) as error:
                    portal.service_install_start(name)
                self.assertEqual(error.exception.status_code, status)
            first = portal.service_install_start('code-server')
            second = portal.service_install_start('code-server')
            self.assertEqual(first, second)
            self.assertEqual(first['operation'], 'install')
            self.assertEqual(thread.call_count, 1)
            self.assertEqual(portal.service_update_status('code-server')['state'], 'running')

    def test_absent_editor_cannot_start_restart_or_enable_autostart(self):
        with patch.object(portal, '_run_supervisorctl') as control, patch.object(portal, '_set_service_autostart') as settings:
            for action in ('start', 'restart'):
                with self.assertRaises(portal.HTTPException) as error:
                    portal.control_service('code-server', action)
                self.assertEqual(error.exception.status_code, 409)
            with self.assertRaises(portal.HTTPException):
                portal.service_autostart('code-server', portal.ServiceAutostartRequest(enabled=True))
            control.assert_not_called(); settings.assert_not_called()
        self.assertFalse(portal._read_service_autostart('code-server'))
        self.assertEqual(portal._service_version_entry('code-server').source, 'optional')
        self.assertTrue(portal.service_registry.public_definition('code-server')['capabilities']['install'])

    def test_failure_is_sanitized_and_retry_dispatches(self):
        job = portal.ServiceUpdateJob(name='code-server', operation='install')
        portal._service_update_jobs['code-server'] = job
        with patch.object(editor, 'install', side_effect=OSError('https://signed-url/SECRET')):
            portal._run_code_server_install(job)
        self.assertEqual(job.state, 'error')
        self.assertNotIn('SECRET', str(portal.service_update_status('code-server')))
        with patch.object(portal.threading, 'Thread') as thread:
            self.assertEqual(portal.service_install_start('code-server')['state'], 'running')
            thread.assert_called_once()

    def test_install_inherits_controlpilot_auth_and_has_no_arbitrary_source_parameter(self):
        async def exercise():
            transport = httpx.ASGITransport(app=portal.app)
            async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
                with patch.object(portal, '_controlpilot_request_authenticated', return_value=False), \
                     patch.object(portal, '_run_code_server_install') as install:
                    response = await client.post('/api/services/code-server/install/start')
                    self.assertEqual(response.status_code, 401)
                    install.assert_not_called()
                with patch.object(portal, '_controlpilot_request_authenticated', return_value=True), \
                     patch.object(portal, '_run_code_server_install') as install:
                    response = await client.post('/api/services/code-server/install/start', json={'url': 'http://evil', 'target_version': 'evil'})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()['target_version'], editor.VERSION)
                    self.assertEqual(install.call_count, 1)
        asyncio.run(exercise())

    def test_success_does_not_start_editor_or_change_autostart(self):
        job = portal.ServiceUpdateJob(name='code-server', operation='install')
        with patch.object(editor, 'install', return_value=editor.VERSION), \
             patch.object(portal, '_run_supervisorctl') as control, patch.object(portal, '_set_service_autostart') as settings:
            portal._run_code_server_install(job)
        self.assertEqual(job.state, 'done')
        control.assert_not_called(); settings.assert_not_called()

    def test_default_image_never_downloads_editor_and_autostart_is_off(self):
        for filename in ('Dockerfile', 'Makefile', 'build.env.example'):
            text = (ROOT / filename).read_text()
            self.assertNotIn('install-code-server', text)
            self.assertNotIn('CODE_SERVER_VERSION', text)
        section = (ROOT / 'supervisor/supervisord.conf').read_text().split('[program:code-server]', 1)[1].split('[program:', 1)[0]
        self.assertIn('autostart=false', section)


class EditorBootTests(unittest.TestCase):
    def test_architecture_is_limited_to_supported_linux_releases(self):
        for system, machine, expected in [('Linux', 'x86_64', 'amd64'), ('Linux', 'aarch64', 'arm64'),
                                          ('Darwin', 'arm64', None), ('Linux', 'armv7l', None)]:
            with self.subTest(system=system, machine=machine), \
                 patch.object(editor.platform, 'system', return_value=system), \
                 patch.object(editor.platform, 'machine', return_value=machine):
                if expected:
                    self.assertEqual(editor.architecture(), expected)
                else:
                    with self.assertRaises(editor.InstallError):
                        editor.architecture()

    def test_missing_editor_suppresses_saved_autostart_but_preserves_preference(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            conf = workspace / 'supervisor.conf'
            conf.write_text('[program:code-server]\nautostart=true\n[program:jupyter]\nautostart=true\n')
            state = workspace / 'autostart.toml'
            state.write_text('[services.code-server]\nautostart = true\n')
            command = [sys.executable, str(ROOT / 'scripts/service-autostart-apply.py'),
                       '--supervisor-conf', str(conf), '--state-file', str(state)]
            env = dict(os.environ, WORKSPACE_ROOT=temp)
            subprocess.run(command, env=env, capture_output=True, check=True)
            settings = configparser.ConfigParser(); settings.read(conf)
            self.assertFalse(settings.getboolean('program:code-server', 'autostart'))
            self.assertTrue(settings.getboolean('program:jupyter', 'autostart'))
            self.assertTrue(tomllib.loads(state.read_text())['services']['code-server']['autostart'])
            executable = workspace / 'apps/code-server/bin/code-server'
            executable.parent.mkdir(parents=True); executable.write_text('#!/bin/sh\n'); executable.chmod(0o755)
            subprocess.run(command, env=env, capture_output=True, check=True)
            settings.read(conf)
            self.assertTrue(settings.getboolean('program:code-server', 'autostart'))
