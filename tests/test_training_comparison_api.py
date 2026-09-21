import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from apps.Portal.services import gpu_guard
from apps.Portal.services.training_api import create_router
import test_guided_training


class TrainingComparisonApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.models = self.root / 'separate-model-library'
        base = self.models / 'checkpoints/base.safetensors'
        base.parent.mkdir(parents=True)
        base.write_bytes(b'base fixture')
        dataset = self.root / 'datasets/1_example'
        dataset.mkdir(parents=True)
        (dataset / 'a.png').write_bytes(b'image fixture')
        self.config = self.root / 'base.toml'
        self.config.write_text(f'pretrained_model_name_or_path = "{base}"\nvae = "{base}"\n')
        self.spec = dict(dataset_name='1_example', output_name='example', family='sdxl', profile='regular')
        self.addCleanup(setattr, gpu_guard, 'managed_conflicts', gpu_guard.managed_conflicts)
        router, self.queue = create_router(self.root, self.models, lambda _: dataset,
            lambda _: self.config, lambda _: 'base', lambda: [])
        start = self.queue.start
        self.queue.start = lambda: start(background=False)
        self.addCleanup(self.queue.close)
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.run = self.client.post('/api/training/runs', json=self.spec).json()
        self.run = self.queue.get(self.run['id'])
        self.run['status'] = 'succeeded'
        self.queue.save(self.run)
        self.artifact = Path(self.run['output_dir']) / 'example.safetensors'
        self.artifact.write_bytes(b'lora fixture')
        self.prefix = '/api/training/runs/' + self.run['id']
        self.request = dict(artifact=self.artifact.name, prompt='portrait of example_person', seed=42)
        self.registry = test_guided_training.ComparisonGraphTests().registry()
        self.library_name = f'ControlPilot/{self.run["id"]}/{self.artifact.name}'
        self.registry['LoraLoader']['input']['required']['lora_name'] = [[self.library_name]]

    def test_checkpoint_download_is_contained_and_refuses_active_runs(self):
        response = self.client.get(self.prefix + '/artifacts/' + self.artifact.name)
        self.assertEqual(response.content, b'lora fixture')
        self.assertIn('attachment;', response.headers['content-disposition'])
        outside = self.root / 'outside.safetensors'
        outside.write_bytes(b'private')
        (self.artifact.parent / 'link.safetensors').symlink_to(outside)
        self.assertEqual(self.client.get(self.prefix + '/artifacts/link.safetensors').status_code, 404)
        self.assertEqual(self.client.get(self.prefix + '/artifacts/%2E%2E%2Foutside.safetensors').status_code, 404)
        self.run['status'] = 'running'
        self.queue.save(self.run)
        self.assertEqual(self.client.get(self.prefix + '/artifacts/' + self.artifact.name).status_code, 409)

    def test_history_search_filters_and_pagination_include_older_runs(self):
        for index in range(105):
            run = dict(self.run, id=f'{index:032x}', spec=dict(self.spec, output_name=f'portrait-{index}', family='flux1'))
            directory = self.queue.directory(run['id'])
            directory.mkdir(exist_ok=True)
            self.queue.save(run)
        result = self.client.get('/api/training/runs?search=portrait&family=flux1&status=succeeded&offset=100').json()
        self.assertEqual(result['total'], 105)
        self.assertEqual(len(result['runs']), 5)
        self.assertEqual(self.client.get('/api/training/runs?search=not-found').json()['total'], 0)
        self.assertEqual(self.client.get('/api/training/runs?offset=-1').status_code, 422)

    def test_library_copy_keeps_originals_and_refuses_collisions(self):
        result = self.client.post(self.prefix + '/library')
        self.assertEqual(result.status_code, 200, result.text)
        target = self.models / 'loras' / self.library_name
        self.assertEqual(target.read_bytes(), self.artifact.read_bytes())
        self.assertTrue(self.artifact.exists())
        detail = self.client.get(self.prefix).json()
        self.assertEqual(detail['library_destination'], str(target.parent))
        self.assertEqual(self.client.post(self.prefix + '/library').status_code, 200)
        target.write_bytes(b'user-edited copy')
        self.assertEqual(self.client.post(self.prefix + '/library').status_code, 409)
        self.assertEqual(target.read_bytes(), b'user-edited copy')

    def test_existing_partial_file_is_not_deleted(self):
        partial = self.models / 'loras' / (self.library_name + '.partial')
        partial.parent.mkdir(parents=True)
        partial.write_bytes(b'incomplete user copy')
        self.assertEqual(self.client.post(self.prefix + '/library').status_code, 409)
        self.assertEqual(partial.read_bytes(), b'incomplete user copy')

    def test_comparison_rejects_traversal_and_symlinked_artifacts(self):
        secret = self.root / 'outside.safetensors'
        secret.write_bytes(b'outside the run')
        (self.artifact.parent / 'linked.safetensors').symlink_to(secret)
        with patch('apps.Portal.services.training_api.comfy') as remote:
            for name in ('../outside.safetensors', str(secret), 'linked.safetensors'):
                response = self.client.post(self.prefix + '/comparison/prepare', json=dict(self.request, artifact=name))
                self.assertEqual(response.status_code, 400, response.text)
            remote.assert_not_called()
        self.assertEqual(secret.read_bytes(), b'outside the run')

    def test_generation_persists_results_and_rejects_duplicate_submission(self):
        def comfy(method, path, **kwargs):
            if path == 'object_info':
                return self.registry
            if path == 'prompt':
                self.assertEqual(kwargs['json']['prompt']['13']['inputs']['seed'], 42)
                return {'prompt_id': 'job-1'}
            if path == 'history/job-1':
                return {}
            return {'queue_running': [], 'queue_pending': [[0, 'job-1']]}
        with patch('apps.Portal.services.training_api.comfy', side_effect=comfy):
            result = self.client.post(self.prefix + '/comparison', json=self.request)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()['status'], 'queued')
            self.assertEqual(self.client.post(self.prefix + '/comparison', json=self.request).status_code, 409)
            self.assertEqual(self.client.get(self.prefix + '/comparison/workflow').status_code, 200)
        history = {'job-1': {'status': {'completed': True}, 'outputs': {
            '15': {'images': [{'filename': 'before.png'}]}, '25': {'images': [{'filename': 'after.png'}]}}}}
        with patch('apps.Portal.services.training_api.comfy', return_value=history) as remote:
            result = self.client.get(self.prefix + '/comparison').json()
            self.assertEqual(result['status'], 'succeeded')
            self.assertEqual(len(result['images']), 2)
            self.client.get(self.prefix + '/comparison')
            remote.assert_called_once()

    def test_unconfirmed_submission_requires_explicit_reset_with_empty_queue(self):
        def comfy(method, path, **kwargs):
            if path == 'object_info':
                return self.registry
            raise HTTPException(503, 'Connection lost after submission')
        with patch('apps.Portal.services.training_api.comfy', side_effect=comfy):
            self.assertEqual(self.client.post(self.prefix + '/comparison', json=self.request).status_code, 503)
            self.assertEqual(self.client.get(self.prefix + '/comparison').json()['status'], 'unknown')
            self.assertEqual(self.client.post(self.prefix + '/comparison', json=self.request).status_code, 409)
        with patch('apps.Portal.services.training_api.comfy', return_value={'queue_running': [[0, 'job-1']]}):
            self.assertEqual(self.client.post(self.prefix + '/comparison/reset').status_code, 409)
        with patch('apps.Portal.services.training_api.comfy', return_value={'queue_running': [], 'queue_pending': []}):
            self.assertEqual(self.client.post(self.prefix + '/comparison/reset').json()['status'], 'none')

    def test_comparison_waits_for_managed_training(self):
        self.queue.proc = Mock()
        self.queue.proc.poll.return_value = None
        with patch('apps.Portal.services.training_api.comfy') as remote:
            self.assertEqual(self.client.post(self.prefix + '/comparison', json=self.request).status_code, 409)
            remote.assert_not_called()
        self.queue.proc = None

    def test_sdxl_use_settings_and_repeat_keep_saved_configuration(self):
        original = self.config.read_text()
        self.config.write_text('invalid changed defaults')
        saved = self.client.post('/api/training/runs', json=dict(self.spec, source_run_id=self.run['id']))
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.client.get('/api/training/runs/' + saved.json()['id']).json()['config_text'], original)
        self.assertEqual(self.client.post(self.prefix + '/repeat').status_code, 200)
        mismatch = self.client.post('/api/training/runs', json=dict(self.spec, family='flux1', source_run_id=self.run['id']))
        self.assertEqual(mismatch.status_code, 400)


class GpuGuardTests(unittest.TestCase):
    def test_gpu_processes_and_comfy_jobs_both_block_training(self):
        response = Mock()
        response.json.return_value = {'queue_running': [[0, 'generation']], 'queue_pending': []}
        with patch('subprocess.run', return_value=Mock(returncode=0, stdout='12, python, 4096\n')), patch('httpx.Client') as client:
            client.return_value.__enter__.return_value.get.return_value = response
            reasons = gpu_guard.conflicts()
        self.assertTrue(any('4096' in reason for reason in reasons))
        self.assertTrue(any('ComfyUI' in reason for reason in reasons))

    def test_stopped_comfy_and_empty_gpu_allow_training_but_unknown_gpu_does_not(self):
        with patch('subprocess.run', return_value=Mock(returncode=0, stdout='')) as gpu, patch('httpx.Client') as client:
            client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError('stopped')
            self.assertEqual(gpu_guard.conflicts(), [])
            gpu.side_effect = subprocess.TimeoutExpired('nvidia-smi', 5)
            self.assertTrue(gpu_guard.conflicts())
