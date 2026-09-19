"""Data boundaries behind dataset previews and the completed-training screen."""
import io
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from apps.Portal import app as portal

try:
    from PIL import Image
except ImportError:
    Image = None


class WorkspaceJourneyTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for name, value in {
            'WORKSPACE_ROOT': self.root, '_DATASET_ROOT': self.root / 'datasets',
            '_OUTPUT_ROOT': self.root / 'outputs', 'MODELS_DIR': self.root / 'models',
            '_tp_run_id': 'run-one', '_tp_exit_code': 0, '_tp_proc': None,
            '_tp_output_baseline': {}, '_tp_moved_run_id': None,
            '_tp_output_dir': self.root / 'outputs/run', '_tp_run_details': {'dataset': '1_sample', 'profile': 'regular'},
        }.items():
            self.stack.enter_context(patch.object(portal, name, value))
        self.dataset = self.root / 'datasets/1_sample'
        self.dataset.mkdir(parents=True)
        portal._tp_output_dir.mkdir(parents=True)

    def test_caption_coverage_matches_images_in_the_same_directory(self):
        (self.dataset / 'nested').mkdir()
        for name in ['a.jpg', 'b.png', 'nested/a.jpg', 'c.webp']:
            (self.dataset / name).write_bytes(b'image')
        for name, text in [('a.txt', 'caption'), ('a.caption', 'duplicate'), ('b.txt', ''),
                           ('orphan.txt', 'not an image'), ('nested/a.caption', 'nested caption')]:
            (self.dataset / name).write_text(text)
        (self.dataset / 'outside.jpg').symlink_to(self.root / 'outside.jpg')
        data = portal._scan_dataset_dir(self.dataset)
        self.assertEqual(data.images, 4)
        self.assertEqual(data.captioned_images, 2)
        self.assertEqual(len(data.preview_files), 3)
        self.assertNotIn('outside.jpg', data.preview_files)

    @unittest.skipIf(Image is None, "Pillow is required for image previews")
    def test_preview_is_a_bounded_jpeg_and_does_not_expose_metadata(self):
        Image.new('RGB', (600, 400), 'white').save(self.dataset / 'image.png')
        response = portal.dataset_preview('1_sample', 'image.png')
        self.assertEqual(response.media_type, 'image/jpeg')
        with Image.open(io.BytesIO(response.body)) as image:
            self.assertEqual(image.size, (180, 120))
        self.assertIn('private', response.headers['cache-control'])

    @unittest.skipIf(Image is None, "Pillow is required for image previews")
    def test_preview_rejects_traversal_symlinks_and_non_images(self):
        (self.dataset / 'secret.txt').write_text('private')
        (self.dataset / 'linked.png').symlink_to(self.root / 'outside.png')
        (self.dataset / 'linked-dir').symlink_to(self.root, target_is_directory=True)
        for path in ['../outside.png', '/tmp/outside.png', 'linked.png', 'linked-dir/outside.png', 'secret.txt']:
            with self.subTest(path=path), self.assertRaises(portal.HTTPException):
                portal.dataset_preview('1_sample', path)

    @unittest.skipIf(Image is None, "Pillow is required for image previews")
    def test_preview_keeps_nested_images_and_rejects_sibling_and_internal_links(self):
        nested = self.dataset / 'nested'
        nested.mkdir()
        image = nested / 'a b.PNG'
        Image.new('RGB', (60, 40), 'white').save(image)
        response = portal.dataset_preview('1_sample', 'nested/a b.PNG')
        with Image.open(io.BytesIO(response.body)) as preview:
            self.assertEqual(preview.size, (60, 40))
        sibling = self.dataset.with_name('1_sample-private')
        sibling.mkdir()
        Image.new('RGB', (60, 40), 'black').save(sibling / 'secret.png')
        (self.dataset / 'internal.png').symlink_to(image)
        (self.dataset / 'escape.png').symlink_to(sibling / 'secret.png')
        (self.dataset / 'linked-dir').symlink_to(sibling, target_is_directory=True)
        for path in ['../1_sample-private/secret.png', 'nested/../../1_sample-private/secret.png',
                     str(sibling / 'secret.png'), 'internal.png', 'escape.png', 'linked-dir/secret.png']:
            with self.subTest(path=path), self.assertRaises(portal.HTTPException) as error:
                portal.dataset_preview('1_sample', path)
            self.assertEqual(error.exception.status_code, 400)
        with self.assertRaises(portal.HTTPException) as error:
            portal._resolve_under_root(self.dataset, sibling / 'secret.png')
        self.assertEqual(error.exception.status_code, 400)

    def test_completion_metadata_survives_a_move_and_is_scoped_to_the_run(self):
        artifact = portal._tp_output_dir / 'run000001.safetensors'
        artifact.write_bytes(b'weights')
        before = portal.trainpilot_logs()
        self.assertEqual(before['artifacts'], [{'name': artifact.name, 'size_bytes': 7}])
        self.assertTrue(before['move_available'])
        with self.assertRaises(portal.HTTPException) as error:
            portal.trainpilot_move_loras(portal.TrainPilotMoveRequest(run_id='older-run'))
        self.assertEqual(error.exception.status_code, 409)
        portal.trainpilot_move_loras(portal.TrainPilotMoveRequest(run_id='run-one'))
        after = portal.trainpilot_logs()
        self.assertTrue(after['moved'])
        self.assertFalse(after['move_available'])
        self.assertEqual(after['artifacts'], before['artifacts'])
        self.assertEqual(after['run']['dataset'], '1_sample')
        self.assertEqual(after['lora_destination'], str(self.root / 'models/loras'))

    def test_failed_run_does_not_offer_artifacts(self):
        (portal._tp_output_dir / 'partial.safetensors').write_bytes(b'partial')
        portal._tp_exit_code = 1
        data = portal.trainpilot_logs()
        self.assertFalse(data['move_available'])
        self.assertEqual(data['artifacts'], [])

    def test_move_conflict_keeps_source_and_existing_model(self):
        source = portal._tp_output_dir / 'run.safetensors'
        source.write_bytes(b'new')
        destination = self.root / 'models/loras/run.safetensors'
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b'existing')
        with self.assertRaises(portal.HTTPException) as error:
            portal.trainpilot_move_loras(portal.TrainPilotMoveRequest(run_id='run-one'))
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(source.read_bytes(), b'new')
        self.assertEqual(destination.read_bytes(), b'existing')
        self.assertFalse(portal.trainpilot_logs()['moved'])
