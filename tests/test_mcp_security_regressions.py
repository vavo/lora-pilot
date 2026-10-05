"""Security recovery and scheduling checks on bounded, disposable fixtures."""
import asyncio
from contextlib import contextmanager
import json
import threading
import unittest
import uuid
from unittest.mock import patch

import anyio
from starlette.requests import ClientDisconnect

from test_mcp_access import Workspace
import test_mcp_operations as operations_tests
from apps.Portal.mcp_server.contracts import SCOPES
from apps.Portal.mcp_server.files import Rejected, canonical
from apps.Portal.mcp_server.store import Store


class LedgerCapacityTests(Workspace):
    def setUp(self):
        super().setUp()
        now = self.store.clock()
        self.store.clock = lambda: now
        self.a, self.token = self.store.create_client('Writer', sorted(SCOPES), ['1_private'], [])
        plan = self.store.plan(self.a, 'training', {'max_steps': 1}, {})
        self.store.approve(plan['id'], True)
        self.request = dict(plan_id=plan['id'], request_id=str(uuid.uuid4()))
        self.op, _ = self.store.accept(self.a, 'training_start', self.request, 'training:submit')

    def test_full_work_ledger_keeps_owner_controls_and_replay_records(self):
        original = self.store.read()
        before = self.snapshot()
        # Reduced byte caps exercise the production transaction boundary without filling a disk.
        with patch('apps.Portal.mcp_server.store.MAX_BYTES', len(canonical(original))), \
             patch('apps.Portal.mcp_server.store.CONTROL_RESERVE_BYTES', 256):
            with self.assertRaises(Rejected) as denied:
                self.store.plan(self.a, 'training', {'max_steps': 1}, {})
            self.assertEqual(denied.exception.code, 'LIMIT_EXCEEDED')
            self.assertEqual(self.store.read(), original)
            for _ in range(12):
                token = self.store.rotate(self.a)
            self.assertEqual(self.store.authenticate(token)['id'], self.a)
            with self.assertRaises(Rejected):
                self.store.authenticate(self.token)
            self.store.change_client(self.a, 'Writer', ['workspace:read'], [], [], 30, {})
            self.assertEqual(self.store.principal(self.a)['scopes'], ['workspace:read'])
            self.store.revoke(self.a)
            with self.assertRaises(Rejected):
                self.store.authenticate(token)
            self.store.set_enabled(False)
            data = self.store.read()
            self.assertFalse(data['enabled'])
            self.assertEqual(data['audit'][-1]['action'], 'disable')
            self.assertLess(len(data['audit']), len(original['audit']) + 15)
            self.assertEqual(data['operations'], original['operations'])
            self.assertLessEqual(len(canonical(data)), len(canonical(original)) + 256)
        self.assertEqual(self.snapshot(), before)

    def test_legacy_full_ledger_without_audit_can_restart_and_disable(self):
        data = self.store.read()
        data['audit'] = []
        pending = self.store.plan(self.a, 'training', {'max_steps': 1}, {})
        data['plans'][pending['id']] = self.store.read()['plans'][pending['id']]
        self.store.files.write('config/mcp/state.json', canonical(data), replace=True)
        with patch('apps.Portal.mcp_server.store.MAX_BYTES', len(canonical(data))), \
             patch('apps.Portal.mcp_server.store.CONTROL_RESERVE_BYTES', 1024):
            fresh = Store(self.root, clock=self.store.clock)
            self.addCleanup(fresh.close)
            fresh.initialize()
            fresh.claim()
            recovered = fresh.read()
            self.assertEqual(recovered['plans'][pending['id']]['state'], 'invalid')
            self.assertEqual(next(iter(recovered['operations'].values()))['state'], 'unknown')
            fresh.revoke(self.a)
            fresh.set_enabled(False)
            self.assertFalse(fresh.read()['enabled'])
            self.assertEqual(len(fresh.read()['operations']), 1)

    def test_replay_and_operation_completion_work_above_work_cap(self):
        cap = len(canonical(self.store.read()))
        with patch('apps.Portal.mcp_server.store.MAX_BYTES', cap), \
             patch('apps.Portal.mcp_server.store.CONTROL_RESERVE_BYTES', 2048):
            self.store.rotate(self.a)
            before = (self.root / 'config/mcp/state.json').read_bytes()
            self.assertGreater(len(before), cap)
            op, created = self.store.accept(self.a, 'training_start', self.request, 'training:submit')
            self.assertFalse(created)
            self.assertEqual(op['id'], self.op['id'])
            self.assertEqual((self.root / 'config/mcp/state.json').read_bytes(), before)
            self.store.update_operation(op['id'], state='failed', error='EXECUTION_FAILED')
            self.assertEqual(self.store.operation(self.a, op['id'])['state'], 'failed')
            with self.store.transaction() as data:
                data['plans'].clear()
            self.assertEqual(len(self.store.read()['operations']), 1)


class ResourceSchedulingTests(Workspace):
    def setUp(self):
        super().setUp()
        self.run_id = uuid.uuid4().hex
        folder = self.root / 'config/training' / self.run_id
        folder.mkdir(parents=True)
        self.output = self.root / 'outputs' / self.run_id
        self.output.mkdir(parents=True)
        self.record = dict(id=self.run_id, status='succeeded', output_dir=str(self.output),
                           spec=dict(output_name='test', family='sdxl'))
        self.record_path = folder / 'run.json'
        self.record_path.write_bytes(canonical(self.record))
        self.store.change_client(self.a, 'A', ['runs:read'], [], [self.run_id], 30, {})

    def test_resource_read_uses_shared_workers_and_leaves_http_responsive(self):
        import httpx2
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client

        async def run():
            app = self.app()
            @app.get('/probe')
            async def probe():
                return {'ok': True}
            await self.runtime.start()
            entered, release, finished = threading.Event(), threading.Event(), threading.Event()
            listdir = self.store.files.listdir
            def slow_listdir(path):
                if path == 'outputs/' + self.run_id:
                    entered.set()
                    release.wait(2)
                    finished.set()
                return listdir(path)
            self.runtime.limiter = anyio.CapacityLimiter(1)
            borrower = object()
            self.runtime.limiter.acquire_on_behalf_of_nowait(borrower)
            try:
                async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),
                        headers={'Authorization': 'Bearer ' + self.token}) as http:
                    async with Client(streamable_http_client('http://127.0.0.1:7878/mcp', http_client=http)) as client:
                        with patch.object(self.store.files, 'listdir', side_effect=slow_listdir):
                            task = asyncio.create_task(client.read_resource('lorapilot://runs/' + self.run_id + '/summary'))
                            try:
                                await asyncio.sleep(0.05)
                                self.assertFalse(entered.is_set(), 'resource bypassed the shared worker limit')
                                self.runtime.limiter.release_on_behalf_of(borrower)
                                self.assertTrue(await asyncio.to_thread(entered.wait, 1))
                                response = await http.get('http://127.0.0.1:7878/probe')
                                self.assertEqual(response.json(), {'ok': True})
                                self.assertFalse(finished.is_set(), 'filesystem work blocked the event loop')
                            finally:
                                release.set()
                                result = await asyncio.wait_for(task, 3)
                            self.assertEqual(json.loads(result.contents[0].text)['run_id'], self.run_id)
            finally:
                release.set()
                if borrower in self.runtime.limiter.statistics().borrowers:
                    self.runtime.limiter.release_on_behalf_of(borrower)
                await self.runtime.stop()
        asyncio.run(run())

    def test_resource_errors_remain_private_and_responses_are_bounded(self):
        import httpx2
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client
        from mcp.shared.exceptions import MCPError

        async def run():
            app = self.app()
            await self.runtime.start()
            try:
                for mode in ['2026-07-28', 'legacy']:
                    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),
                            headers={'Authorization': 'Bearer ' + self.token}) as http:
                        async with Client(streamable_http_client('http://127.0.0.1:7878/mcp', http_client=http), mode=mode) as client:
                            for run_id in [uuid.uuid4().hex, '../private']:
                                with self.subTest(mode=mode, run_id=run_id), self.assertRaises(MCPError) as error:
                                    await client.read_resource('lorapilot://runs/' + run_id + '/summary')
                                self.assertNotIn(str(self.root), str(error.exception))
                            self.record['spec']['output_name'] = 'x' * (256 * 1024)
                            self.record_path.write_bytes(canonical(self.record))
                            with self.assertRaises(MCPError):
                                await client.read_resource('lorapilot://runs/' + self.run_id + '/summary')
                            self.record['spec']['output_name'] = 'test'
                            self.record_path.write_bytes(canonical(self.record))
                            result = await client.read_resource('lorapilot://runs/' + self.run_id + '/summary')
                            self.assertEqual(json.loads(result.contents[0].text)['name'], 'test')
            finally:
                await self.runtime.stop()
        asyncio.run(run())


class DownloadSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = operations_tests.OperationsTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        f = self.fixture
        self.run_id, self.checkpoint, _ = f.checkpoint()
        self.url = self.export(f.a)
        f.runtime.setup_sdk()

    def export(self, principal):
        f = self.fixture
        plan = f.facade.call(principal, 'export_plan', dict(run_id=self.run_id, checkpoint_id=self.checkpoint))
        f.store.approve(plan['id'], True)
        result = f.facade.call(principal, 'export_create', dict(plan_id=plan['id'], request_id=str(uuid.uuid4())))
        self.assertEqual(result['state'], 'succeeded')
        return '/mcp-artifacts/' + result['operation_id']

    async def download(self, send, token=None, url=None, version='2.4', receive=None):
        async def wait_for_disconnect():
            await asyncio.Event().wait()
        scope = dict(type='http', method='GET', path=url or self.url, query_string=b'', scheme='http',
            server=('127.0.0.1', 7878), client=('127.0.0.1', 1234), http_version='1.1',
            asgi={'version': '3.0', 'spec_version': version},
            headers=[(b'host', b'127.0.0.1:7878'),
                     (b'authorization', ('Bearer ' + (token or self.fixture.token)).encode())])
        await self.fixture.runtime.handle(scope, receive or wait_for_disconnect, send)

    def test_one_stream_per_identity_leaves_capacity_for_another_connection(self):
        f = self.fixture
        b, token_b = f.store.create_client('Exporter B', sorted(SCOPES), [], [self.run_id])
        url_b = self.export(b)
        async def run():
            entered, release = asyncio.Event(), asyncio.Event()
            async def held_send(message):
                if message['type'] == 'http.response.body' and message.get('body'):
                    entered.set()
                    await release.wait()
            first = asyncio.create_task(self.download(held_send))
            try:
                await asyncio.wait_for(entered.wait(), 2)
                # Rotating a token cannot allocate a second slot for the same identity.
                rotated = f.store.rotate(f.a)
                for token, url, expected in [(rotated, self.url, 429), (token_b, url_b, 200)]:
                    messages = []
                    async def collect(message):
                        messages.append(message)
                    await self.download(collect, token, url)
                    self.assertEqual(messages[0]['status'], expected)
                    self.assertEqual(f.runtime.downloads.borrowed_tokens, 1)
            finally:
                release.set()
                await asyncio.wait_for(first, 2)
            self.assertEqual(f.runtime.downloads.borrowed_tokens, 0)
        asyncio.run(run())

    def test_stalled_headers_body_and_completion_release_stream_and_descriptor(self):
        f = self.fixture
        opened = []
        original = f.store.files.open
        @contextmanager
        def tracked_open(path, *args, **kwargs):
            with original(path, *args, **kwargs) as stream:
                if path.endswith('.zip'):
                    opened.append(stream)
                yield stream
        async def run():
            for version in ['2.3', '2.4']:
                for phase in ['headers', 'body', 'completion']:
                    with self.subTest(version=version, phase=phase):
                        messages = []
                        async def stalled(message):
                            messages.append(message)
                            current = ('headers' if message['type'] == 'http.response.start'
                                       else 'body' if message.get('body') else 'completion')
                            if current == phase:
                                await asyncio.Event().wait()
                        with patch('apps.Portal.mcp_server.server.DOWNLOAD_SEND_TIMEOUT', 0.03):
                            with self.assertRaises((RuntimeError, ClientDisconnect, ExceptionGroup)):
                                await asyncio.wait_for(self.download(stalled, version=version), 2)
                        self.assertEqual(sum(m['type'] == 'http.response.start' for m in messages), 1)
                        self.assertEqual(f.runtime.downloads.borrowed_tokens, 0)
                        self.assertTrue(opened)
                        self.assertTrue(all(stream.closed for stream in opened))
                        successful = []
                        async def collect(message):
                            successful.append(message)
                        await self.download(collect, version=version)
                        self.assertEqual(successful[0]['status'], 200)
                        self.assertTrue(b''.join(m.get('body', b'') for m in successful).startswith(b'PK'))
                        self.assertEqual(f.runtime.downloads.borrowed_tokens, 0)
        with patch.object(f.store.files, 'open', side_effect=tracked_open):
            asyncio.run(run())

    def test_blocked_error_responses_do_not_reserve_download_capacity(self):
        f = self.fixture
        async def run():
            cases = [(f.token, '/mcp-artifacts/invalid'), (f.token_b, self.url)]
            for token, url in cases:
                with self.subTest(url=url, foreign=token == f.token_b):
                    entered, release = asyncio.Event(), asyncio.Event()
                    async def held_error(message):
                        if message['type'] == 'http.response.start':
                            self.assertEqual(message['status'], 404)
                            entered.set()
                            await release.wait()
                    task = asyncio.create_task(self.download(held_error, token, url))
                    try:
                        await asyncio.wait_for(entered.wait(), 2)
                        self.assertEqual(f.runtime.downloads.borrowed_tokens, 0)
                    finally:
                        release.set()
                        await asyncio.wait_for(task, 2)
        asyncio.run(run())

    def test_disconnect_and_cancellation_release_download_capacity(self):
        f = self.fixture
        async def run():
            for mode in ['disconnect', 'cancel']:
                with self.subTest(mode=mode):
                    entered = asyncio.Event()
                    async def send(message):
                        if message['type'] == 'http.response.body' and message.get('body'):
                            entered.set()
                            if mode == 'disconnect':
                                raise OSError('client disconnected')
                            await asyncio.Event().wait()
                    task = asyncio.create_task(self.download(send))
                    await asyncio.wait_for(entered.wait(), 2)
                    if mode == 'cancel':
                        task.cancel()
                    with self.assertRaises((ClientDisconnect, asyncio.CancelledError)):
                        await asyncio.wait_for(task, 2)
                    self.assertEqual(f.runtime.downloads.borrowed_tokens, 0)
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
