"""Owner-authorized setup, deployment URL discovery and SDK activation."""
import asyncio
import json
import os
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
        with TestClient(self.app(), base_url=origin.replace('https://', 'http://'), raise_server_exceptions=False) as client:
            headers = {**self.owner(client), 'Origin': origin}
            response = client.post('/api/settings/mcp/clients', headers=headers, json=self.connection())
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(client.get('/api/settings/mcp', headers={'Host': 'different.proxy.runpod.net'}).status_code, 403)
            self.assertEqual(client.post('/mcp', json={}).status_code, 401)
            self.assertEqual(client.post('/mcp', headers={'Origin': 'https://evil.example'}, json={}).status_code, 403)
        with patch.dict(os.environ, {'RUNPOD_POD_ID': 'fixturepod', 'RUNPOD_TCP_PORT_7878': '34567'}):
            self.assertFalse(Runtime(self.facade, '').accepts_transport({'scheme': 'http'}))

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
