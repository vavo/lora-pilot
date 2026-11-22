"""Exercise skill discovery and reads through the authenticated MCP transport."""
import asyncio
import unittest

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError

from test_mcp_access import Workspace
from apps.Portal.mcp_server.agent_skill import SKILL_RESOURCES, SKILL_ROOT, SKILL_URI


class SkillResourcesTests(Workspace):
    def roundtrip(self, token, verify):
        async def run():
            await self.runtime.start()
            self.assertIsNone(self.runtime.failure)
            try:
                async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=self.app()),
                    headers={'Authorization': 'Bearer ' + token}) as http:
                    transport = streamable_http_client('http://127.0.0.1:7878/mcp', http_client=http)
                    async with Client(transport) as client:
                        await verify(client)
            finally:
                await self.runtime.stop()
        asyncio.run(run())

    def test_workspace_reader_discovers_and_reads_the_complete_packaged_skill(self):
        before = self.snapshot()

        async def verify(client):
            listing = await client.list_resources()
            resources = {str(item.uri): item for item in listing.resources}
            self.assertEqual(set(resources), {'lorapilot://docs/mcp', *SKILL_RESOURCES})
            for uri, (_, relative) in SKILL_RESOURCES.items():
                with self.subTest(uri=uri):
                    result = await client.read_resource(uri)
                    self.assertEqual(len(result.contents), 1)
                    self.assertEqual(result.contents[0].text, (SKILL_ROOT / relative).read_text())
                    self.assertEqual(result.contents[0].mime_type, 'text/markdown')
                    self.assertEqual(resources[uri].mime_type, 'text/markdown')
                    self.assertLess(len(result.contents[0].text.encode()), 256 * 1024)
                    self.assertNotIn('private caption canary', result.contents[0].text)
                    self.assertNotIn(self.token, result.contents[0].text)
            tools = await client.list_tools()
            self.assertEqual({item.name for item in tools.tools}, {
                'workspace_status', 'datasets_list', 'dataset_review', 'models_list',
                'runs_list', 'run_get', 'operation_get'})

        self.roundtrip(self.token, verify)
        self.assertEqual(self.snapshot(), before)
        self.queue.submit.assert_not_called()
        self.queue.start.assert_not_called()

    def test_model_only_connection_cannot_list_or_read_skill_resources(self):
        _, token = self.store.create_client('Models only', ['models:read'], [], [])

        async def verify(client):
            self.assertEqual((await client.list_resources()).resources, [])
            for uri in SKILL_RESOURCES:
                with self.subTest(uri=uri), self.assertRaises(MCPError):
                    await client.read_resource(uri)

        self.roundtrip(token, verify)

    def test_resource_allowlist_rejects_paths_and_revocation_still_applies(self):
        async def verify(client):
            for uri in [SKILL_URI + '/SKILL.md', SKILL_URI + '/../../config/mcp/state.json',
                        SKILL_URI + '/image-models?token=canary', 'file:///etc/passwd']:
                with self.subTest(uri=uri), self.assertRaises(MCPError):
                    await client.read_resource(uri)
            self.store.revoke(self.a)
            with self.assertRaises(Exception):
                await client.read_resource(SKILL_URI)

        self.roundtrip(self.token, verify)


if __name__ == '__main__':
    unittest.main()
