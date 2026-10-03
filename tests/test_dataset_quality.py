import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from apps.Portal.services.dataset_quality import review_dataset


class DatasetQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def image(self, name='photo.png', size=(512, 512)):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', size).save(path)
        return path

    def test_reports_real_problems_without_changing_files(self):
        photo = self.image(size=(200, 600))
        (self.root / 'copy.png').write_bytes(photo.read_bytes())
        (self.root / 'broken.jpg').write_bytes(b'not an image')
        (self.root / 'copy.txt').write_text('')
        (self.root / 'orphan.caption').write_text('robot')
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        report = review_dataset(self.root)
        self.assertTrue(report['complete'])
        self.assertEqual(report['counts'], dict(duplicate=1, empty_caption=1, missing_caption=2,
                                                orphan_caption=1, small=2, unreadable=1))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_nested_captions_match_by_path_and_alternate_extension(self):
        self.image('nested/a.png')
        (self.root / 'nested/a.caption').write_text('orange robot')
        self.assertEqual(review_dataset(self.root)['findings'], [])

    def test_links_are_reported_and_never_followed(self):
        (self.root / 'outside.png').symlink_to('/etc/passwd')
        (self.root / 'outside').symlink_to('/etc', target_is_directory=True)
        report = review_dataset(self.root)
        self.assertEqual(report['images'], 0)
        self.assertEqual(report['counts'], {'unsafe': 2})

    def test_time_limit_is_not_reported_as_clean(self):
        self.image()
        with patch('apps.Portal.services.dataset_quality.time.monotonic', side_effect=[0, 100, 100]):
            self.assertFalse(review_dataset(self.root)['complete'])

    def test_small_threshold_is_short_side(self):
        self.image(size=(1200, 511))
        self.assertEqual(review_dataset(self.root)['counts']['small'], 1)
