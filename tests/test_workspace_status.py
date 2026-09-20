import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.Portal.services import diagnostics, activity


class DiagnosticsTests(unittest.TestCase):
    def test_unknown_metadata_is_honest_and_extra_fields_never_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'build.json'
            self.assertEqual(diagnostics.build_identity(path), {'revision': None, 'built_at': None})
            path.write_text(json.dumps({'revision': 'a' * 40, 'built_at': '2026-09-20T01:02:03Z',
                                       'token': 'SECRET', 'url': 'https://user:SECRET@example.com'}))
            self.assertEqual(diagnostics.build_identity(path), {'revision': 'a' * 40, 'built_at': '2026-09-20T01:02:03Z'})
            path.write_text('{bad json')
            self.assertIsNone(diagnostics.build_identity(path)['revision'])

    def test_support_snapshot_excludes_secrets_paths_hosts_and_raw_errors(self):
        specs = {'comfy': {'kind': 'git', 'repo_dir': '/private/workspace'}, 'invoke': {}}
        gpus = lambda: [{'name': 'NVIDIA A40', 'mem_total': 46068 * 1024 * 1024, 'token': 'SECRET', 'host': 'private-host'}]
        with patch.object(diagnostics, 'command', return_value='comfy RUNNING pid 12 https://SECRET\ninvoke STOPPED SECRET'), \
             patch.object(diagnostics, 'installed_version', return_value='a' * 40):
            data = diagnostics.snapshot(gpus, specs, 'supervisorctl', lambda: {'revision': 'b' * 40, 'built_at': None})
        encoded = json.dumps(data)
        for forbidden in ('SECRET', '/private', 'private-host', 'https://', 'pid 12'):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(data['services'][1]['state'], 'STOPPED')
        self.assertIn('NVIDIA A40 (46068 MiB)', data['summary'])

    def test_service_versions_are_local_and_reject_unexpected_output(self):
        with patch.object(diagnostics, 'command', return_value='https://user:secret@example.com') as cmd:
            self.assertIsNone(diagnostics.installed_version({'kind': 'git', 'repo_dir': '/repo'}))
            self.assertIsNone(diagnostics.installed_version({'kind': 'pip', 'python_bin': '/python', 'package': 'test'}))
            self.assertFalse(any('index' in str(call) or 'fetch' in str(call) for call in cmd.call_args_list))

    def test_stopped_service_status_is_read_even_when_supervisor_returns_nonzero(self):
        with patch('subprocess.run', return_value=Mock(returncode=3, stdout='comfy STOPPED\n')):
            self.assertEqual(diagnostics.command(['supervisorctl', 'status'], status=True), 'comfy STOPPED')


class ActivityTests(unittest.TestCase):
    def test_activity_has_progress_and_links_without_logs_or_configuration(self):
        queue = Mock()
        queue.root.exists.return_value = True
        queue.lock = threading.RLock()
        queue.paused = False
        queue.list.return_value = [dict(id='a'*32, spec={'output_name': 'Portrait'}, status='running',
                                       created_at='2026-09-20T01:00:00Z', template={'secret': 'SECRET'})]
        queue.logs.return_value = ['steps: 42%| 42/100 SECRET']
        downloads = Mock()
        downloads.list_jobs.return_value = {'jobs': [dict(name='base', started_at=10, state='error', progress_pct=20, error='SECRET')]}
        app = FastAPI()
        app.include_router(activity.create_router(queue, downloads, lambda: []))
        with TestClient(app) as client:
            data = client.get('/api/activity').json()
        self.assertEqual(data['items'][0]['progress'], 42)
        self.assertEqual(data['items'][0]['run_id'], 'a'*32)
        self.assertEqual(data['items'][1]['state'], 'failed')
        self.assertNotIn('SECRET', json.dumps(data))

    def test_unavailable_source_does_not_erase_other_sources_or_create_queue(self):
        queue = Mock()
        queue.root.exists.return_value = False
        downloads = Mock()
        downloads.list_jobs.side_effect = RuntimeError('SECRET')
        app = FastAPI()
        app.include_router(activity.create_router(queue, downloads, lambda: [{'id': 'legacy'}]))
        with TestClient(app) as client:
            data = client.get('/api/activity').json()
        queue.start.assert_not_called()
        self.assertEqual(data['unavailable'], ['Downloads'])
        self.assertEqual(data['items'], [{'id': 'legacy'}])

    def test_old_active_runs_are_not_hidden_by_newer_history(self):
        queue = Mock()
        queue.root.exists.return_value = True
        queue.lock = threading.RLock()
        queue.paused = False
        complete = dict(spec={'output_name': 'Finished'}, status='succeeded', created_at='2026-09-20T01:00:00Z')
        queue.list.return_value = [dict(complete, id=str(i)) for i in range(110)] + [
            dict(complete, id='active', status='running')]
        queue.logs.return_value = ['steps: 25%|']
        downloads = Mock()
        downloads.list_jobs.return_value = {'jobs': []}
        app = FastAPI()
        app.include_router(activity.create_router(queue, downloads, lambda: []))
        with TestClient(app) as client:
            items = client.get('/api/activity').json()['items']
        self.assertEqual(len(items), 101)
        self.assertEqual(items[0]['id'], 'training:active')
        self.assertEqual(items[0]['progress'], 25)

    def test_diffusion_pipe_completion_records_actual_exit_result(self):
        from apps.Portal import dpipe_api
        saved = dict(dpipe_api._last_activity)
        self.addCleanup(lambda: (dpipe_api._last_activity.clear(), dpipe_api._last_activity.update(saved)))
        proc = Mock(stdout=io.BytesIO(b'steps: 10%|\n'))
        proc.wait.return_value = 1
        with patch.dict(dpipe_api._logs, {}, clear=True), patch.dict(dpipe_api._procs, {}, clear=True):
            dpipe_api._last_activity.update(pid=123, state='running')
            dpipe_api._read_stream(proc, 123)
            self.assertEqual(dpipe_api._last_activity['state'], 'failed')
            dpipe_api._last_activity['state'] = 'stopped'
            proc.stdout = io.BytesIO(b'')
            dpipe_api._read_stream(proc, 123)
            self.assertEqual(dpipe_api._last_activity['state'], 'stopped')


class BuildMetadataTests(unittest.TestCase):
    def test_built_identity_round_trips_and_filters_environment(self):
        import os
        import subprocess
        import sys
        script = Path(__file__).resolve().parents[1] / 'scripts/write-build-info.py'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'build-info.json'
            env = dict(os.environ, BUILD_REVISION='a' * 40, BUILD_DATE='2026-09-20T10:00:00Z', HF_TOKEN='SECRET')
            subprocess.run([sys.executable, str(script), str(path)], env=env, check=True)
            self.assertEqual(diagnostics.build_identity(path), {'revision': 'a' * 40, 'built_at': '2026-09-20T10:00:00Z'})
            self.assertNotIn('SECRET', path.read_text())
            env.update(BUILD_REVISION='unknown', BUILD_DATE='unknown')
            subprocess.run([sys.executable, str(script), str(path)], env=env, check=True)
            self.assertIsNone(diagnostics.build_identity(path)['revision'])
            self.assertIsNotNone(diagnostics.build_identity(path)['built_at'])
