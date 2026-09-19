import io
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from apps.Portal.services.guided_training import GuidedTraining, FLUX_MODELS
from apps.Portal.services.lora_comparison import ComparisonRequest, graph, result_images
from apps.Portal.services.training_api import create_router
from apps.Portal.services import gpu_guard


class GuidedTrainingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.models = self.root / 'models'
        self.dataset = self.root / 'datasets/1_sample'
        self.dataset.mkdir(parents=True)
        (self.dataset / 'a.png').write_bytes(b'image')
        (self.dataset / 'a.txt').write_text('a portrait')
        for _, relative in FLUX_MODELS.values():
            path = self.models / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture')
        self.ckpt = self.models / 'checkpoints/base.safetensors'
        self.ckpt.parent.mkdir()
        self.ckpt.write_bytes(b'fixture')
        self.config = self.root / 'base.toml'
        self.config.write_text(f'pretrained_model_name_or_path = "{self.ckpt}"\nvae = "{self.ckpt}"\n')
        self.resolve_dataset = Mock(return_value=self.dataset)
        self.recipe = GuidedTraining(self.root, self.models, self.resolve_dataset, lambda _: self.config, lambda _: 'base')
        self.spec = dict(dataset_name='1_sample', output_name='portrait', family='flux1', profile='quick_test')
        self.rid = 'a' * 32
        self.directory = self.root / 'config/training' / self.rid
        self.directory.mkdir(parents=True)

    def test_flux_uses_separate_reviewed_recipe_and_exact_encoders(self):
        template = self.recipe.template(self.spec)
        self.assertEqual(template['network_module'], 'networks.lora_flux')
        self.assertTrue(template['network_train_unet_only'])
        self.assertEqual(template['max_train_steps'], 600)
        self.assertEqual(template['blocks_to_swap'], 18)
        self.assertNotIn('sdxl', template)
        self.assertNotIn('shuffle_caption', template)
        self.assertEqual(self.recipe.requirements(self.spec)['missing'], [])
        (self.models / FLUX_MODELS['t5xxl'][1]).unlink()
        self.assertEqual(self.recipe.requirements(self.spec)['missing'][0]['model_name'], 'flux-t5xxl-fp16')

    def test_queued_run_keeps_template_and_detects_dataset_changes(self):
        run = self.recipe.prepare(self.spec, self.rid, self.directory)
        run['id'] = self.rid
        (self.dataset / 'a.txt').write_text('changed caption')
        with self.assertRaises(HTTPException) as error:
            self.recipe.launch(run, io.BytesIO())
        self.assertEqual(error.exception.status_code, 409)

    def test_flux_launch_uses_isolated_dataset_config_and_kohya_venv(self):
        run = self.recipe.prepare(self.spec, self.rid, self.directory)
        run['id'] = self.rid
        kohya = self.root / 'kohya'
        (kohya / 'sd-scripts').mkdir(parents=True)
        (kohya / 'sd-scripts/flux_train_network.py').touch()
        with patch.dict('os.environ', {'KOHYA_ROOT': str(kohya)}), patch('subprocess.Popen') as popen:
            self.recipe.launch(run, io.BytesIO())
        command = popen.call_args.args[0]
        self.assertEqual(command[:2], ['/opt/venvs/kohya/bin/python', '-u'])
        self.assertIn('flux_train_network.py', command[2])
        config = tomllib.loads((self.directory / 'effective.toml').read_text())
        dataset = tomllib.loads((self.directory / 'dataset.toml').read_text())
        self.assertEqual(config['output_dir'], run['output_dir'])
        copied = Path(dataset['datasets'][0]['subsets'][0]['image_dir'])
        self.assertNotEqual(copied, self.dataset)
        self.assertEqual((copied / 'a.txt').read_text(), 'a portrait')
        self.assertTrue(popen.call_args.kwargs['start_new_session'])

    def test_dataset_symlinks_and_models_outside_root_are_rejected(self):
        (self.dataset / 'escape.png').symlink_to(self.config)
        with self.assertRaises(HTTPException):
            self.recipe.prepare(self.spec, self.rid, self.directory)
        with self.assertRaises(HTTPException):
            self.recipe.requirements(dict(self.spec, family='sdxl'), {'pretrained_model_name_or_path': '/etc/passwd'})

    def test_api_history_repeat_cancel_and_config_snapshot(self):
        old_check = gpu_guard.managed_conflicts
        self.addCleanup(setattr, gpu_guard, 'managed_conflicts', old_check)
        router, queue = create_router(self.root, self.models, self.resolve_dataset, lambda _: self.config, lambda _: 'base', lambda: [])
        start = queue.start
        queue.start = lambda: start(background=False)
        self.addCleanup(queue.close)
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            first = client.post('/api/training/runs', json=self.spec)
            self.assertEqual(first.status_code, 200, first.text)
            rid = first.json()['id']
            detail = client.get('/api/training/runs/' + rid).json()
            self.assertIn('networks.lora_flux', detail['config_text'])
            second = client.post(f'/api/training/runs/{rid}/repeat').json()
            self.assertNotEqual(second['id'], rid)
            self.assertNotEqual(second['output_dir'], detail['output_dir'])
            self.assertEqual(client.post(f'/api/training/runs/{rid}/cancel').json()['status'], 'cancelled')
            self.assertEqual(len(client.get('/api/training/runs').json()['runs']), 2)
            self.assertEqual(client.post('/api/training/runs', json=dict(self.spec, output_name='../bad')).status_code, 422)


class ComparisonGraphTests(unittest.TestCase):
    def registry(self):
        # Node contracts from pinned ComfyUI v0.34.0. Model dropdowns are supplied at runtime.
        schemas = {
            'CheckpointLoaderSimple': dict(ckpt_name=['base.safetensors']),
            'UNETLoader': dict(unet_name=['flux1-dev.safetensors'], weight_dtype=['default']),
            'DualCLIPLoader': dict(clip_name1=['clip_l.safetensors'], clip_name2=['t5xxl_fp16.safetensors'], type=['flux']),
            'VAELoader': dict(vae_name=['ae.safetensors']),
            'LoraLoader': dict(model='MODEL', clip='CLIP', lora_name=['trained.safetensors'], strength_model='FLOAT', strength_clip='FLOAT'),
            'EmptyLatentImage': dict(width='INT', height='INT', batch_size='INT'),
            'EmptySD3LatentImage': dict(width='INT', height='INT', batch_size='INT'),
            'CLIPTextEncode': dict(text='STRING', clip='CLIP'),
            'FluxGuidance': dict(conditioning='CONDITIONING', guidance='FLOAT'),
            'KSampler': dict(model='MODEL', positive='CONDITIONING', negative='CONDITIONING', latent_image='LATENT', seed='INT', steps='INT', cfg='FLOAT', sampler_name=['euler', 'dpmpp_2m'], scheduler=['simple', 'normal'], denoise='FLOAT'),
            'VAEDecode': dict(samples='LATENT', vae='VAE'),
            'SaveImage': dict(images='IMAGE', filename_prefix='STRING'),
        }
        return {kind: {'input': {'required': {k: [v] for k, v in values.items()}}} for kind, values in schemas.items()}

    def run_record(self, family):
        config = {key: '/workspace/models/' + relative for key, (_, relative) in FLUX_MODELS.items()}
        if family == 'sdxl':
            config = {'pretrained_model_name_or_path': '/workspace/models/checkpoints/base.safetensors'}
        return {'id': 'a' * 32, 'spec': {'family': family}, 'template': config}

    def test_comparisons_use_same_prompt_seed_and_base_with_distinct_lora_branch(self):
        for family in ['sdxl', 'flux1']:
            with self.subTest(family=family):
                workflow = graph(self.run_record(family), ComparisonRequest(artifact='trained.safetensors', prompt='a portrait', seed=42), 'trained.safetensors', self.registry())
                self.assertEqual(workflow['13']['inputs']['seed'], workflow['23']['inputs']['seed'])
                self.assertEqual(workflow['10']['inputs']['text'], workflow['20']['inputs']['text'])
                self.assertEqual(workflow['13']['inputs']['model'], ['1', 0])
                self.assertEqual(workflow['23']['inputs']['model'], ['4', 0])
                self.assertEqual(workflow['4']['inputs']['model'], ['1', 0])
                self.assertEqual(workflow['5']['class_type'], 'EmptySD3LatentImage' if family == 'flux1' else 'EmptyLatentImage')

    def test_missing_nodes_or_unavailable_models_prevent_submission(self):
        registry = self.registry()
        del registry['LoraLoader']
        request = ComparisonRequest(artifact='trained.safetensors', prompt='portrait')
        with self.assertRaises(HTTPException):
            graph(self.run_record('sdxl'), request, 'trained.safetensors', registry)
        with self.assertRaises(HTTPException):
            graph(self.run_record('sdxl'), request, 'missing.safetensors', self.registry())

    def test_images_use_only_known_outputs_and_encoded_proxy_urls(self):
        images = result_images({'outputs': {'15': {'images': [{'filename': 'a & b.png', 'subfolder': 'test'}]}, '25': {'images': [{'filename': 'c.png'}]}}})
        self.assertEqual([item['label'] for item in images], ['Without LoRA', 'With LoRA'])
        self.assertIn('a+%26+b.png', images[0]['url'])
