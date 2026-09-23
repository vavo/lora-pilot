"""Exercise the native listener, including requests forwarded from localhost."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apps.Portal.services.comfy_access import (
    INTERNAL_HEADER, direct_access_middleware, install_direct_access, internal_headers,
)
try:
    from aiohttp import web, WSServerHandshakeError
    from aiohttp.test_utils import TestClient, TestServer
except ModuleNotFoundError:
    web = None


class ComfyInstallTests(unittest.TestCase):
    def test_installs_before_all_other_middleware_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'server.py'
            path.write_text('class Server:\n    def __init__(self):\n'
                            '        self.app = web.Application(client_max_size=max_upload_size, middlewares=middlewares)\n')
            install_direct_access(path)
            first = path.read_text()
            install_direct_access(path)
            self.assertEqual(first, path.read_text())
            import sys
            from apps.Portal.services import comfy_access
            with patch.dict(sys.modules, {'comfy_access': comfy_access}):
                from unittest.mock import Mock
                existing = object()
                namespace = {'web': Mock(), 'max_upload_size': 1024, 'middlewares': [existing]}
                exec(compile(first, str(path), 'exec'), namespace)
                namespace['Server']()
                middleware = namespace['web'].Application.call_args.kwargs['middlewares']
                self.assertEqual(middleware[0].__name__, 'authenticate')
                self.assertIs(middleware[1], existing)
            path.write_text('upstream changed')
            with self.assertRaises(ValueError):
                install_direct_access(path)

    def test_launcher_installs_and_exports_module_path_before_starting_comfy(self):
        import shlex
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'config').mkdir()
            (root / 'config/comfy-access.json').write_text('{"enabled": true}')
            (root / 'server.py').write_text('class Server:\n    def __init__(self):\n'
                '        self.app = web.Application(client_max_size=max_upload_size, middlewares=middlewares)\n')
            launcher = Path('scripts/comfy.sh').read_text()
            start = launcher.index('COMFY_LISTEN=')
            end = launcher.index('\n\n', start)
            fragment = launcher[start:end].replace('/opt/venvs/core/bin/python', shlex.quote(sys.executable))
            fragment = fragment.replace('/opt/pilot/apps/Portal/services', str(Path('apps/Portal/services').resolve()))
            result = subprocess.check_output(['bash', '-ec', fragment + '\nprintf "%s\n" "$COMFY_LISTEN" "$PYTHONPATH"'],
                env={**os.environ, 'WORKSPACE_ROOT': tmp, 'COMFY_DIR': tmp, 'PYTHONPATH': ''}, text=True)
            self.assertEqual(result.splitlines(), ['127.0.0.1', str(Path('apps/Portal/services').resolve())])
            self.assertIn('middlewares.insert(0, direct_access_middleware())', (root / 'server.py').read_text())


@unittest.skipIf(web is None, 'aiohttp unavailable')
class ComfyDirectAccessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        config = Path(self.tmp.name) / 'config'
        config.mkdir()
        self.policy = config / 'comfy-access.json'
        self.policy.write_text(json.dumps({'enabled': True, 'token_hash': ''}))
        settings = config / 'controlpilot-settings.json'
        settings.write_text(json.dumps({'session_secret': 'private-test-secret', 'password_enabled': True, 'password_hash': 'test-hash'}))
        env = patch.dict(os.environ, {'WORKSPACE_ROOT': self.tmp.name, 'CONTROLPILOT_SETTINGS_PATH': str(settings), 'COMFY_PORT': '5555'})
        env.start()
        self.addCleanup(env.stop)
        self.reached = []

        async def handler(request):
            self.reached.append(request.path)
            if request.path == '/ws':
                ws = web.WebSocketResponse()
                await ws.prepare(request)
                async for msg in ws:
                    if isinstance(msg.data, bytes):
                        await ws.send_bytes(msg.data)
                    else:
                        await ws.send_str(msg.data)
                return ws
            return web.Response(body=await request.read() or b'allowed')

        app = web.Application(middlewares=[direct_access_middleware()])
        app.router.add_route('*', '/{path:.*}', handler)
        self.client = TestClient(TestServer(app, host='127.0.0.1'))
        self.addAsyncCleanup(self.client.close)
        await self.client.start_server()

    async def test_direct_http_and_forwarded_loopback_requests_are_denied(self):
        for path in ['/', '/system_stats', '/api/prompt', '/view?filename=private.png', '/assets/index.js', '/custom-node']:
            for headers in [{}, {'X-Forwarded-For': '127.0.0.1', 'X-Real-IP': '127.0.0.1'},
                            {INTERNAL_HEADER: 'forged'}, {'Authorization': 'Bearer external-token'}]:
                response = await self.client.get(path, headers=headers)
                self.assertEqual(response.status, 401, path)
        response = await self.client.post('/upload/image', data=b'private upload')
        self.assertEqual(response.status, 401)
        with self.assertRaises(WSServerHandshakeError) as error:
            await self.client.ws_connect('/ws')
        self.assertEqual(error.exception.status, 401)
        self.assertEqual(self.reached, [])

    async def test_internal_uploads_and_binary_websockets_work(self):
        headers = internal_headers()
        response = await self.client.post('/upload/image', headers=headers, data=b'upload-body')
        self.assertEqual(response.status, 200)
        self.assertEqual(await response.read(), b'upload-body')
        async with self.client.ws_connect('/ws?clientId=preview', headers=headers) as ws:
            await ws.send_bytes(b'\x00\x01preview')
            self.assertEqual((await ws.receive()).data, b'\x00\x01preview')
            await ws.send_str('progress')
            self.assertEqual((await ws.receive()).data, 'progress')

    async def test_default_off_and_corrupt_policy(self):
        self.policy.write_text('{"enabled": false}')
        self.assertEqual(internal_headers(), {})
        self.assertEqual((await self.client.get('/')).status, 200)
        self.policy.write_text('broken')
        self.assertEqual((await self.client.get('/')).status, 503)
        self.policy.unlink()
        self.assertEqual((await self.client.get('/')).status, 200)

    async def test_missing_password_fails_closed_even_with_internal_header(self):
        headers = internal_headers()
        settings = Path(os.environ['CONTROLPILOT_SETTINGS_PATH'])
        for enabled, password_hash in [(False, ''), ('false', 123), (True, '   '), (True, 123)]:
            settings.write_text(json.dumps({'session_secret': 'private-test-secret',
                                           'password_enabled': enabled, 'password_hash': password_hash}))
            self.assertEqual((await self.client.get('/', headers=headers)).status, 503)

    async def test_credentials_never_go_to_custom_remote_endpoint(self):
        for url in ['http://other:5555', 'https://localhost:5555', 'http://127.0.0.1:8188',
                    'http://localhost:5555.evil.test', 'http://user@localhost:5555']:
            # Malformed URLs fail closed rather than obtaining a credential.
            try:
                self.assertEqual(internal_headers(url), {})
            except ValueError:
                pass
        self.assertTrue(internal_headers('http://localhost:5555'))
        with patch.dict(os.environ, {'COMFY_PORT': '7777'}):
            self.assertEqual(internal_headers('http://localhost:5555'), {})
            self.assertTrue(internal_headers('http://127.0.0.1:7777'))
