import io
import os
import unittest
import zipfile
from unittest.mock import patch

from PIL import Image
import test_mediapilot_video


class MediaPilotLatestTests(unittest.TestCase):
    setUp = test_mediapilot_video.MediaPilotVideoTests.setUp

    def media(self, root, name, timestamp):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == '.png':
            Image.new('RGB', (32, 32)).save(path)
        else:
            path.write_bytes(name.encode())
        os.utime(path, (1700000000 + timestamp, 1700000000 + timestamp))
        return path

    def latest(self, **params):
        response = self.client.get('/mediapilot/images', params={'folder': '_latest', **params})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_recursive_order_pagination_and_original_folder_views(self):
        self.media(self.mp.OUTPUT_ROOT, 'same.png', 10)
        self.media(self.mp.OUTPUT_ROOT, 'nested/deep/same.png', 30)
        self.media(self.mp.INVOKEAI_ROOT, 'clips/new #1.mp4', 40)
        self.media(self.mp.OUTPUT_ROOT, 'tag/old.mp4', 20)
        first = self.latest(limit=2)
        second = self.latest(limit=2, page=2)
        self.assertEqual(first['pages'], 2)
        self.assertEqual([i['filename'] for i in first['images'] + second['images']], [
            'invoke/clips/new #1.mp4', 'output/nested/deep/same.png',
            'output/tag/old.mp4', 'output/same.png'])
        self.assertEqual(first['images'][0]['full_url'], './invoke/clips/new%20%231.mp4')
        for item in first['images'] + second['images']:
            self.assertEqual(self.client.get('/mediapilot/' + item['full_url'][2:]).status_code, 200)
        root = self.client.get('/mediapilot/images', params={'folder': '_root'}).json()
        self.assertEqual([i['filename'] for i in root['images']], ['same.png'])
        with patch.object(self.mp, 'extract_metadata', return_value={'prompt': 'robot'}):
            self.assertEqual(len(self.latest(search='robot')['images']), 2)

    def test_duplicate_names_keep_likes_moves_deletes_and_downloads_separate(self):
        first = self.media(self.mp.OUTPUT_ROOT, 'a/same.png', 1)
        second = self.media(self.mp.OUTPUT_ROOT, 'b/same.png', 2)
        response = self.client.post('/mediapilot/like/output/a/same.png?folder=_latest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual({i['filename']: i['liked'] for i in self.latest()['images']},
                         {'output/a/same.png': True, 'output/b/same.png': False})
        response = self.client.post('/mediapilot/download/bulk', json={
            'folder': '_latest', 'filenames': ['output/a/same.png', 'output/b/same.png']})
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(archive.namelist(), ['output/a/same.png', 'output/b/same.png'])
        response = self.client.post('/mediapilot/tag', params={
            'filename': 'output/a/same.png', 'old_folder': '_latest', 'new_folder': 'kept'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(first.exists())
        self.assertTrue(second.exists())
        kept = next(i for i in self.latest()['images'] if i['filename'] == 'output/kept/same.png')
        self.assertTrue(kept['liked'])
        response = self.client.delete('/mediapilot/selection', params={
            'folder': '_latest', 'filename': 'output/b/same.png'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(second.exists())
        self.assertTrue((self.mp.OUTPUT_ROOT / 'kept/same.png').exists())

    def test_upscale_uses_original_source(self):
        source = self.media(self.mp.OUTPUT_ROOT, 'nested/image.png', 1)
        with patch.object(self.mp, 'load_upscale_workflow_template', return_value={}), \
             patch.object(self.mp, 'upload_image_to_comfy', return_value='input.png') as upload, \
             patch.object(self.mp, 'ensure_workflow_input_image', return_value={}), \
             patch.object(self.mp, 'submit_workflow_to_comfy', return_value='job'):
            response = self.client.post('/mediapilot/upscale/bulk', json={
                'folder': '_latest', 'filenames': ['output/nested/image.png']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(upload.call_args.args[1:], (source.resolve(), 'image.png'))

    def test_excludes_internal_folders_and_symlinks_and_rejects_traversal(self):
        outside = self.media(self.root, 'outside/secret.png', 1)
        self.media(self.mp.OUTPUT_ROOT, '_thumbs/cached.png', 2)
        self.media(self.mp.OUTPUT_ROOT, '.hidden/private.png', 3)
        (self.mp.OUTPUT_ROOT / 'escape.png').symlink_to(outside)
        (self.mp.OUTPUT_ROOT / 'linked').symlink_to(outside.parent)
        self.assertEqual(self.latest()['images'], [])
        for name in ('output/../outside/secret.png', 'other/secret.png', 'output/escape.png'):
            response = self.client.delete('/mediapilot/selection', params={
                'folder': '_latest', 'filename': name})
            self.assertEqual(response.status_code, 400)
        self.assertTrue(outside.exists())
        response = self.client.post('/mediapilot/tag', params={
            'filename': 'image.png', 'old_folder': '_root', 'new_folder': '_latest'})
        self.assertEqual(response.status_code, 400)
