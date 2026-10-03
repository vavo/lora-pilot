import io
import json
import zipfile
import unittest
from urllib.parse import urlencode

from PIL import Image, PngImagePlugin
from apps.Portal.services.training_runs import write_json
import test_training_comparison_api


class ExperimentExportTests(unittest.TestCase):
    setUp = test_training_comparison_api.TrainingComparisonApiTests.setUp
    def preview(self, **extra):
        return self.client.post(self.prefix + '/export/preview', json=dict(artifact=self.artifact.name, **extra))

    def download(self, **extra):
        response = self.preview(**extra)
        self.assertEqual(response.status_code, 200, response.text)
        query = dict(artifact=self.artifact.name, token=response.json()['token'], **extra)
        return self.client.get(self.prefix + '/export?' + urlencode(query, doseq=True))

    def test_package_excludes_credentials_paths_and_dataset(self):
        self.run['template'].update(api_key='secret', huggingface_token='secret',
                                    train_data_dir='/private/images', network_dim=32)
        self.queue.save(self.run)
        response = self.download(trigger_words='orangebot', sample_prompt='orangebot waves')
        self.assertEqual(response.status_code, 200, response.text)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(set(archive.namelist()), {'checkpoint/example.safetensors', 'experiment.json', 'README.md'})
            metadata = archive.read('experiment.json').decode()
            self.assertNotIn('secret', metadata)
            self.assertNotIn(str(self.root), metadata)
            self.assertNotIn('train_data_dir', metadata)
            self.assertEqual(json.loads(metadata)['settings']['network_dim'], 32)
            self.assertEqual(json.loads(metadata)['trigger_words'], 'orangebot')

    def test_only_selected_comparison_image_without_embedded_metadata(self):
        root = self.root / 'outputs/comfy/LoRA-Pilot' / self.run['id']
        root.mkdir(parents=True)
        pnginfo = PngImagePlugin.PngInfo(); pnginfo.add_text('workflow', 'private value')
        Image.new('RGB', (32, 32)).save(root / 'sample.png', pnginfo=pnginfo)
        comparison = dict(images=[dict(label='Without LoRA', url='/proxy/comfy/view?' + urlencode(
            dict(subfolder=f'LoRA-Pilot/{self.run["id"]}', filename='sample.png', type='output')))],
            request=dict(prompt='orangebot', seed=42, strength=1))
        write_json(self.queue.directory(self.run['id']) / 'comparison.json', comparison)
        with zipfile.ZipFile(io.BytesIO(self.download(images=[0]).content)) as archive:
            with Image.open(io.BytesIO(archive.read('samples/00.png'))) as image:
                self.assertNotIn('workflow', image.info)
        with zipfile.ZipFile(io.BytesIO(self.download().content)) as archive:
            self.assertNotIn('samples/00.png', archive.namelist())

    def test_cross_run_and_out_of_bounds_image_requests_are_rejected(self):
        write_json(self.queue.directory(self.run['id']) / 'comparison.json', dict(images=[dict(label='bad',
            url='/proxy/comfy/view?subfolder=../../private&filename=secret.png')]))
        self.assertEqual(self.preview(images=[0]).status_code, 400)
        self.assertEqual(self.preview(images=[-1]).status_code, 400)

    def test_changed_checkpoint_requires_new_preview(self):
        preview = self.preview().json()
        self.artifact.write_bytes(b'changed')
        response = self.client.get(self.prefix + '/export', params=dict(artifact=self.artifact.name, token=preview['token']))
        self.assertEqual(response.status_code, 409)

    def test_active_run_and_symlink_checkpoint_are_rejected(self):
        self.run['status'] = 'running'; self.queue.save(self.run)
        self.assertEqual(self.preview().status_code, 409)
        self.run['status'] = 'succeeded'; self.queue.save(self.run)
        self.artifact.unlink(); self.artifact.symlink_to(self.config)
        self.assertEqual(self.preview().status_code, 404)
