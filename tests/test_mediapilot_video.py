import importlib.util
import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from PIL import Image

APP_DIR = Path(__file__).resolve().parents[1] / 'apps/MediaPilot'


class MediaPilotVideoTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        config = {key: str(self.root / key) for key in ('MEDIAPILOT_OUTPUT_DIR',
                  'MEDIAPILOT_THUMBS_DIR', 'MEDIAPILOT_INVOKEAI_DIR', 'MEDIAPILOT_DB_FILE')}
        config['MEDIAPILOT_ACCESS_PASSWORD'] = ''
        spec = importlib.util.spec_from_file_location('mediapilot_video_test', APP_DIR / 'main.py')
        self.mp = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, config), patch.object(sys, 'path', sys.path.copy()):
            spec.loader.exec_module(self.mp)
        parent = FastAPI()
        parent.mount('/mediapilot', self.mp.app)
        self.client = TestClient(parent)
        self.addCleanup(self.client.close)

    def test_lists_videos_without_image_decoding_or_thumbnails(self):
        for folder in ('_root', 'nested folder', 'InvokeAI'):
            base = self.mp.base_dir_for_folder(folder)
            base.mkdir(parents=True, exist_ok=True)
            for ext in self.mp.VIDEO_EXTS:
                (base / ('clip #' + ext.upper())).write_bytes(b'video')
            Image.new('RGB', (32, 32)).save(base / 'still.png')
            (base / 'notes.txt').write_text('not media')
            with patch.object(self.mp, 'extract_metadata', return_value={}) as metadata, \
                 patch.object(self.mp, 'make_thumb') as thumb:
                result = self.client.get('/mediapilot/images', params={'folder': folder}).json()
            self.assertEqual(len(result['images']), 7)
            self.assertEqual(metadata.call_count, 1)
            self.assertEqual(thumb.call_count, 1)
            for item in result['images']:
                if item['filename'] == 'still.png':
                    self.assertEqual(item['media_type'], 'image')
                else:
                    self.assertEqual(item['media_type'], 'video')
                    self.assertEqual(item['thumb_url'], '')
                    self.assertIn('%20%23', item['full_url'])
            self.assertEqual(self.client.get('/mediapilot/images', params={
                'folder': folder, 'search': 'lora:test'}).json()['images'], [])

    def test_mounted_video_range_requests_and_download(self):
        name = 'clip #1.mp4'
        data = bytes(range(256)) * 8
        (self.mp.OUTPUT_ROOT / name).write_bytes(data)
        response = self.client.get('/mediapilot/output/clip%20%231.mp4', headers={'Range': 'bytes=10-29'})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, data[10:30])
        self.assertEqual(response.headers['content-range'], f'bytes 10-29/{len(data)}')
        self.assertIn('video/mp4', response.headers['content-type'])
        response = self.client.post('/mediapilot/download/bulk', json={'filenames': [name]})
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(archive.read(name), data)

    def test_video_upscale_is_rejected_without_upload(self):
        (self.mp.OUTPUT_ROOT / 'clip.mp4').write_bytes(b'video')
        with patch.object(self.mp, 'upload_image_to_comfy') as upload:
            with self.assertRaises(HTTPException) as error:
                self.mp.upscale_bulk(self.mp.BulkUpscalePayload(filenames=['clip.mp4']))
        upload.assert_not_called()
        self.assertEqual(error.exception.detail['submitted'], [])
        self.assertEqual(error.exception.detail['failed'][0]['error'], 'Upscale only supports images')

    def test_video_static_paths_keep_auth_and_containment(self):
        outside = self.root / 'private.mp4'
        outside.write_bytes(b'private')
        (self.mp.OUTPUT_ROOT / 'escape.mp4').symlink_to(outside)
        response = self.client.get('/mediapilot/output/escape.mp4')
        self.assertEqual(response.status_code, 404)
        (self.mp.OUTPUT_ROOT / 'clip.mp4').write_bytes(b'video')
        with patch.object(self.mp, 'AUTH_ENABLED', True):
            response = self.client.get('/mediapilot/output/clip.mp4', headers={'Range':'bytes=0-1'})
        self.assertEqual(response.status_code, 401)
