"""Owner-authorized setup, deployment URL discovery and SDK activation."""
import asyncio
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from starlette.testclient import TestClient

from test_mcp_access import Workspace
from apps.Portal.mcp_server.admin import create_app
from apps.Portal.mcp_server.server import Runtime, public_origin


class SetupTests(Workspace):
    def test_launcher_preserves_socket_peer_only_for_runpod_origin(self):
        script = (Path(__file__).resolve().parents[1] / 'scripts/portal.sh').read_text()
        script = script.replace('source /opt/venvs/core/bin/activate', ':').replace(
            '/workspace/config/secrets.env', '/dev/null').replace('exec uvicorn ', "printf '%s\\n' ")
        for pod, origin, expected in [('fixture', '', True), ('fixture', 'https://fixture-7878.proxy.runpod.net/', True),
                                      ('fixture', 'https://custom.example', False), ('', '', False)]:
            with self.subTest(pod=pod, origin=origin):
                args = subprocess.check_output(['bash', '-c', script], text=True, env={
                    'PATH': os.defpath, 'RUNPOD_POD_ID': pod, 'MCP_PUBLIC_URL': origin, 'PORTAL_RELOAD': '1'
                }).splitlines()
                self.assertEqual('--no-proxy-headers' in args, expected)
                self.assertIn('--reload', args)

    def setUp(self):
        super().setUp()
        environment = patch.dict(os.environ, {'RUNPOD_POD_ID': '', 'PORTAL_PORT': '7878'}, clear=False)
        environment.start()
        self.addCleanup(environment.stop)
        self.store.set_enabled(False)
        self.runtime = Runtime(self.facade, '')
        self.runtime.setup_sdk()

    def owner(self, client):
        client.cookies.set('owner', 'session')
        response = client.get('/api/settings/mcp')
        self.assertEqual(response.status_code, 200, response.text)
        return {'Origin': str(client.base_url).rstrip('/'), 'X-MCP-CSRF': response.json()['csrf']}

    def connection(self):
        return dict(password='correct', label='My agent', scopes=['workspace:read'], enable=True)

    def test_missing_url_can_be_pinned_only_by_authenticated_password_confirmed_owner(self):
        with TestClient(self.app(), base_url='https://pilot.example', raise_server_exceptions=False) as client:
            self.assertEqual(client.get('/api/settings/mcp').status_code, 403)
            headers = self.owner(client)
            for changes in ({'Origin': 'https://evil.example'}, {'Origin': 'null'}, {'X-MCP-CSRF': 'bad'}, {'Sec-Fetch-Site': 'cross-site'}):
                response = client.post('/api/settings/mcp/clients', headers={**headers, **changes}, json=self.connection())
                self.assertEqual(response.status_code, 403, response.text)
                self.assertIsNone(self.runtime.origin)
                self.assertNotIn('public_origin', self.store.read())
            response = client.post('/api/settings/mcp/clients', headers=headers, json={**self.connection(), 'password': 'wrong'})
            self.assertEqual(response.status_code, 403)
            response = client.post('/api/settings/mcp/clients', headers=headers, json=self.connection())
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            self.assertEqual(result['url'], 'https://pilot.example/mcp')
            self.assertTrue(self.store.read()['enabled'])
            self.assertEqual(self.store.authenticate(result['token'])['scopes'], ['workspace:read'])
            self.assertEqual(self.runtime.transport_security.allowed_hosts, ['pilot.example'])
            self.assertEqual(self.runtime.transport_security.allowed_origins, ['https://pilot.example'])
            self.assertNotIn(result['token'], client.get('/api/settings/mcp').text)
            self.assertNotIn(result['token'], (self.root / 'config/mcp/state.json').read_text())
            self.assertEqual((self.root / 'config/mcp/state.json').stat().st_mode & 0o777, 0o600)
            self.assertEqual(Runtime(self.facade, '').origin, 'https://pilot.example')
            self.assertEqual(client.get('/api/settings/mcp', headers={'Host': 'evil.example'}).status_code, 403)

    def test_missing_password_returns_only_setup_state_and_cannot_enable(self):
        app = self.app()
        self.runtime.admin = create_app(self.runtime, lambda: False, lambda request: True,
                                        lambda: 'session-value', lambda value: True)
        with TestClient(app, base_url='https://pilot.example', raise_server_exceptions=False) as client:
            result = client.get('/api/settings/mcp')
            self.assertEqual(result.json(), dict(password_required=True, enabled=False, url=''))
            self.assertIn('no-store', result.headers['cache-control'])
            self.assertEqual(client.post('/api/settings/mcp/clients', headers={'Origin': 'https://pilot.example'},
                                         json=self.connection()).status_code, 403)
            self.assertFalse(self.store.read()['enabled'])

    def test_bad_config_and_sdk_failure_cannot_be_overridden_by_setup(self):
        for runtime in (Runtime(self.facade, 'http://public.example'), Runtime(self.facade, '')):
            self.runtime = runtime
            self.runtime.failure = 'MCP_UNAVAILABLE'
            with TestClient(self.app(), base_url='https://pilot.example', raise_server_exceptions=False) as client:
                headers = self.owner(client)
                response = client.post('/api/settings/mcp/clients', headers=headers, json=self.connection())
                self.assertEqual(response.status_code, 409, response.text)
                self.assertFalse(self.store.read()['enabled'])

    def test_plain_http_and_spoofed_forwarding_cannot_pin_public_origin(self):
        with TestClient(self.app(), base_url='http://public.example', raise_server_exceptions=False) as client:
            headers = self.owner(client)
            for origin in ('http://public.example', 'https://public.example'):
                response = client.post('/api/settings/mcp/clients', headers={**headers, 'Origin': origin,
                    'X-Forwarded-Proto': 'https', 'X-Forwarded-Host': 'pilot.example'}, json=self.connection())
                self.assertEqual(response.status_code, 403, response.text)
            self.assertIsNone(self.runtime.origin)
            self.assertFalse(self.store.read()['enabled'])

    def test_explicit_url_wins_and_invalid_urls_fail_closed(self):
        with patch.dict(os.environ, {'RUNPOD_POD_ID': 'fixturepod', 'PORTAL_PORT': '9999'}):
            self.assertEqual(Runtime(self.facade, '').origin, 'https://fixturepod-9999.proxy.runpod.net')
            self.assertEqual(Runtime(self.facade, 'https://custom.example').origin, 'https://custom.example')
            for value in ('https://evil.example/path', 'https://user:pass@evil.example',
                          'https://evil.example?token=x', 'https://evil.example#x',
                          'https://evil.example:bad', 'https://evil.example:0',
                          'https://evil.example\\path', ' https://evil.example'):
                with self.subTest(value=value):
                    self.assertEqual(Runtime(self.facade, value).failure, 'MCP_UNAVAILABLE')
        for pod, port in [('evil.example/', '7878'), ('fixture', 'not-a-port'), ('fixture', '65536')]:
            with patch.dict(os.environ, {'RUNPOD_POD_ID': pod, 'PORTAL_PORT': port}):
                self.assertEqual(Runtime(self.facade, '').failure, 'MCP_UNAVAILABLE')

    def test_runpod_proxy_setup_accepts_internal_http_but_not_foreign_hosts(self):
        with patch.dict(os.environ, {'RUNPOD_POD_ID': 'fixturepod', 'PORTAL_PORT': '7878', 'RUNPOD_TCP_PORT_7878': ''}):
            self.runtime = Runtime(self.facade, '')
            self.runtime.setup_sdk()
        origin = self.runtime.origin
        with TestClient(self.app(), base_url=origin.replace('https://', 'http://'), client=('100.64.1.64', 41234), raise_server_exceptions=False) as client:
            headers = {**self.owner(client), 'Origin': origin}
            response = client.post('/api/settings/mcp/clients', headers=headers, json=self.connection())
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(client.get('/api/settings/mcp', headers={'Host': 'different.proxy.runpod.net'}).status_code, 403)
            self.assertEqual(client.post('/mcp', json={}).status_code, 401)
            self.assertEqual(client.post('/mcp', headers={'Origin': 'https://evil.example'}, json={}).status_code, 403)
        with patch.dict(os.environ, {'RUNPOD_POD_ID': 'fixturepod', 'RUNPOD_TCP_PORT_7878': '34567'}):
            self.assertFalse(Runtime(self.facade, '').accepts_transport({'scheme': 'http'}))

    def test_runpod_rewritten_host_owner_setup_and_sdk_roundtrip(self):
        async def run():
            with patch.dict(os.environ, {'RUNPOD_POD_ID': 'fixturepod', 'RUNPOD_TCP_PORT_7878': ''}):
                self.runtime = Runtime(self.facade, '')
            app = self.app()
            await self.runtime.start()
            origin = self.runtime.origin
            proxy = {'Host': '100.65.17.138:60269', 'X-Forwarded-Host': urlsplit(origin).netloc,
                     'X-Forwarded-Proto': 'https'}
            try:
                async def after_tls_termination(scope, receive, send):
                    await app(dict(scope, scheme='http'), receive, send)

                transport = httpx2.ASGITransport(app=after_tls_termination, client=('100.64.1.68', 59912),
                                                 raise_app_exceptions=False)
                async with httpx2.AsyncClient(transport=transport, base_url=origin, headers=proxy) as owner:
                    self.assertEqual((await owner.get('/api/settings/mcp')).status_code, 403)
                    owner.cookies.set('owner', 'session')
                    status = await owner.get('/api/settings/mcp')
                    self.assertEqual(status.status_code, 200, status.text)
                    headers = {'Origin': origin, 'X-MCP-CSRF': status.json()['csrf']}
                    for bad in ({'Origin': 'https://foreign.example'}, {'X-MCP-CSRF': 'invalid'}):
                        denied = await owner.post('/api/settings/mcp/clients', headers={**headers, **bad},
                                                  json=self.connection())
                        self.assertEqual(denied.status_code, 403)
                    created = await owner.post('/api/settings/mcp/clients', headers=headers, json=self.connection())
                    self.assertEqual(created.status_code, 200, created.text)
                    self.assertEqual(created.json()['url'], origin + '/mcp')
                async with httpx2.AsyncClient(transport=transport, headers={**proxy,
                        'Authorization': 'Bearer ' + created.json()['token']}) as http:
                    async with Client(streamable_http_client(origin + '/mcp', http_client=http)) as agent:
                        self.assertEqual([t.name for t in (await agent.list_tools()).tools], ['workspace_status'])
            finally:
                await self.runtime.stop()
        asyncio.run(run())

    def test_forwarded_identity_cannot_be_spoofed_or_ambiguous(self):
        host = 'fixturepod-7878.proxy.runpod.net'
        proxy = [('Host', '100.65.17.138:60269'), ('X-Forwarded-Host', host), ('X-Forwarded-Proto', 'https')]
        peer = ('100.64.1.67', 40900)
        for pod, tcp, address, headers in [
            ('', '', peer, proxy), ('fixturepod', '34567', peer, proxy),
            ('fixturepod', '', ('203.0.113.7', 5555), proxy),
            ('fixturepod', '', ('127.0.0.1', 5555), proxy + [('X-Forwarded-For', peer[0] + ':40900')]),
            ('fixturepod', '', (peer[0], 0), proxy),
            ('fixturepod', '', peer, proxy + [proxy[1]]),
            ('fixturepod', '', peer, proxy + [proxy[2]]),
            ('fixturepod', '', peer, proxy[:2]),
            ('fixturepod', '', peer, [proxy[0], ('X-Forwarded-Host', host + ', evil.test'), proxy[2]]),
            ('fixturepod', '', peer, [proxy[0], proxy[1], ('X-Forwarded-Proto', 'http')]),
            ('fixturepod', '', peer, [('Host', 'evil.test'), *proxy[1:]]),
        ]:
            with self.subTest(pod=pod, tcp=tcp, address=address, headers=headers), patch.dict(os.environ,
                    {'RUNPOD_POD_ID': pod, 'RUNPOD_TCP_PORT_7878': tcp}):
                self.runtime = Runtime(self.facade, 'https://' + host)
                self.runtime.setup_sdk()
                with TestClient(self.app(), base_url='http://' + host, client=address) as client:
                    client.cookies.set('owner', 'session')
                    expected = 400 if len(headers) != len(dict(headers)) else 403
                    self.assertEqual(client.get('/api/settings/mcp', headers=headers).status_code, expected)
                    self.assertEqual(client.post('/mcp', headers=headers, json={}).status_code, expected)

    def test_setup_activates_existing_sdk_lifespan_without_restart(self):
        async def run():
            self.runtime = Runtime(self.facade, '')
            app = self.app()
            await self.runtime.start()
            try:
                async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),
                    base_url='https://pilot.example', cookies={'owner': 'session'}) as owner:
                    result = (await owner.get('/api/settings/mcp')).json()
                    response = await owner.post('/api/settings/mcp/clients',
                        headers={'Origin': 'https://pilot.example', 'X-MCP-CSRF': result['csrf']}, json=self.connection())
                    self.assertEqual(response.status_code, 200, response.text)
                    token = response.json()['token']
                async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),
                    headers={'Authorization': 'Bearer ' + token}) as http:
                    async with Client(streamable_http_client('https://pilot.example/mcp', http_client=http)) as client:
                        self.assertEqual([tool.name for tool in (await client.list_tools()).tools], ['workspace_status'])
                        result = await client.call_tool('workspace_status', {})
                        self.assertFalse(result.is_error)
            finally:
                await self.runtime.stop()
        asyncio.run(run())
