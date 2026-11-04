import importlib.util
import json
import os
import sys
from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi import HTTPException


APP_DIR = Path(__file__).resolve().parents[1] / 'apps' / 'MediaPilot'


class MediaPilotUpscaleTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.enterContext(chdir(self.root))
        self.app_dir = self.root / 'MediaPilot'
        self.app_dir.mkdir()
        template = 'comfy_upscale_workflow.example.json'
        (self.app_dir / template).write_bytes((APP_DIR / template).read_bytes())
        # Exercise the relative setting shipped in .env.example from a different cwd.
        config = dict(line.split('=', 1) for line in (APP_DIR / '.env.example').read_text().splitlines()
                      if line and not line.startswith('#'))
        config.update({key: str(self.root / key) for key in ('MEDIAPILOT_OUTPUT_DIR', 'MEDIAPILOT_INVOKEAI_DIR',
                      'MEDIAPILOT_THUMBS_DIR', 'MEDIAPILOT_DB_FILE')})
        spec = importlib.util.spec_from_file_location('mediapilot_upscale_test', APP_DIR / 'main.py')
        self.mp = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, config), patch.object(sys, 'path', sys.path.copy()):
            spec.loader.exec_module(self.mp)
        self.mp.BASE_DIR = str(self.app_dir)

    def test_bundled_workflow_queues_selected_image_without_a_model(self):
        mp = self.mp
        (Path(mp.OUTPUT_DIR) / 'My photo.png').touch()
        with patch.object(mp, 'upload_image_to_comfy', return_value='inputs/My photo (1).png'), \
             patch.object(mp, 'submit_workflow_to_comfy', return_value='prompt-id') as submit:
            response = mp.upscale_bulk(mp.BulkUpscalePayload(filenames=['My photo.png']))
        self.assertEqual(response['submitted'][0]['prompt_id'], 'prompt-id')
        graph = submit.call_args.args[1]
        self.assertEqual([graph[n]['class_type'] for n in ('1', '2', '3')], ['LoadImage', 'ImageScaleBy', 'SaveImage'])
        self.assertEqual(graph['1']['inputs']['image'], 'inputs/My photo (1).png')
        self.assertEqual(graph['2']['inputs'], {'image': ['1', 0], 'upscale_method': 'lanczos', 'scale_by': 2})
        self.assertEqual(graph['3']['inputs'], {'images': ['2', 0], 'filename_prefix': 'mediapilot-upscaled/My-photo'})

    def test_custom_workflow_wins_and_invalid_custom_file_is_not_ignored(self):
        custom = self.app_dir / 'comfy_upscale_workflow.json'
        custom.write_text(json.dumps({'custom': True}))
        self.assertEqual(self.mp.load_upscale_workflow_template(), {'custom': True})
        custom.write_text('not json')
        with self.assertRaises(HTTPException) as error:
            self.mp.load_upscale_workflow_template()
        self.assertIn('Invalid workflow JSON', error.exception.detail)

    def test_missing_explicit_override_does_not_queue_the_default(self):
        self.mp.UPSCALE_WORKFLOW_FILE = str(self.root / 'missing.json')
        with self.assertRaises(HTTPException) as error:
            self.mp.load_upscale_workflow_template()
        self.assertIn('missing.json', error.exception.detail)

    def test_existing_cwd_relative_override_still_works(self):
        (self.root / 'comfy_upscale_workflow.json').write_text('{"from": "cwd"}')
        self.assertEqual(self.mp.load_upscale_workflow_template(), {'from': 'cwd'})
