import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.Portal.services import service_registry as registry

ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / 'supervisor/supervisord.conf'


class ServiceRegistryTests(unittest.TestCase):
    def test_bundled_supervisor_agrees(self):
        self.assertEqual(registry.validate_supervisor(CONF), [])

    def test_mismatches_identify_missing_extra_logs_and_launcher(self):
        source = CONF.read_text().replace('[program:comfy]', '[program:wrong-comfy]')
        source = source.replace('/workspace/logs/kohya.err.log', '/workspace/logs/wrong.log')
        source = source.replace('/opt/pilot/invoke.sh', '/opt/pilot/wrong.sh')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'supervisord.conf'; path.write_text(source)
            errors = registry.validate_supervisor(path)
        self.assertIn('Missing Supervisor program: comfy', errors)
        self.assertIn('Unregistered Supervisor program: wrong-comfy', errors)
        self.assertTrue(any('kohya: stderr_logfile' in e for e in errors))
        self.assertTrue(any('invoke: command' in e for e in errors))

    def test_port_overrides_match_launchers_and_bad_ports_do_not_fall_back(self):
        for name, spec in registry.SERVICES.items():
            launcher = (ROOT / 'scripts' / spec['launcher']).read_text()
            env = spec['port_env'][-1]
            self.assertIn('${' + env + ':-' + str(spec['port']) + '}', launcher, name)
            self.assertEqual(registry.service_port(name, {env: '12345'}), 12345)
            for value in ('0', '65536', 'bad', '8080/path'):
                self.assertIsNone(registry.service_port(name, {env: value}))
        self.assertEqual(registry.service_port('invoke', {'INVOKEAI_PORT': '9123', 'INVOKE_PORT': '9000'}), 9123)
        self.assertEqual(registry.local_url('copilot', {'COPILOT_SIDECAR_PORT': '7880'}), 'http://127.0.0.1:7880')

    def test_public_metadata_has_only_browser_fields(self):
        payload = {name: registry.public_definition(name, {'GH_TOKEN': 'secret'}) for name in registry.SERVICES}
        text = json.dumps(payload)
        for private in ('secret', 'repo_dir', 'python_bin', 'launcher', '/workspace/logs', 'port_env'):
            self.assertNotIn(private, text)
        self.assertFalse(payload['copilot']['capabilities']['open'])
        self.assertFalse(payload['controlpilot']['capabilities']['open'])
        self.assertTrue(payload['comfy']['capabilities']['open'])
        self.assertEqual(payload['kohya']['capabilities']['tensorboard'], 'kohya')
        self.assertEqual([name for name, value in payload.items() if value['capabilities']['update']], ['invoke'])

    def test_status_rejects_errors_or_a_different_program(self):
        self.assertEqual(registry.supervisor_state('comfy', 'comfy RUNNING pid 42'), 'RUNNING')
        for output in ('comfy: ERROR (no such process)', 'kohya RUNNING pid 42', '', 'comfy surprise'):
            self.assertEqual(registry.supervisor_state('comfy', output), 'UNKNOWN')

    def test_service_api_preserves_fields_and_reports_resolved_metadata(self):
        from apps.Portal import app as portal
        with patch.object(portal, 'SUPERVISORCTL', '/fixture/supervisorctl'), \
             patch.object(portal.subprocess, 'check_output', return_value='comfy RUNNING pid 42'), \
             patch.object(portal, '_read_service_autostart', return_value=True), \
             patch.dict(os.environ, COMFY_PORT='5566'):
            entry = portal.supervisor_status('comfy').model_dump()
        self.assertEqual(entry['name'], 'comfy')
        self.assertEqual(entry['state_raw'], 'RUNNING')
        self.assertTrue(entry['running'])
        self.assertTrue(entry['autostart'])
        self.assertEqual(entry['display'], entry['definition']['label'])
        self.assertEqual(entry['definition']['port'], 5566)
        self.assertEqual(portal.SERVICE_LOGS, registry.SERVICE_LOGS)
        self.assertEqual(portal.SERVICE_UPDATE_SPECS, registry.VERSION_SPECS)

    def test_updater_can_load_registry_in_packaged_image_layout(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            services = root / 'apps/Portal/services'; services.mkdir(parents=True)
            shutil.copy(ROOT / 'apps/Portal/services/service_registry.py', services)
            shutil.copy(ROOT / 'scripts/service-updates-reconcile.py', root)
            result = subprocess.run([os.sys.executable, str(root / 'service-updates-reconcile.py'), '--help'],
                                    cwd=temp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_ai_toolkit_preserves_worker_and_uses_requested_port(self):
        section = (ROOT / 'scripts/ai-toolkit.sh').read_text().split('PORT="${AI_TOOLKIT_PORT', 1)[1]
        section = 'PORT="${AI_TOOLKIT_PORT' + section
        with tempfile.TemporaryDirectory() as temp:
            launcher = Path(temp) / 'node_modules/.bin/concurrently'; launcher.parent.mkdir(parents=True)
            launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n'); launcher.chmod(0o755)
            result = subprocess.run(['bash', '-c', section], cwd=temp, env=dict(os.environ, AI_TOOLKIT_PORT='8765'), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('node dist/cron/worker.js', result.stdout)
            self.assertIn('node dist/cron/fileServer.js start --port 8765', result.stdout)
            invalid = subprocess.run(['bash', '-c', section], cwd=temp, env=dict(os.environ, AI_TOOLKIT_PORT='8675; echo unsafe'), capture_output=True, text=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertNotIn('unsafe', invalid.stdout)

    def test_copilot_client_uses_configured_port_without_breaking_portal_on_invalid_port(self):
        import asyncio
        import httpx
        from apps.Portal import app as portal
        from fastapi import HTTPException
        with patch.object(portal, 'COPILOT_SIDECAR_URL', ''), \
             patch.dict(os.environ, COPILOT_SIDECAR_PORT='7880'), \
             patch.object(portal.httpx, 'AsyncClient') as client:
            request = client.return_value.__aenter__.return_value.request
            request.return_value = httpx.Response(200, json={'reachable': True})
            asyncio.run(portal._copilot_sidecar_request('GET', '/status'))
            self.assertEqual(request.call_args.args[1], 'http://127.0.0.1:7880/status')
        with patch.object(portal, 'COPILOT_SIDECAR_URL', ''), patch.dict(os.environ, COPILOT_SIDECAR_PORT='bad'):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(portal._copilot_sidecar_request('GET', '/status'))
            self.assertEqual(caught.exception.status_code, 503)

    def test_stopped_comfy_still_reports_resolved_port(self):
        import requests
        from apps.Portal.services.comfy import create_router
        router = create_router(Path('/unused'))
        endpoint = next(route.endpoint for route in router.routes if route.path == '/api/comfy/status')
        with patch.dict(os.environ, COMFY_PORT='5566'), patch('requests.get', side_effect=requests.ConnectionError('offline')):
            result = endpoint()
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['port'], '5566')
