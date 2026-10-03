import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.Portal.services.first_lora import create_router, BUNDLE, DATASET
from apps.Portal.services.guided_training import GuidedTraining
from apps.Portal.services.training_runs import TrainingRuns, write_json


class FirstLoraTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.recipe = GuidedTraining(self.root, self.root / 'models', lambda name: self.root / 'datasets' / name, None, None)
        self.queue = TrainingRuns(self.root / 'config/training', None, None, lambda: [])
        self.invalidate = Mock()
        app = FastAPI(); app.include_router(create_router(self.root, self.queue, self.recipe, self.invalidate))
        self.client = TestClient(app); self.addCleanup(self.client.close)

    def test_installs_original_eight_images_and_never_overwrites_edits(self):
        result = self.client.post('/first-lora/install')
        self.assertEqual(result.status_code, 200, result.text)
        dataset = self.root / 'datasets' / DATASET
        manifest = json.loads((BUNDLE / 'manifest.json').read_text())
        self.assertEqual(len(list(dataset.glob('*.png'))), 8)
        for name, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((dataset / name).read_bytes()).hexdigest(), digest)
        caption = next(dataset.glob('*.txt')); caption.write_text('my edited caption')
        self.assertEqual(self.client.post('/first-lora/install').status_code, 200)
        self.assertEqual(caption.read_text(), 'my edited caption')
        self.invalidate.assert_called_once()

    def test_name_collision_does_not_replace_user_dataset(self):
        dataset = self.root / 'datasets' / DATASET; dataset.mkdir(parents=True)
        (dataset / 'original.txt').write_text('keep')
        self.assertEqual(self.client.post('/first-lora/install').status_code, 409)
        self.assertEqual((dataset / 'original.txt').read_text(), 'keep')

    def test_review_is_explicit_and_invalidated_when_dataset_changes(self):
        self.client.post('/first-lora/install')
        self.assertFalse(self.client.get('/first-lora').json()['reviewed'])
        self.assertTrue(self.client.post('/first-lora/reviewed').json()['reviewed'])
        dataset = self.root / 'datasets' / DATASET
        next(dataset.glob('*.txt')).write_text('changed')
        self.assertFalse(self.client.get('/first-lora').json()['reviewed'])

    def test_progress_requires_successful_matching_training_and_comparison(self):
        self.client.post('/first-lora/install')
        dataset = self.root / 'datasets' / DATASET
        run = dict(id='a'*32, created_at='2026-10-03', status='failed', dataset=str(dataset),
                   dataset_fingerprint=self.recipe.fingerprint(dataset, self.recipe.dataset_files(dataset)),
                   spec=dict(family='sdxl'))
        directory = self.queue.directory(run['id']); directory.mkdir(parents=True)
        self.queue.save(run)
        self.assertFalse(self.client.get('/first-lora').json()['trained'])
        run['status'] = 'succeeded'; self.queue.save(run)
        self.assertTrue(self.client.get('/first-lora').json()['trained'])
        self.assertFalse(self.client.get('/first-lora').json()['compared'])
        write_json(directory / 'comparison.json', dict(status='succeeded', images=[{}, {}]))
        self.assertTrue(self.client.get('/first-lora').json()['compared'])
