import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock
from fastapi import HTTPException
from apps.Portal.services.storage import Storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run_id = 'a' * 32
        self.history = self.root / 'config/training' / self.run_id
        self.images = self.history / 'images'
        self.images.mkdir(parents=True)
        (self.images / 'image.png').write_bytes(b'private copy')
        (self.images / 'latents.npz').write_bytes(b'cache')
        (self.history / 'run.json').write_text('history kept')
        self.output = self.root / 'outputs' / ('portrait-' + self.run_id)
        self.output.mkdir(parents=True)
        self.checkpoint = self.output / 'portrait.safetensors'
        self.checkpoint.write_bytes(b'checkpoint')
        self.models = self.root / 'models'
        self.models.mkdir()
        (self.models / 'base.safetensors').write_bytes(b'base model')
        source = self.root / 'datasets/1_portrait'
        source.mkdir(parents=True)
        (source / 'image.png').write_bytes(b'original')
        self.run = dict(id=self.run_id, status='succeeded', spec={'output_name': 'portrait'}, output_dir=str(self.output))
        self.queue = Mock(lock=threading.RLock())
        self.queue.list.side_effect = lambda: [self.run]
        self.queue.orphan_conflicts.return_value = []
        self.downloads = Mock(lock=threading.RLock(), jobs={})
        self.conflicts = Mock(return_value=[])
        self.storage = Storage(self.root, self.models, self.queue, self.downloads, self.conflicts)

    def ids(self):
        return [item['id'] for item in self.storage.inventory()['candidates']]

    def test_inventory_and_explicit_selection_preserve_everything_else(self):
        data = self.storage.inventory()
        self.assertEqual(len(data['categories']), 5)
        self.assertEqual(len(data['candidates']), 3)
        item = next(item for item in data['candidates'] if item['category'] == 'Training caches')
        plan = self.storage.preview([item['id']])
        self.assertTrue((self.images / 'latents.npz').exists())
        result = self.storage.cleanup(plan['token'])
        self.assertTrue(result['complete'])
        self.assertEqual(result['removed_files'], 1)
        self.assertTrue(self.checkpoint.exists())
        self.assertTrue((self.images / 'image.png').exists())
        self.assertTrue((self.models / 'base.safetensors').exists())
        self.assertTrue((self.history / 'run.json').exists())
        self.assertTrue((self.root / 'datasets/1_portrait/image.png').exists())
        with self.assertRaises(HTTPException):
            self.storage.cleanup(plan['token'])

    def test_active_jobs_downloads_and_unknown_workloads_block_cleanup(self):
        ids = self.ids()
        for state in ('running', 'queued', 'stopping'):
            self.run['status'] = state
            with self.assertRaises(HTTPException):
                self.storage.preview(ids)
        self.run['status'] = 'succeeded'
        self.downloads.jobs['model'] = Mock(state='running')
        with self.assertRaises(HTTPException): self.storage.preview(ids)
        self.downloads.jobs.clear()
        self.conflicts.return_value = ['GPU unavailable']
        with self.assertRaises(HTTPException): self.storage.preview(ids)
        self.assertTrue(self.checkpoint.exists())

    def test_job_started_after_preview_invalidates_cleanup(self):
        plan = self.storage.preview(self.ids())
        self.run['status'] = 'running'
        with self.assertRaises(HTTPException): self.storage.cleanup(plan['token'])
        self.assertTrue(self.checkpoint.exists())

    def test_changed_or_added_files_require_new_preview(self):
        for change in ('modify', 'add'):
            plan = self.storage.preview(self.ids())
            if change == 'modify': self.checkpoint.write_bytes(b'updated checkpoint')
            else: (self.images / 'new.png').write_bytes(b'new image')
            with self.assertRaises(HTTPException): self.storage.cleanup(plan['token'])
            self.assertTrue((self.images / 'image.png').exists())

    def test_symlinks_hardlinks_and_shared_model_references_are_protected(self):
        outside = self.root / 'private.txt'
        outside.write_text('private')
        (self.images / 'linked.png').symlink_to(outside)
        (self.models / 'shared.safetensors').symlink_to(self.checkpoint)
        os.link(self.images / 'image.png', self.root / 'shared.png')
        items = self.storage.inventory()['candidates']
        self.assertEqual([item['category'] for item in items], ['Training caches'])
        plan = self.storage.preview([item['id'] for item in items])
        self.storage.cleanup(plan['token'])
        self.assertEqual(outside.read_text(), 'private')
        self.assertTrue(self.checkpoint.exists())
        self.assertTrue((self.images / 'image.png').exists())

    def test_swapped_parent_cannot_redirect_cleanup(self):
        plan = self.storage.preview(self.ids())
        moved = self.history / 'moved'
        self.images.rename(moved)
        self.images.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(HTTPException): self.storage.cleanup(plan['token'])
        self.assertTrue((moved / 'image.png').exists())
        self.assertTrue(self.checkpoint.exists())

    def test_forged_expired_or_duplicate_selection_is_rejected(self):
        with self.assertRaises(HTTPException): self.storage.preview(['../../models/base.safetensors'])
        ids = self.ids()
        with self.assertRaises(HTTPException): self.storage.preview([ids[0], ids[0]])
        plan = self.storage.preview(ids)
        self.storage.plans[plan['token']]['expires'] = 0
        with self.assertRaises(HTTPException): self.storage.cleanup(plan['token'])
        self.assertTrue(self.checkpoint.exists())

    def test_linked_ancestor_is_excluded_and_blocks_preview(self):
        config = self.root / 'config'
        moved = self.root / 'moved-config'
        config.rename(moved)
        config.symlink_to(moved, target_is_directory=True)
        data = self.storage.inventory()
        self.assertTrue(data['warnings'])
        self.assertFalse(any(item['category'] == 'Dataset snapshot' for item in data['candidates']))
        with self.assertRaises(HTTPException): self.storage.preview(self.ids())
        self.assertTrue((moved / 'training' / self.run_id / 'images/image.png').exists())
