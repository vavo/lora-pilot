"""MCP P/A/F/R gates using disposable workspaces and the real SDK."""
import asyncio
import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient

from apps.Portal.mcp_server.admin import create_app
from apps.Portal.mcp_server.contracts import READ_SCOPES
from apps.Portal.mcp_server.facade import Facade
from apps.Portal.mcp_server.files import Files, Rejected
from apps.Portal.mcp_server.server import Boundary, Runtime, RateLimit
from apps.Portal.mcp_server.store import Store


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'datasets/1_private').mkdir(parents=True)
        from PIL import Image
        Image.new('RGB', (32, 32)).save(self.root / 'datasets/1_private/a.png')
        (self.root / 'datasets/1_private/a.txt').write_text('private caption canary')
        self.store = Store(self.root)
        self.store.initialize()
        self.store.set_enabled(True)
        self.addCleanup(self.store.close)
        self.a, self.token = self.store.create_client('A', sorted(READ_SCOPES), ['1_private'], [])
        self.b, self.token_b = self.store.create_client('B', sorted(READ_SCOPES), [], [])
        self.queue = SimpleNamespace(paused=True, start=Mock(), submit=Mock())
        self.manifest = self.root / 'bundled.manifest'
        self.manifest.write_text('demo|hf_file|org/repo:model.safetensors|checkpoints||100\n')
        self.facade = Facade(self.store, self.queue, self.root / 'models', self.manifest)
        self.runtime = Runtime(self.facade, 'http://127.0.0.1:7878')

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mode)
                for p in (self.root / 'datasets').rglob('*') if p.is_file()}

    def app(self):
        app = FastAPI()
        app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
        app.add_middleware(Boundary, runtime=self.runtime)
        self.runtime.admin = create_app(self.runtime, lambda: True,
            lambda request: request.cookies.get('owner') == 'session', lambda: 'session-value', lambda value: value == 'correct')
        return app


class AccessTests(Workspace):
    def test_A01_A05_A12_tokens_are_scoped_revocable_and_rotatable(self):
        self.assertEqual(self.store.authenticate(self.token)['id'], self.a)
        for token in ['', 'cookie-canary', 'hf_canary', self.token + 'x']:
            with self.subTest(token=token), self.assertRaises(Rejected):
                self.store.authenticate(token)
        new = self.store.rotate(self.a)
        with self.assertRaises(Rejected):
            self.store.authenticate(self.token)
        self.assertEqual(self.store.authenticate(new)['id'], self.a)
        self.store.revoke(self.a)
        with self.assertRaises(Rejected):
            self.store.authenticate(new)
        state = (self.root / 'config/mcp/state.json').read_text()
        self.assertNotIn(new, state)
        self.assertNotIn(self.token_b, state)

    def test_A13_corrupt_state_and_unknown_schema_fail_closed(self):
        path = self.root / 'config/mcp/state.json'
        for value in ['{', '{"version":99}', '{}']:
            path.write_text(value)
            with self.subTest(value=value), self.assertRaises((ValueError, Rejected)):
                self.store.authenticate(self.token)

    def test_A12_renewal_preserves_identity_but_cannot_restore_revoked_client(self):
        with self.store.transaction() as data:
            data['clients'][self.a]['expires_at'] = 1
        with self.assertRaises(Rejected):
            self.store.authenticate(self.token)
        self.store.change_client(self.a, 'Renewed', ['workspace:read'], [], [], 1, {})
        self.assertEqual(self.store.authenticate(self.token)['id'], self.a)
        self.store.revoke(self.a)
        with self.assertRaises(Rejected):
            self.store.change_client(self.a, 'Renewed', ['workspace:read'], [], [], 1, {})

    def test_A13_corrupt_automation_policy_fails_closed(self):
        from pydantic import ValidationError
        data = self.store.read()
        data['clients'][self.a]['policy'] = {'enabled': 'true', 'max_steps': -1}
        (self.root / 'config/mcp/state.json').write_text(json.dumps(data))
        with self.assertRaises(ValidationError):
            self.store.authenticate(self.token)

    def test_O10_offline_bootstrap_refuses_active_owner_and_grants_only_reads(self):
        import subprocess
        import sys
        command = [sys.executable, '-m', 'apps.Portal.mcp_server.cli', '--workspace', str(self.root),
                   'create-read-client', '--label', 'Offline', '--dataset', '1_private']
        self.store.claim()
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.store.close()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        token = json.loads(result.stdout)['token']
        self.assertEqual(set(self.store.authenticate(token)['scopes']), READ_SCOPES)

    def test_A04_cross_client_objects_and_cursors(self):
        first = self.facade.call(self.a, 'datasets_list', {})
        dataset_id = first['items'][0]['dataset_id']
        self.assertEqual(self.facade.call(self.b, 'datasets_list', {})['items'], [])
        with self.assertRaises(Rejected):
            self.facade.call(self.b, 'dataset_review', {'dataset_id': dataset_id})
        cursor = self.facade.page(self.store.principal(self.a), 'test', list(range(5)), None, 1)['next_cursor']
        with self.assertRaises(Rejected):
            self.facade.page(self.store.principal(self.b), 'test', list(range(5)), cursor, 1)

    def test_Q01_F06_R03_reads_leave_source_and_queue_untouched(self):
        before = self.snapshot()
        dataset = next(iter(self.store.principal(self.a)['datasets']))
        result = self.facade.call(self.a, 'dataset_review', {'dataset_id': dataset})
        self.assertEqual(result['images'], 1)
        self.assertNotIn('private caption canary', json.dumps(result))
        self.assertTrue(self.facade.call(self.a, 'workspace_status', {})['queue_paused'])
        self.assertEqual(self.facade.call(self.a, 'runs_list', {})['items'], [])
        self.facade.call(self.a, 'models_list', {})
        self.assertFalse((self.root / 'models').exists())
        self.assertEqual(self.snapshot(), before)
        self.queue.start.assert_not_called()
        self.queue.submit.assert_not_called()

    def test_P05_extra_fields_and_mutations_rejected(self):
        from pydantic import ValidationError
        for key in ['path', 'url', 'command', 'env', '_template', 'confirmed', 'toml_path']:
            with self.subTest(key=key), self.assertRaises(ValidationError):
                self.facade.call(self.a, 'workspace_status', {key: 'canary'})
        for name in ['training_start', 'run_cancel', 'call_api', 'delete_dataset']:
            with self.subTest(name=name), self.assertRaises(Rejected):
                self.facade.call(self.a, name, {})

    def test_F01_F02_component_links_special_files_and_traversal(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'secret').write_text('outside-secret')
        (self.root / 'datasets/link').symlink_to(outside, target_is_directory=True)
        for path in ['../outside/secret', '/etc/passwd', 'datasets/link/secret', 'datasets/../outside/secret', 'datasets\\x']:
            with self.subTest(path=path), self.assertRaises((OSError, Rejected)):
                with self.store.files.open(path):
                    self.fail('unsafe open succeeded')
        target = self.root / 'datasets/1_private/a.txt'
        os.link(outside / 'secret', target.with_name('hardlink.txt'))
        with self.assertRaises(Rejected):
            with self.store.files.open('datasets/1_private/hardlink.txt'):
                self.fail('hardlink open succeeded')
        os.mkfifo(target.with_name('fifo'))
        with self.assertRaises(Rejected):
            with self.store.files.open('datasets/1_private/fifo'):
                self.fail('FIFO open succeeded')
        self.assertEqual((outside / 'secret').read_text(), 'outside-secret')

    def test_F11_private_state_permissions(self):
        for relative in ['config/mcp', 'config/mcp/state.json']:
            path = self.root / relative
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700 if path.is_dir() else 0o600)
            previous = path.stat().st_mode
            path.chmod(0o777)
            with self.assertRaises(Rejected):
                self.store.authenticate(self.token)
            path.chmod(previous)

    def test_P10_R04_bounded_pagination_and_rate_buckets(self):
        limiter = RateLimit(limit=2, capacity=2, clock=lambda: 1)
        self.assertTrue(limiter.allow('a'))
        self.assertTrue(limiter.allow('a'))
        self.assertFalse(limiter.allow('a'))
        self.assertTrue(limiter.allow('b'))
        self.assertFalse(limiter.allow('c'))
        self.assertEqual(len(limiter.buckets), 2)


class ProtocolTests(Workspace):
    def test_P01_invalid_configuration_disables_only_mcp(self):
        self.runtime = Runtime(self.facade, 'http://public.example')
        self.assertEqual(self.runtime.failure, 'MCP_UNAVAILABLE')
        with TestClient(self.app()) as client:
            self.assertEqual(client.get('/mcp').status_code, 503)

    def test_P02_A03_current_and_legacy_sdk_roundtrips(self):
        import httpx2
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client

        async def run():
            app = self.app()
            await self.runtime.start()
            self.assertIsNone(self.runtime.failure)
            try:
                for mode in ['2026-07-28', 'legacy']:
                    with self.subTest(mode=mode):
                        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),
                            headers={'Authorization': 'Bearer ' + self.token}) as http:
                            transport = streamable_http_client('http://127.0.0.1:7878/mcp', http_client=http)
                            async with Client(transport, mode=mode) as client:
                                listing = await client.list_tools()
                                self.assertIn('workspace_status', [tool.name for tool in listing.tools])
                                self.assertNotIn('training_start', [tool.name for tool in listing.tools])
                                result = await client.call_tool('workspace_status', {})
                                self.assertFalse(result.is_error, result)
                                self.assertTrue(result.structured_content['queue_paused'])
                                failed = await client.call_tool('workspace_status', {'secret': 'do-not-echo-canary'})
                                self.assertTrue(failed.is_error)
                                self.assertNotIn('do-not-echo-canary', failed.model_dump_json())
            finally:
                await self.runtime.stop()
        asyncio.run(run())

    def test_P04_P06_O07_O09_http_boundary(self):
        self.runtime.setup_sdk()
        with TestClient(self.app(), base_url='http://127.0.0.1:7878') as client:
            headers = {'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'}
            for body in ['[]', '{', '{"method":"a","method":"b"}', '{"x":NaN}', '[' * 1000]:
                with self.subTest(body=body[:50]):
                    self.assertEqual(client.post('/mcp', headers=headers, content=body).status_code, 400)
            self.assertEqual(client.post('/mcp', headers=headers, content=b'x' * (64 * 1024 + 1)).status_code, 413)
            for origin in ['null', 'https://evil.example', 'http://127.0.0.1:7878.evil.example']:
                self.assertEqual(client.options('/mcp', headers={'Origin': origin}).status_code, 403)
            self.assertEqual(client.post('/mcp', headers={**headers, 'Host': 'evil.example'}, json={}).status_code, 403)
            self.assertEqual(client.post('/mcp', json={}).status_code, 401)
            self.assertEqual(client.post('/mcp', headers={'Cookie': 'owner=session'}, json={}).status_code, 401)
            self.assertEqual(client.post('/mcp/', headers=headers, json={}).status_code, 404)
            self.assertEqual(client.post('/mcp?token=canary', headers=headers, json={}).status_code, 400)
            self.assertEqual(client.post('/mcp', headers={**headers, 'Content-Encoding': 'gzip'}, content=b'x').status_code, 400)
            response = client.options('/mcp', headers={'Origin': self.runtime.origin, 'Access-Control-Request-Method': 'POST'})
            self.assertEqual(response.headers['access-control-allow-origin'], self.runtime.origin)
            self.assertNotIn('*', response.headers['access-control-allow-origin'])

    def test_A09_A14_owner_settings_csrf_and_password(self):
        self.runtime.setup_sdk()
        with TestClient(self.app(), base_url='http://127.0.0.1:7878', raise_server_exceptions=False) as client:
            self.assertEqual(client.get('/api/settings/mcp').status_code, 403)
            client.cookies.set('owner', 'session')
            result = client.get('/api/settings/mcp').json()
            self.assertNotIn('token_hash', json.dumps(result))
            headers = {'Origin': self.runtime.origin, 'X-MCP-CSRF': result['csrf']}
            for changes in [{}, {'Origin': 'null'}, {'X-MCP-CSRF': 'wrong'}]:
                self.assertEqual(client.post('/api/settings/mcp', headers=changes, json={'enabled': True, 'password': 'correct'}).status_code, 403)
            self.assertEqual(client.post('/api/settings/mcp', headers=headers, json={'enabled': True, 'password': 'wrong'}).status_code, 403)
            self.assertEqual(client.post('/api/settings/mcp', headers=headers, json={'enabled': True, 'password': 'correct'}).status_code, 200)
            result = client.post('/api/settings/mcp/clients', headers=headers,
                json={'password': 'correct', 'label': '<img src=x onerror=alert(1)>', 'scopes': ['workspace:read']})
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.json()['token'].startswith('lp_mcp_'))
            identifier = result.json()['id']
            change = dict(password='correct', label='Edited', scopes=['datasets:inspect'], datasets=['1_private'])
            self.assertEqual(client.patch('/api/settings/mcp/clients/' + identifier, json=change).status_code, 403)
            self.assertEqual(client.patch('/api/settings/mcp/clients/' + identifier, headers=headers, json=change).status_code, 200)
            self.assertEqual(len(self.store.principal(identifier)['datasets']), 1)
            self.assertEqual(client.post('/api/settings/mcp', headers=headers, content=b'x' * 65537).status_code, 413)
            invalid = client.post('/api/settings/mcp/clients', headers=headers, json={'password': 'secret-input-canary', 'unexpected': True})
            self.assertNotIn('secret-input-canary', invalid.text)


if __name__ == '__main__':
    unittest.main()
