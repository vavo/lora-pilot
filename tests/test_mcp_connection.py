"""Owner diagnostics remain useful without relaxing MCP's access boundary."""
import asyncio
import json
from unittest.mock import patch

import httpx2
from starlette.testclient import TestClient

from test_mcp_access import Workspace
from apps.Portal.mcp_server.connection import test_connection
from apps.Portal.mcp_server.server import Runtime


class ConnectionTests(Workspace):
    def setUp(self):
        super().setUp()
        self.runtime = Runtime(self.facade, 'https://pilot.example')
        self.runtime.setup_sdk()

    def test_diagnostics_require_owner_and_never_disclose_tokens_or_write_state(self):
        before = self.store.read()
        with TestClient(self.app(), base_url='https://pilot.example') as client:
            self.assertEqual(client.get('/api/settings/mcp-diagnostics').status_code, 403)
            client.cookies.set('owner', 'session')
            response = client.get('/api/settings/mcp-diagnostics')
            self.assertTrue(response.json()['ready'])
            self.assertIn('no-store', response.headers['cache-control'])
            self.assertNotIn(self.token, response.text)
            self.assertNotIn('private caption canary', response.text)
            self.assertEqual(client.get('/api/settings/mcp-diagnostics', headers={'Sec-Fetch-Site': 'cross-site'}).status_code, 403)
            self.assertEqual(client.get('/api/settings/mcp-diagnostics', headers={'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.store.read(), before)

    def test_diagnostics_explain_address_and_https_failure_when_settings_are_blocked(self):
        with TestClient(self.app(), base_url='http://another.example') as client:
            client.cookies.set('owner', 'session')
            self.assertEqual(client.get('/api/settings/mcp').status_code, 403)
            result = client.get('/api/settings/mcp-diagnostics').json()
        checks = {item['id']: item for item in result['checks']}
        self.assertFalse(result['ready'])
        self.assertEqual(checks['host']['state'], 'error')
        self.assertIn('MCP_PUBLIC_URL', checks['host']['message'])
        self.assertEqual(checks['https']['state'], 'error')

    def test_connection_test_requires_owner_csrf_and_origin(self):
        with TestClient(self.app(), base_url='https://pilot.example', raise_server_exceptions=False) as client:
            client.cookies.set('owner', 'session')
            csrf = client.get('/api/settings/mcp').json()['csrf']
            for headers in ({}, {'Origin': 'https://pilot.example'},
                            {'Origin': 'https://evil.example', 'X-MCP-CSRF': csrf}):
                response = client.post('/api/settings/mcp/test', headers=headers, json={'token': self.token})
                self.assertEqual(response.status_code, 403)

    def test_public_handshake_lists_tools_and_calls_workspace_status(self):
        async def run():
            await self.runtime.start()
            real_client = httpx2.AsyncClient
            app = self.app()
            def client(**kwargs):
                return real_client(transport=httpx2.ASGITransport(app=app), **kwargs)
            try:
                with patch('httpx2.AsyncClient', side_effect=client):
                    result = await test_connection(self.runtime, self.token)
                self.assertTrue(result['ok'], result)
                self.assertTrue(result['workspace_checked'])
                self.assertIn('workspace_status', result['tools'])
                self.assertNotIn(self.token, json.dumps(result))
                self.queue.submit.assert_not_called()
                self.queue.start.assert_not_called()
            finally:
                await self.runtime.stop()
        asyncio.run(run())

    def test_invalid_tokens_are_never_sent_to_the_network(self):
        self.store.revoke(self.a)
        with patch('httpx2.AsyncClient') as client:
            result = asyncio.run(test_connection(self.runtime, self.token))
            self.assertEqual(result['code'], 'TOKEN_REJECTED')
            client.assert_not_called()

    def test_proxy_denials_have_safe_actionable_errors(self):
        real_client = httpx2.AsyncClient
        def denied(request):
            return httpx2.Response(403, text='private-upstream-canary ' + self.token)
        def client(**kwargs):
            return real_client(transport=httpx2.MockTransport(denied), **kwargs)
        with patch('httpx2.AsyncClient', side_effect=client):
            result = asyncio.run(test_connection(self.runtime, self.token))
        self.assertEqual(result['code'], 'PROXY_REJECTED')
        self.assertNotIn('private-upstream-canary', json.dumps(result))
        self.assertNotIn(self.token, json.dumps(result))
