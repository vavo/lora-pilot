import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from apps.Portal.services import runpod, shutdown
from apps.Portal.services.storage_capacity import workspace_capacity


class RunpodTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {'RUNPOD_POD_ID': 'pod-test', 'RUNPOD_API_KEY': 'private-key',
                         'WORKSPACE_ROOT': '/workspace', 'CONTROLPILOT_SETTINGS_PATH': self.tmp.name + '/settings.json'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.pod = {'id': 'pod-test', 'status': 'RUNNING', 'actions': ['stop', 'terminate'], 'locked': False,
                    'cost': 2, 'runtime': {'uptime': 1800}, 'env': {'TOKEN': 'private-env'},
                    'registry': {'password': 'private-registry'},
                    'mounts': {'network': [{'volumeId': 'vol-test', 'path': '/workspace'}]}}
        self.seen = []
        self.volume_status = 200
        self.billing_status = 200
        self.transport = httpx.MockTransport(self.handle)
        self.client = runpod.RunpodClient(self.transport)
        patcher = patch.object(runpod, 'client', self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutdown.cancel_shutdown)

    def handle(self, request):
        self.seen.append(request)
        self.assertEqual(request.url.host, 'api.runpod.io')
        self.assertEqual(request.headers['authorization'], 'Bearer private-key')
        if request.method == 'POST':
            self.assertEqual(request.url.path, '/v2/pods/pod-test/action')
            action = json.loads(request.content)['action']
            return httpx.Response(204) if action == 'terminate' else httpx.Response(200, json={**self.pod, 'status': 'EXITED'})
        if request.url.path == '/v2/pods/pod-test':
            return httpx.Response(200, json=self.pod)
        if request.url.path == '/v2/network-volumes/vol-test':
            return httpx.Response(self.volume_status, json={'id': 'vol-test', 'size': 100, 'type': 'HIGH_PERFORMANCE', 'secret': 'private-volume'})
        self.assertEqual(request.url.path, '/v2/billing/pods')
        self.assertEqual(request.url.params['podId'], 'pod-test')
        self.assertEqual(request.url.params['bucketSize'], 'hour')
        self.assertIn('T00:00:00+00:00', request.url.params['startTime'])
        return httpx.Response(self.billing_status, json={'metadata': {'totals': {'totalAmount': 3, 'gpuAmount': 2,
                 'cpuAmount': 0, 'diskAmount': 1}}, 'secret': 'private-billing'})

    def test_summary_is_allowlisted_and_costs_are_distinct(self):
        app = FastAPI()
        app.include_router(runpod.create_router('/workspace'))
        data = TestClient(app).get('/api/runpod/status').json()
        self.assertEqual(data['hourly_usd'], 2)
        self.assertEqual(data['session_estimate_usd'], 1)
        self.assertEqual(data['billing']['total_usd'], 3)
        self.assertEqual(data['storage']['size_gb'], 100)
        self.assertNotIn('private', json.dumps(data))
        self.assertNotIn('env', data)
        self.assertNotIn('registry', data)
        self.assertEqual(len(self.seen), 3)
        runpod.summary('/workspace')
        self.assertEqual(len(self.seen), 3)  # Cached across browsers and telemetry.

    def test_optional_permissions_do_not_break_pod_information(self):
        self.volume_status = self.billing_status = 403
        data = runpod.summary('/workspace')
        self.assertTrue(data['available'])
        self.assertEqual(data['hourly_usd'], 2)
        for field in ['storage', 'billing']:
            self.assertFalse(data[field]['available'])
            self.assertEqual(data[field]['reason'], 'forbidden')
        runpod.summary('/workspace')
        self.assertEqual(len(self.seen), 3)

    def test_persistent_allocation_does_not_need_volume_permissions(self):
        self.pod['mounts'] = {'persistent': {'size': 50, 'path': '/workspace'}}
        result = workspace_capacity('/workspace', {'mount': '/workspace', 'total': 999999999999}, 10)
        self.assertEqual(result['total'], 50 * 1024**3)
        self.assertEqual(result['capacity_source'], 'runpod')
        self.assertEqual(result['used'], 10)
        self.assertIsNone(result['free'])
        self.assertIsNone(result['pct'])
        self.assertEqual(len(self.seen), 1)

    def test_volume_is_matched_to_workspace_and_unknown_free_is_not_fabricated(self):
        data = runpod.workspace_allocation('/workspace/subdir')
        self.assertTrue(data['available'])
        self.assertFalse(runpod.workspace_allocation('/workspace-other')['available'])
        result = workspace_capacity('/workspace', {'mount': '/workspace', 'total': 2235 * 1024**4}, 52 * 1024**3)
        self.assertEqual(result['total'], 100 * 1024**3)
        self.assertIsNone(result['free'])
        self.assertEqual(result['used'], 52 * 1024**3)

    def test_denied_volume_falls_back_to_configured_allocation(self):
        self.volume_status = 403
        with patch.dict(os.environ, {'WORKSPACE_STORAGE_CAPACITY_GB': '80'}):
            data = workspace_capacity('/workspace', {}, 10)
        self.assertEqual(data['total'], 80 * 1024**3)
        self.assertEqual(data['capacity_source'], 'configured')

    def test_mount_alias_and_workspace_subdirectory_are_matched(self):
        root = Path(self.tmp.name) / 'data'
        root.mkdir()
        alias = Path(self.tmp.name) / 'mount'
        alias.symlink_to(root, target_is_directory=True)
        self.pod['mounts']['network'][0]['path'] = str(alias)
        self.assertTrue(runpod.workspace_allocation(root / 'dataset')['available'])
        self.assertFalse(runpod.workspace_allocation(root.parent)['available'])

    def test_missing_optional_metrics_are_unknown_not_zero(self):
        self.pod['cost'] = None
        self.pod['runtime'] = None
        data = runpod.summary('/workspace')
        self.assertIsNone(data['hourly_usd'])
        self.assertIsNone(data['session_estimate_usd'])
        self.assertTrue(data['billing']['available'])

    def test_malformed_optional_metrics_do_not_break_status(self):
        self.pod.update(cost=10**400, runtime={'uptime': 'unknown'}, status=['RUNNING'], mounts='invalid')
        data = runpod.summary('/workspace')
        self.assertTrue(data['available'])
        self.assertIsNone(data['hourly_usd'])
        self.assertEqual(data['status'], 'UNKNOWN')
        self.assertFalse(data['storage']['available'])
        self.assertTrue(data['billing']['available'])

    def test_auto_plan_uses_api_mounts_not_environment_guesses(self):
        with patch.dict(os.environ, {'RUNPOD_VOLUME_TYPE': 'local'}):
            plan = shutdown._runpod_shutdown_plan()
        self.assertEqual(plan['action'], 'terminate')
        self.pod['mounts'] = {'persistent': {'size': 50, 'path': '/workspace'}}
        with patch.dict(os.environ, {'RUNPOD_NETWORK_VOLUME_ID': 'stale-hint'}):
            self.assertEqual(shutdown._runpod_shutdown_plan()['action'], 'stop')
        self.pod['mounts'] = {'network': [{'volumeId': 'vol-test', 'path': '/elsewhere'}]}
        self.assertEqual(shutdown._runpod_shutdown_plan()['action'], 'stop')

    def test_explicit_stop_overrides_auto_and_execution_does_not_change_action(self):
        Path(os.environ['CONTROLPILOT_SETTINGS_PATH']).write_text('{"shutdown_mode":"stop"}')
        plan = shutdown._runpod_shutdown_plan()
        self.assertEqual(plan['action'], 'stop')
        Path(os.environ['CONTROLPILOT_SETTINGS_PATH']).write_text('{"shutdown_mode":"remove"}')
        with patch.object(shutdown.subprocess, 'run') as local:
            shutdown._execute_shutdown(plan)
            local.assert_not_called()
        self.assertEqual(json.loads(self.seen[-1].content), {'action': 'stop'})

    def test_termination_accepts_empty_204(self):
        plan = shutdown._runpod_shutdown_plan()
        shutdown._execute_shutdown(plan)
        self.assertEqual(json.loads(self.seen[-1].content), {'action': 'terminate'})

    def test_locks_and_ineligible_actions_prevent_schedule_and_execution(self):
        plan = shutdown._runpod_shutdown_plan()
        self.pod['locked'] = True
        with self.assertRaises(HTTPException) as error:
            shutdown.schedule_shutdown(shutdown.ShutdownRequest(value=1, unit='minutes'))
        self.assertEqual(error.exception.status_code, 409)
        with self.assertRaises(runpod.RunpodError):
            shutdown._execute_shutdown(plan)
        self.assertFalse(any(request.method == 'POST' for request in self.seen))
        self.pod['locked'] = False
        self.pod['actions'] = ['start']
        with self.assertRaises(runpod.RunpodError):
            shutdown._runpod_shutdown_plan()

    def test_no_credentials_prevents_timer_without_exposing_secrets(self):
        with patch.dict(os.environ, {'RUNPOD_API_KEY': ''}), patch.object(Path, 'home', return_value=Path(self.tmp.name)):
            data = runpod.summary('/workspace')
            self.assertEqual(data['reason'], 'no_credentials')
            with self.assertRaises(HTTPException):
                shutdown.schedule_shutdown(shutdown.ShutdownRequest(value=1, unit='minutes'))
        self.assertFalse(shutdown.get_shutdown_status().scheduled)
        self.assertEqual(self.seen, [])

    def test_schedule_captures_action_and_cancel_clears_it(self):
        with patch.object(shutdown.threading, 'Thread'):
            shutdown.schedule_shutdown(shutdown.ShutdownRequest(value=30, unit='minutes'))
            status = shutdown.get_shutdown_status()
            self.assertTrue(status.scheduled)
            self.assertEqual(status.action, 'terminate')
            self.assertIn('local storage', status.notice)
            self.assertNotIn('private', status.model_dump_json())
            self.assertFalse(any(request.method == 'POST' for request in self.seen))
            shutdown.cancel_shutdown()
            self.assertIsNone(shutdown.get_shutdown_status().action)
        shutdown.shutdown_thread = None

    def test_status_route_obeys_controlpilot_authentication(self):
        from apps.Portal import app as portal
        with patch.object(portal, '_controlpilot_request_authenticated', return_value=False):
            response = TestClient(portal.app).get('/api/runpod/status')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.seen, [])

    def test_injected_cli_credentials_and_env_precedence(self):
        root = Path(self.tmp.name)
        (root / '.runpod').mkdir()
        (root / '.runpod/config.toml').write_text('apikey="injected-key"\n')
        with patch.object(Path, 'home', return_value=root):
            self.assertEqual(runpod.api_key(), 'private-key')
            with patch.dict(os.environ, {'RUNPOD_API_KEY': ''}):
                self.assertEqual(runpod.api_key(), 'injected-key')

    def test_local_shutdown_remains_local_and_provider_failure_never_falls_back(self):
        with patch.dict(os.environ, {'RUNPOD_POD_ID': ''}), patch.object(shutdown.subprocess, 'run', return_value=Mock(returncode=0)) as local:
            self.assertIsNone(shutdown._runpod_shutdown_plan())
            self.assertEqual(runpod.summary('/workspace'), {'enabled': False})
            shutdown._execute_shutdown(None)
            self.assertEqual(local.call_args.args[0], ['shutdown', '-h', 'now'])
        with patch.object(self.client, 'action', side_effect=runpod.RunpodError('forbidden', 'Denied', 403)), patch.object(shutdown.subprocess, 'run') as local:
            with self.assertRaises(runpod.RunpodError):
                shutdown._execute_shutdown({'pod_id': 'pod-test', 'action': 'stop'})
            local.assert_not_called()

    def test_error_responses_are_safe_and_writes_are_not_retried(self):
        for status in [401, 403, 404, 409, 422, 429, 500, 302]:
            seen = []
            def respond(request):
                seen.append(request)
                return httpx.Response(status, json={'detail': 'private-key private-env'}, headers={'Location': 'https://elsewhere.invalid'})
            client = runpod.RunpodClient(httpx.MockTransport(respond))
            with self.assertRaises(runpod.RunpodError) as error:
                client.action('pod-test', 'stop')
            self.assertNotIn('private', str(error.exception))
            self.assertEqual(len(seen), 1)

    def test_rate_limit_read_cooldown_honors_retry_after(self):
        seen = []
        def respond(request):
            seen.append(request)
            return httpx.Response(429, headers={'Retry-After': '120'})
        client = runpod.RunpodClient(httpx.MockTransport(respond))
        for now in [0, 60, 121]:
            with patch.object(runpod.time, 'monotonic', return_value=now), self.assertRaises(runpod.RunpodError):
                client.pod('pod-test')
        self.assertEqual(len(seen), 2)

    def test_invalid_ids_never_reach_network(self):
        for identifier in ['../account/secrets', 'pod?x=1', 'a/b', '']:
            with self.assertRaises(runpod.RunpodError):
                self.client.pod(identifier)
        self.assertEqual(self.seen, [])
