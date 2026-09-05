import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from apps.Portal.services.comfy_access import read_policy, token_matches
try:
    from fastapi.testclient import TestClient
    from apps.Portal import app as portal
except ModuleNotFoundError as exc:
    if exc.name not in {"fastapi", "httpx"}:
        raise
    portal = None


class ComfyPolicyTests(unittest.TestCase):
    def test_default_and_corruption_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'policy.json'
            self.assertFalse(read_policy(path)['enabled'])
            for content in ['broken', '{}', '{"enabled":"false"}', '{"enabled":true,"token_hash":"bad"}']:
                path.write_text(content)
                with self.assertRaises(ValueError):
                    read_policy(path)

    def test_bearer_token_hash(self):
        policy = {'enabled': True, 'token_hash': hashlib.sha256(b'test-token').hexdigest()}
        self.assertTrue(token_matches('Bearer test-token', policy))
        self.assertFalse(token_matches('Bearer wrong', policy))
        self.assertFalse(token_matches('Basic test-token', policy))
        self.assertFalse(token_matches('Bearer test-token', {'token_hash': ''}))

    def test_launcher_policy_selects_binding(self):
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'policy.json'
            for enabled, expected in [(False, '0.0.0.0'), (True, '127.0.0.1')]:
                path.write_text(json.dumps({'enabled': enabled, 'token_hash': ''}))
                result = subprocess.check_output([sys.executable, 'apps/Portal/services/comfy_access.py', str(path)], text=True)
                self.assertEqual(result.strip(), expected)
            path.write_text('invalid')
            result = subprocess.run([sys.executable, 'apps/Portal/services/comfy_access.py', str(path)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b'0.0.0.0', result.stdout)


@unittest.skipIf(portal is None, 'Portal test dependencies unavailable')
class ComfyAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, value in [('CONFIG_DIR', self.root), ('CONTROLPILOT_SETTINGS_PATH', self.root / 'settings.json')]:
            patcher = patch.object(portal, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(portal.app)
        self.addCleanup(self.client.close)
        self.origin = {'Origin': 'http://testserver'}

    def login(self):
        settings = portal._default_controlpilot_settings()
        settings.update(password_enabled=True, password_hash=portal._hash_controlpilot_password('test-password'))
        portal._write_controlpilot_settings(settings)
        response = self.client.post('/api/settings/auth/login', json={'password': 'test-password'})
        self.assertEqual(response.status_code, 200)

    def policy(self, enabled=True, token='test-token'):
        portal._save_comfy_policy({'enabled': enabled, 'token_hash': hashlib.sha256(token.encode()).hexdigest() if token else ''})

    def test_toggle_requires_password_and_authenticated_same_origin(self):
        response = self.client.post('/api/settings/comfy/protection', json={'enabled': True}, headers=self.origin)
        self.assertEqual(response.status_code, 422)
        self.login()
        response = self.client.post('/api/settings/comfy/protection', json={'enabled': True}, headers={'Origin':'https://evil.example'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(portal._comfy_policy()['enabled'])

    def test_toggle_stops_before_saving_and_starts_after(self):
        self.login()
        observed = []
        def supervisor(action, name, **kwargs):
            observed.append((action, portal._comfy_policy()['enabled']))
        with patch.object(portal, 'supervisor_status') as status, patch.object(portal, '_run_supervisorctl', side_effect=supervisor):
            status.return_value.state = 'RUNNING'
            response = self.client.post('/api/settings/comfy/protection', json={'enabled': True}, headers=self.origin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed, [('stop', False), ('start', True)])
        self.assertEqual((self.root / 'comfy-access.json').stat().st_mode & 0o777, 0o600)

    def test_stop_failure_does_not_change_policy(self):
        self.login()
        with patch.object(portal, 'supervisor_status') as status, patch.object(portal, '_run_supervisorctl', side_effect=RuntimeError('failed')):
            status.return_value.state = 'RUNNING'
            response = self.client.post('/api/settings/comfy/protection', json={'enabled': True}, headers=self.origin)
        self.assertEqual(response.status_code, 503)
        self.assertFalse(portal._comfy_policy()['enabled'])

    def test_start_failure_keeps_saved_protection(self):
        self.login()
        with patch.object(portal, 'supervisor_status') as status, patch.object(portal, '_run_supervisorctl', side_effect=RuntimeError('failed')):
            status.return_value.state = 'STOPPED'
            response = self.client.post('/api/settings/comfy/protection', json={'enabled': True}, headers=self.origin)
        self.assertEqual(response.status_code, 503)
        self.assertTrue(portal._comfy_policy()['enabled'])

    def test_token_rotation_revocation_and_secret_redaction(self):
        self.login()
        self.policy()
        response = self.client.post('/api/settings/comfy/token', headers=self.origin)
        token = response.json()['token']
        self.assertIn('no-store', response.headers['cache-control'])
        self.assertTrue(token_matches('Bearer '+token, portal._comfy_policy()))
        self.assertNotIn(token, (self.root / 'comfy-access.json').read_text())
        self.assertNotIn('token_hash', self.client.get('/api/settings').text)
        self.assertNotIn(token, self.client.get('/api/settings').text)
        self.client.post('/api/settings/comfy/token', headers=self.origin)
        self.assertFalse(token_matches('Bearer '+token, portal._comfy_policy()))
        self.client.delete('/api/settings/comfy/token', headers=self.origin)
        self.assertEqual(portal._comfy_policy(), {'enabled': True, 'token_hash': ''})
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/comfy/system_stats', headers={'Authorization': 'Bearer '+token}).status_code, 401)

    def test_password_cannot_be_removed_while_protected(self):
        self.login()
        self.policy()
        response = self.client.post('/api/settings/password', json={'enabled': False}, headers=self.origin)
        self.assertEqual(response.status_code, 409)
        response = self.client.post('/api/settings/password', json={'enabled': True, 'password': 'changed'}, headers={'Origin':'https://evil.example'})
        self.assertEqual(response.status_code, 403)

    def test_gateway_denies_anonymous_and_tokens_do_not_access_controlpilot(self):
        self.login()
        self.policy()
        self.client.cookies.clear()
        for path in ['/comfy/system_stats','/comfy/view?filename=secret.png','/comfy/assets/index.js']:
            self.assertEqual(self.client.get(path).status_code, 401)
        response = self.client.get('/api/settings', headers={'Authorization':'Bearer test-token'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get('/comfy/', headers={'Accept':'text/html'}, follow_redirects=False).status_code, 303)

    def test_cookie_csrf_and_corrupt_policy(self):
        self.login()
        self.policy()
        for origin in ['', 'https://evil.example']:
            response = self.client.post('/comfy/prompt', json={}, headers={'Origin':origin})
            self.assertEqual(response.status_code, 401)
        (self.root / 'comfy-access.json').write_text('broken')
        self.assertEqual(self.client.get('/comfy/system_stats').status_code, 401)
        self.assertEqual(self.client.get('/api/settings').status_code, 503)

    def test_websocket_denies_anonymous_and_foreign_origin(self):
        from starlette.websockets import WebSocketDisconnect
        self.login()
        self.policy()
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect('/comfy/ws', headers={'Origin':'https://evil.example'}):
                pass
        self.client.cookies.clear()
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect('/comfy/ws'):
                pass

    def test_http_proxy_streams_methods_queries_and_filters_credentials(self):
        import httpx
        real_client = httpx.AsyncClient
        seen = []
        class Body(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'video-part'
        async def upstream(request):
            seen.append((request.method, str(request.url), dict(request.headers), await request.aread()))
            return httpx.Response(206, headers={'Content-Range':'bytes 0-9/20', 'Content-Type':'video/mp4'}, stream=Body())
        def client(**kwargs):
            return real_client(transport=httpx.MockTransport(upstream), **kwargs)
        with patch('apps.Portal.services.comfy.httpx.AsyncClient', side_effect=client):
            # No policy: existing unauthenticated access works.
            response = self.client.get('/comfy/view?filename=a%20b.mp4', headers={'Range':'bytes=0-9'})
            self.assertEqual(response.content, b'video-part')
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response.headers['content-range'], 'bytes 0-9/20')
            self.policy()
            for method in ['POST','PUT','PATCH','DELETE']:
                response = self.client.request(method, '/comfy/api/prompt', content=b'payload',
                    headers={'Authorization':'Bearer test-token', 'Cookie':'private=value', 'Connection':'x-secret', 'x-secret':'hidden'})
                self.assertEqual(response.status_code, 206)
            self.login()
            response = self.client.post('/comfy/upload/image', content=b'multipart-placeholder', headers=self.origin)
            self.assertEqual(response.status_code, 206)
        self.assertIn('filename=a%20b.mp4', seen[0][1])
        self.assertEqual(seen[1][3], b'payload')
        for _, _, headers, _ in seen:
            self.assertNotIn('authorization', headers)
            self.assertNotIn('cookie', headers)
            self.assertNotIn('x-secret', headers)

    def test_websocket_relays_binary_and_text_and_preserves_client_id(self):
        import asyncio
        from contextlib import asynccontextmanager
        self.policy()
        urls = []
        class Upstream:
            def __init__(self):
                self.queue = asyncio.Queue()
            def __aiter__(self):
                return self
            async def __anext__(self):
                return await self.queue.get()
            async def send(self, message):
                await self.queue.put(message)
        @asynccontextmanager
        async def connect(url, **kwargs):
            urls.append(url)
            yield Upstream()
        with patch('apps.Portal.services.comfy.websockets.connect', connect):
            with self.client.websocket_connect('/comfy/ws?clientId=test-client', headers={'Authorization':'Bearer test-token'}) as ws:
                ws.send_text('progress')
                self.assertEqual(ws.receive_text(), 'progress')
                ws.send_bytes(b'\x00\x01preview')
                self.assertEqual(ws.receive_bytes(), b'\x00\x01preview')
                self.policy(token='')
                ws.send_text('after-revocation')
                from starlette.websockets import WebSocketDisconnect
                with self.assertRaises(WebSocketDisconnect):
                    ws.receive_text()
        self.assertTrue(urls[0].endswith('/ws?clientId=test-client'))
