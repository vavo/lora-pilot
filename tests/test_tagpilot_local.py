import asyncio
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from apps.Portal.services import tagpilot_ai, tagpilot_local


class TagPilotLocalTests(unittest.TestCase):
    def test_local_provider_honors_shared_model_directory(self):
        self.assertEqual(tagpilot_local.model_directory({'MODELS_DIR': '/custom/models'}),
                         Path('/custom/models/text_encoders/Qwen3-VL-2B-Instruct'))

    def image_bytes(self):
        output = io.BytesIO()
        Image.new('RGB', (256, 256), 'red').save(output, 'PNG')
        return output.getvalue()

    def test_local_provider_uses_shared_offline_worker_without_key(self):
        directories = []
        def worker(command, **kwargs):
            directory = Path(command[2])
            directories.append(directory)
            self.assertEqual(Path(command[1]).name, 'tagpilot_local.py')
            self.assertEqual(kwargs['env']['HF_HUB_OFFLINE'], '1')
            self.assertEqual(kwargs['env']['TRANSFORMERS_OFFLINE'], '1')
            request = json.loads((directory / 'vision-request.json').read_text())
            self.assertEqual(request['mode'], 'text')
            self.assertIn('caption', request['prompt'])
            self.assertTrue((directory / 'image.png').is_file())
            (directory / 'vision-result.json').write_text(json.dumps({'image.png': {'text': 'A red image.'}}))
        with patch.object(tagpilot_local, 'model_ready', return_value=True), \
             patch.object(tagpilot_local.subprocess, 'run', side_effect=worker):
            result = asyncio.run(tagpilot_ai.generate(provider='local', mode='caption', prompt='',
                image_bytes=self.image_bytes(), mime_type='image/png', environ={}))
        self.assertEqual(result['text'], 'A red image.')
        self.assertEqual(result['provider'], 'local')
        self.assertTrue(all(not directory.exists() for directory in directories))

    def test_missing_weights_are_actionable_and_never_launch_worker(self):
        with patch.object(tagpilot_local, 'model_ready', return_value=False), \
             patch.object(tagpilot_local.subprocess, 'run') as worker:
            with self.assertRaisesRegex(ValueError, 'Install dataset-local-captioner'):
                tagpilot_local.generate(self.image_bytes(), 'caption', {})
        worker.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'does not use an API key'):
            tagpilot_ai.secret_name_for_provider('local')

    def test_worker_failure_has_no_cloud_fallback(self):
        with patch.object(tagpilot_local, 'model_ready', return_value=True), \
             patch.object(tagpilot_local.subprocess, 'run', side_effect=OSError('failure')):
            with self.assertRaisesRegex(tagpilot_ai.ProviderRequestError, 'no external API'):
                asyncio.run(tagpilot_ai.generate(provider='local', mode='tags', prompt='',
                    image_bytes=self.image_bytes(), mime_type='image/png', environ={}))

    def test_invalid_image_is_rejected_before_inference(self):
        with patch.object(tagpilot_local, 'model_ready', return_value=True), \
             patch.object(tagpilot_local.subprocess, 'run') as worker:
            with self.assertRaises(ValueError):
                tagpilot_local.generate(b'invalid', 'caption', {})
        worker.assert_not_called()
