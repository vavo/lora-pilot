"""Observable write, replay, file-integrity and crash oracles. No GPU/provider calls."""
import concurrent.futures
import asyncio
import hashlib
import io
import json
import os
import subprocess
import sys
import threading
import time
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from test_mcp_access import Workspace
from apps.Portal.mcp_server.contracts import SCOPES
from apps.Portal.mcp_server.files import Rejected, canonical
from apps.Portal.mcp_server.operations import Execution, GIB
from apps.Portal.mcp_server.store import Store
from apps.Portal.services.training_runs import TrainingRuns


class Immediate:
    def submit(self, function, *args):
        function(*args)

    def shutdown(self, **kwargs):
        pass


class OperationsTests(Workspace):
    def setUp(self):
        super().setUp()
        self.store.claim()
        self.a, self.token = self.store.create_client('Writer', sorted(SCOPES), ['1_private'], [])
        self.queue = TrainingRuns(self.root / 'config/training', Mock(), Mock(), lambda: [])
        start = self.queue.start
        self.queue.start = lambda: start(background=False)
        self.addCleanup(self.queue.close)
        self.facade.queue, self.facade.writes = self.queue, True
        self.execution = Execution(self.facade, 32 * GIB, provider=Mock())
        self.execution.pool.shutdown()
        self.execution.pool = Immediate()
        self.addCleanup(self.execution.close)
        (self.root / 'models/checkpoints').mkdir(parents=True)
        (self.root / 'models/checkpoints/sd_xl_base_1.0.safetensors').write_bytes(b'synthetic base model')
        self.dataset = next(iter(self.store.principal(self.a)['datasets']))

    def plan(self):
        result = self.facade.call(self.a, 'training_plan', dict(dataset_id=self.dataset, output_name='test', max_steps=1))
        self.store.approve(result['id'], True)
        return {'plan_id': result['id'], 'request_id': str(uuid.uuid4())}

    def queued_run(self):
        result = self.facade.call(self.a, 'training_start', self.plan())
        return result['operation_id'], self.queue.get(result['operation_id'])

    def checkpoint(self):
        run_id, run = self.queued_run()
        run['status'] = 'succeeded'
        self.queue.save(run)
        header = canonical({'x': {'dtype': 'F32', 'shape': [1], 'data_offsets': [0, 4]}})
        path = Path(run['output_dir']) / 'test.safetensors'
        path.write_bytes(len(header).to_bytes(8, 'little') + header + b'\0' * 4)
        checkpoint = self.facade.call(self.a, 'run_get', {'run_id': run_id})['checkpoints'][0]['checkpoint_id']
        return run_id, checkpoint, path

    def test_W01_W02_W07_concurrent_replay_and_approval_consumption(self):
        before = self.snapshot()
        request = self.plan()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(lambda _: self.facade.call(self.a, 'training_start', request), range(20)))
        self.assertEqual(len({result['operation_id'] for result in results}), 1)
        self.assertEqual(len(self.queue.list()), 1)
        self.assertEqual(self.snapshot(), before)
        with self.assertRaises(Rejected) as conflict:
            self.facade.call(self.a, 'export_create', request)
        self.assertEqual(conflict.exception.code, 'IDEMPOTENCY_CONFLICT')
        with self.assertRaises(Rejected):
            self.facade.call(self.a, 'training_start', dict(request, request_id=str(uuid.uuid4())))

    def test_A06_A08_unapproved_and_foreign_plan_has_no_run(self):
        plan = self.facade.call(self.a, 'training_plan', dict(dataset_id=self.dataset, output_name='test'))
        request = dict(plan_id=plan['id'], request_id=str(uuid.uuid4()))
        with self.assertRaises(Rejected) as denied:
            self.facade.call(self.a, 'training_start', request)
        self.assertEqual(denied.exception.code, 'APPROVAL_REQUIRED')
        self.store.approve(plan['id'], True)
        b, _ = self.store.create_client('Other', sorted(SCOPES), ['1_private'], [])
        with self.assertRaises(Rejected):
            self.facade.call(b, 'training_start', request)
        self.assertEqual(self.queue.list(), [])

    def test_F04_stale_same_size_same_mtime_source_never_queues(self):
        request = self.plan()
        path = self.root / 'datasets/1_private/a.txt'
        info = path.stat()
        path.write_text('x' * info.st_size)
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
        result = self.facade.call(self.a, 'training_start', request)
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['error'], 'PLAN_STALE')
        self.assertEqual(self.queue.list(), [])
        self.assertEqual(self.facade.call(self.a, 'training_start', request)['operation_id'], result['operation_id'])

    def test_F05_F06_copy_is_private_verified_and_never_hardlinked(self):
        before = self.snapshot()
        _, run = self.queued_run()
        image = self.root / run['mcp_recipe']['snapshot'][0]['path']
        image.write_bytes(b'fake trainer modified its input')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(image.stat().st_nlink, 1)
        self.queue.mcp_conflicts = lambda: []
        with patch('apps.Portal.services.training_performance.sample'), patch('subprocess.Popen') as launch:
            self.queue.tick()
            launch.assert_not_called()
        self.assertEqual(self.queue.get(run['id'])['status'], 'failed')

    def test_A10_Q06_revocation_and_disable_before_dispatch(self):
        for disable in [False, True]:
            with self.subTest(disable=disable):
                if disable:
                    self.a, self.token = self.store.create_client('Again', sorted(SCOPES), ['1_private'], [])
                    self.dataset = next(iter(self.store.principal(self.a)['datasets']))
                run_id, _ = self.queued_run()
                if disable:
                    self.store.set_enabled(False)
                else:
                    self.store.revoke(self.a)
                self.queue.mcp_launch = Mock()
                self.queue.tick()
                self.queue.mcp_launch.assert_not_called()
                self.assertEqual(self.queue.get(run_id)['status'], 'cancelled')

    def test_Q02_gpu_busy_keeps_queue_waiting(self):
        run_id, _ = self.queued_run()
        self.queue.mcp_conflicts = lambda: ['GPU busy']
        self.queue.mcp_launch = Mock()
        self.queue.tick()
        self.assertEqual(self.queue.get(run_id)['status'], 'queued')
        self.queue.mcp_launch.assert_not_called()

    def test_Q03_queued_source_config_or_record_change_never_launches(self):
        run_id, run = self.queued_run()
        self.queue.mcp_conflicts = lambda: []
        for path in [self.root / 'datasets/1_private/a.txt',
                     self.root / run['mcp_recipe']['configs'][0]['path'],
                     self.root / run['mcp_recipe']['configs'][1]['path']]:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b'changed')
                with patch('subprocess.Popen') as launch, self.assertRaises(Rejected):
                    self.execution.launch(run, io.BytesIO())
                launch.assert_not_called()
                path.write_bytes(original)
        run['mcp_recipe']['max_seconds'] = 999999
        self.assertFalse(self.execution.authorize_run(run))

    def test_A10_grant_edit_invalidates_plan_and_queued_run(self):
        request = self.plan()
        client = self.store.principal(self.a)
        self.store.change_client(self.a, 'Edited', sorted(SCOPES), ['1_private'], [], 30, {})
        self.assertEqual(self.store.authenticate(self.token)['id'], self.a)
        self.assertEqual(self.store.principal(self.a)['datasets'], client['datasets'])
        with self.assertRaises(Rejected):
            self.facade.call(self.a, 'training_start', request)
        run_id, _ = self.queued_run()
        self.store.change_client(self.a, 'Reader', ['runs:read'], [], [run_id], 30, {})
        self.queue.mcp_launch = Mock()
        self.queue.tick()
        self.queue.mcp_launch.assert_not_called()
        self.assertEqual(self.queue.get(run_id)['status'], 'cancelled')

    def test_A08_bounded_policy_approves_only_within_each_limit(self):
        policy = dict(enabled=True, max_steps=10, max_seconds=120, max_bytes=5 * GIB)
        self.store.change_client(self.a, 'Automation', sorted(SCOPES), ['1_private'], [], 30, policy)
        payload = dict(dataset_id=self.dataset, output_name='auto', max_steps=10, max_seconds=120)
        approved = self.facade.call(self.a, 'training_plan', payload)
        self.assertEqual(approved['state'], 'approved')
        for changed in [dict(max_steps=11), dict(max_seconds=121)]:
            self.assertEqual(self.facade.call(self.a, 'training_plan', {**payload, **changed})['state'], 'pending')
        self.store.change_client(self.a, 'Too small', sorted(SCOPES), ['1_private'], [], 30, {**policy, 'max_bytes': GIB})
        self.assertEqual(self.facade.call(self.a, 'training_plan', payload)['state'], 'pending')
        self.store.change_client(self.a, 'Manual', sorted(SCOPES), ['1_private'], [], 30, {})
        self.assertEqual(self.facade.call(self.a, 'training_plan', payload)['state'], 'pending')
        self.assertEqual(self.queue.list(), [])

    def test_Q05_cancel_preserves_files_and_replays(self):
        before = self.snapshot()
        run_id, run = self.queued_run()
        request = dict(run_id=run_id, request_id=str(uuid.uuid4()))
        first = self.facade.call(self.a, 'run_cancel', request)
        second = self.facade.call(self.a, 'run_cancel', request)
        self.assertEqual(first['operation_id'], second['operation_id'])
        self.assertEqual(first['state'], 'succeeded')
        self.assertEqual(self.queue.get(run_id)['status'], 'cancelled')
        self.assertTrue(Path(run['output_dir']).is_dir())
        self.assertEqual(self.snapshot(), before)

    def test_Q05_Q07_real_runner_identity_and_cancellation(self):
        from apps.Portal.services.training_runs import process_identity
        run_id, run = self.queued_run()
        launches = self.root / 'launches.jsonl'
        code = 'import pathlib,sys,time; pathlib.Path(sys.argv[1]).open("a").write(sys.argv[2]+"\\n"); time.sleep(30)'
        processes = []
        def launch(record, stream):
            proc = subprocess.Popen([sys.executable, '-c', code, str(launches), record['id']],
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, env={'PATH': os.environ.get('PATH', '')})
            processes.append(proc)
            return proc
        self.queue.mcp_launch = launch
        self.queue.mcp_conflicts = lambda: []
        try:
            with patch('apps.Portal.services.training_performance.sample'):
                self.queue.tick()
            self.assertEqual(len(processes), 1)
            proc = processes[0]
            with patch('apps.Portal.mcp_server.operations.process_identity', return_value='different-process'):
                result = self.facade.call(self.a, 'run_cancel', dict(run_id=run_id, request_id=str(uuid.uuid4())))
                self.assertEqual(result['error'], 'PROCESS_IDENTITY_UNAVAILABLE')
                self.assertIsNone(proc.poll())
            result = self.facade.call(self.a, 'run_cancel', dict(run_id=run_id, request_id=str(uuid.uuid4())))
            if process_identity(proc.pid) is None and sys.platform != 'linux':
                self.assertEqual(result['error'], 'PROCESS_IDENTITY_UNAVAILABLE')
            else:
                self.assertEqual(result['state'], 'succeeded')
                self.assertIsNotNone(proc.poll())
            self.assertTrue(Path(run['output_dir']).exists())
        finally:
            for proc in processes:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)

    def test_E01_E02_export_allowlist_digest_and_private_archive(self):
        run_id, checkpoint_id, checkpoint = self.checkpoint()
        before = self.snapshot()
        plan = self.facade.call(self.a, 'export_plan', dict(run_id=run_id, checkpoint_id=checkpoint_id))
        self.store.approve(plan['id'], True)
        result = self.facade.call(self.a, 'export_create', dict(plan_id=plan['id'], request_id=str(uuid.uuid4())))
        self.assertEqual(result['state'], 'succeeded')
        op = self.store.operation(self.a, result['operation_id'])
        archive = self.root / op['artifact']['path']
        with zipfile.ZipFile(archive) as package:
            self.assertEqual(set(package.namelist()), {'README.md', 'experiment.json', 'checkpoint/LoRA.safetensors'})
            self.assertEqual(package.read('checkpoint/LoRA.safetensors'), checkpoint.read_bytes())
            self.assertNotIn(b'private caption canary', package.read('experiment.json'))
            self.assertNotIn(str(self.root).encode(), package.read('experiment.json'))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)

    def test_E02_stale_checkpoint_blocks_archive(self):
        run_id, checkpoint_id, checkpoint = self.checkpoint()
        plan = self.facade.call(self.a, 'export_plan', dict(run_id=run_id, checkpoint_id=checkpoint_id))
        self.store.approve(plan['id'], True)
        info = checkpoint.stat()
        with checkpoint.open('r+b') as stream:
            stream.seek(-1, 2)
            stream.write(b'x')
        os.utime(checkpoint, ns=(info.st_atime_ns, info.st_mtime_ns))
        result = self.facade.call(self.a, 'export_create', dict(plan_id=plan['id'], request_id=str(uuid.uuid4())))
        self.assertEqual(result['state'], 'failed')
        self.assertFalse(list(self.root.glob('config/mcp/jobs/*/experiment.zip')))

    def test_E01_export_removes_checkpoint_metadata_preserving_tensor_bytes(self):
        run_id, checkpoint_id, checkpoint = self.checkpoint()
        header = canonical({'__metadata__': {'training_config': 'secret-path-caption-canary'},
                            'weight': {'dtype': 'F32', 'shape': [1], 'data_offsets': [0, 4]}})
        original = len(header).to_bytes(8, 'little') + header + b'\x00\x00\x80\x3f'
        checkpoint.write_bytes(original)
        plan = self.facade.call(self.a, 'export_plan', dict(run_id=run_id, checkpoint_id=checkpoint_id))
        self.store.approve(plan['id'], True)
        result = self.facade.call(self.a, 'export_create', dict(plan_id=plan['id'], request_id=str(uuid.uuid4())))
        self.assertEqual(result['state'], 'succeeded')
        op = self.store.operation(self.a, result['operation_id'])
        with zipfile.ZipFile(self.root / op['artifact']['path']) as archive:
            exported = archive.read('checkpoint/LoRA.safetensors')
            self.assertNotIn(b'secret-path-caption-canary', exported)
            self.assertNotIn(b'__metadata__', exported)
            offset = 8 + int.from_bytes(exported[:8], 'little')
            self.assertEqual(exported[offset:], original[-4:])
        self.assertEqual(checkpoint.read_bytes(), original)

    def test_C02_C05_E03_E04_fixed_comparison_and_selected_image_export(self):
        from PIL import Image, PngImagePlugin
        from test_guided_training import ComparisonGraphTests
        run_id, checkpoint_id, _ = self.checkpoint()
        prompt_id = str(uuid.uuid4())
        history = {}
        calls = []
        def provider(method, path, **kwargs):
            if path == 'object_info':
                registry = ComparisonGraphTests().registry()
                registry['CheckpointLoaderSimple']['input']['required']['ckpt_name'] = [['sd_xl_base_1.0.safetensors']]
                registry['LoraLoader']['input']['required']['lora_name'] = [[p.relative_to(self.root / 'models/loras').as_posix()
                    for p in (self.root / 'models/loras').rglob('*.safetensors')]]
                return registry
            if path == 'prompt':
                workflow = kwargs['json']['prompt']
                calls.append(workflow)
                self.assertEqual(workflow['13']['inputs']['seed'], workflow['23']['inputs']['seed'])
                self.assertEqual(workflow['13']['inputs']['steps'], 20)
                outputs = {}
                for node_id in ['15', '25']:
                    prefix = workflow[node_id]['inputs']['filename_prefix']
                    folder = str(Path(prefix).parent)
                    destination = self.root / 'outputs/comfy' / folder
                    destination.mkdir(parents=True, exist_ok=True)
                    metadata = PngImagePlugin.PngInfo(); metadata.add_text('private', 'image-metadata-canary')
                    Image.new('RGB', (32, 32)).save(destination / (node_id + '.png'), pnginfo=metadata)
                    outputs[node_id] = {'images': [dict(filename=node_id + '.png', subfolder=folder, type='output')]}
                history[prompt_id] = {'status': {'completed': True}, 'outputs': outputs}
                return {'prompt_id': prompt_id}
            if path.startswith('history/'):
                return history
            return {'queue_running': [], 'queue_pending': []}
        self.execution.provider = provider
        plan = self.facade.call(self.a, 'comparison_plan', dict(run_id=run_id, checkpoint_id=checkpoint_id, prompt='portrait'))
        self.store.approve(plan['id'], True)
        with patch('apps.Portal.mcp_server.operations.gpu_guard.conflicts', return_value=[]), \
             patch('apps.Portal.mcp_server.operations.gpu_guard.managed_conflicts', return_value=[]):
            result = self.facade.call(self.a, 'comparison_start', dict(plan_id=plan['id'], request_id=str(uuid.uuid4())))
        self.assertEqual(result['state'], 'succeeded')
        self.assertEqual(result['result']['image_count'], 2)
        self.assertEqual(len(calls), 1)
        export = self.facade.call(self.a, 'export_plan', dict(run_id=run_id, checkpoint_id=checkpoint_id,
            comparison_id=result['operation_id'], images=[1]))
        self.store.approve(export['id'], True)
        result = self.facade.call(self.a, 'export_create', dict(plan_id=export['id'], request_id=str(uuid.uuid4())))
        self.assertEqual(result['state'], 'succeeded')
        op = self.store.operation(self.a, result['operation_id'])
        with zipfile.ZipFile(self.root / op['artifact']['path']) as archive:
            self.assertIn('samples/0.png', archive.namelist())
            self.assertNotIn('samples/1.png', archive.namelist())
            image = archive.read('samples/0.png')
            self.assertNotIn(b'image-metadata-canary', image)
            with Image.open(io.BytesIO(image)) as decoded:
                self.assertEqual(decoded.size, (32, 32))

    def test_E05_E06_E08_authenticated_download_and_revocation(self):
        from starlette.testclient import TestClient
        run_id, checkpoint_id, path = self.checkpoint()
        # A larger safe tensor makes streaming span multiple revocation checks.
        payload = b'\0' * (1024 * 1024)
        header = canonical({'x': {'dtype': 'F32', 'shape': [len(payload) // 4], 'data_offsets': [0, len(payload)]}})
        path.write_bytes(len(header).to_bytes(8, 'little') + header + payload)
        plan = self.facade.call(self.a, 'export_plan', dict(run_id=run_id, checkpoint_id=checkpoint_id))
        self.store.approve(plan['id'], True)
        result = self.facade.call(self.a, 'export_create', dict(plan_id=plan['id'], request_id=str(uuid.uuid4())))
        self.runtime.facade = self.facade
        self.runtime.setup_sdk()
        url = '/mcp-artifacts/' + result['operation_id']
        with TestClient(self.app(), base_url='http://127.0.0.1:7878') as client:
            self.assertEqual(client.get(url).status_code, 401)
            self.assertEqual(client.get(url, headers={'Authorization': 'Bearer ' + self.token_b}).status_code, 404)
            headers = {'Authorization': 'Bearer ' + self.token}
            self.assertEqual(client.get(url, headers={**headers, 'Range': 'bytes=0-1,3-4'}).status_code, 404)
            response = client.get(url, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
            self.assertTrue(response.content.startswith(b'PK'))
        async def revoked_stream():
            chunks = []
            scope = dict(type='http', method='GET', path=url, query_string=b'', scheme='http',
                server=('127.0.0.1', 7878), client=('127.0.0.1', 1234), http_version='1.1',
                asgi={'version': '3.0', 'spec_version': '2.4'},
                headers=[(b'host', b'127.0.0.1:7878'), (b'authorization', ('Bearer ' + self.token).encode())])
            async def receive():
                return {'type': 'http.request', 'body': b''}
            async def send(message):
                if message['type'] == 'http.response.body' and message.get('body'):
                    chunks.append(message['body'])
                    self.store.revoke(self.a)
            await self.runtime.handle(scope, receive, send)
            self.assertEqual(sum(map(len, chunks)), 256 * 1024)
        asyncio.run(revoked_stream())

    def test_F08_F09_W09_storage_and_ledger_fail_before_effect(self):
        self.execution.budget = 1
        with self.assertRaises(Rejected):
            self.plan()
        self.assertEqual(self.queue.list(), [])
        self.execution.budget = 32 * GIB
        request = self.plan()
        with patch('apps.Portal.mcp_server.store.MAX_OPERATIONS', 0), self.assertRaises(Rejected):
            self.facade.call(self.a, 'training_start', request)
        self.assertEqual(self.queue.list(), [])
        with patch.object(self.store.files, 'write', side_effect=OSError('secret-write-canary')), self.assertRaises(OSError):
            self.facade.call(self.a, 'training_start', request)
        self.assertEqual(self.queue.list(), [])

    def test_A07_restart_invalidates_approvals_and_clock_rollback_fails_closed(self):
        request = self.plan()
        self.store.close()
        fresh = Store(self.root)
        self.addCleanup(fresh.close)
        fresh.claim()
        with self.assertRaises(Rejected):
            fresh.accept(self.a, 'training_start', request, 'training:submit')
        fresh.clock = lambda: 1
        with self.assertRaises(Rejected):
            fresh.authenticate(self.token)

    def test_W06_second_owner_cannot_dispatch(self):
        other = Store(self.root)
        self.addCleanup(other.close)
        with self.assertRaises(OSError):
            other.claim()

    def test_F03_F07_destination_race_never_overwrites(self):
        source = 'datasets/1_private/a.txt'
        target = 'config/mcp/copy'
        expected = self.store.files.digest(source)
        (self.root / target).write_bytes(b'keep-me')
        with self.assertRaises(FileExistsError):
            self.store.files.copy_verified(source, target, expected)
        self.assertEqual((self.root / target).read_bytes(), b'keep-me')

    def test_C01_C04_lost_comfy_reply_never_submits_twice(self):
        run_id, checkpoint, _ = self.checkpoint()
        request = dict(run_id=run_id, checkpoint_id=checkpoint, prompt='synthetic test')
        before = set(self.root.rglob('*'))
        plan = self.facade.call(self.a, 'comparison_plan', request)
        self.assertEqual(set(self.root.rglob('*')), before)
        self.store.approve(plan['id'], True)
        calls = []
        def provider(method, path, **kwargs):
            if method == 'GET':
                return {}
            calls.append(kwargs)
            raise OSError('accepted but response lost secret-canary')
        self.execution.provider = provider
        execute = dict(plan_id=plan['id'], request_id=str(uuid.uuid4()))
        with patch('apps.Portal.mcp_server.operations.graph', return_value={}), \
             patch('apps.Portal.mcp_server.operations.gpu_guard.conflicts', return_value=[]), \
             patch('apps.Portal.mcp_server.operations.gpu_guard.managed_conflicts', return_value=[]):
            result = self.facade.call(self.a, 'comparison_start', execute)
            self.assertEqual(result['state'], 'unknown')
            self.assertNotIn('secret-canary', json.dumps(result))
            self.facade.call(self.a, 'comparison_start', execute)
        self.assertEqual(len(calls), 1)

    def test_W04_process_kill_after_acceptance_and_dispatch_never_repeats(self):
        self.store.close()
        code = '''
import json, sys, time
from pathlib import Path
from apps.Portal.mcp_server.store import Store
root, principal, stage, request_id = sys.argv[1:]
assert (Path(root) / '.mcp-test-workspace').read_text() == 'disposable'
s = Store(root); s.claim()
p = s.plan(principal, 'export', {'allocation_bytes': 0}, {'files': []})
s.approve(p['id'], True)
request = {'plan_id': p['id'], 'request_id': request_id}
op, _ = s.accept(principal, 'export_create', request, 'artifacts:export')
if stage == 'dispatch': s.update_operation(op['id'], state='dispatching')
print(json.dumps({'request': request, 'id': op['id']}), flush=True)
time.sleep(60)
'''
        (self.root / '.mcp-test-workspace').write_text('disposable')
        for stage in ['accept', 'dispatch']:
            with self.subTest(stage=stage):
                # Distinct principal avoids bypassing an earlier unresolved operation.
                principal, _ = self.store.create_client(stage, sorted(SCOPES), [], [])
                proc = subprocess.Popen([sys.executable, '-c', code, str(self.root), principal, stage, str(uuid.uuid4())],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    import select
                    self.assertTrue(select.select([proc.stdout], [], [], 10)[0], 'child failed to reach crash barrier')
                    value = json.loads(proc.stdout.readline())
                    proc.kill()
                    proc.wait(timeout=10)
                    fresh = Store(self.root)
                    try:
                        fresh.claim()
                        replay, created = fresh.accept(principal, 'export_create', value['request'], 'artifacts:export')
                        self.assertFalse(created)
                        self.assertEqual(replay['id'], value['id'])
                        self.assertEqual(replay['state'], 'unknown')
                    finally:
                        fresh.close()
                finally:
                    if proc.poll() is None:
                        proc.kill(); proc.wait(timeout=10)
                    proc.stdout.close(); proc.stderr.close()


if __name__ == '__main__':
    unittest.main()
