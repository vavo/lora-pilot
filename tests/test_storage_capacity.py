import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.Portal.services.storage_capacity import shared_workspace, workspace_capacity


class StorageCapacityTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.disk = dict(total=2235 * 1024**4, used=1553 * 1024**4, free=682 * 1024**4, pct=69, alert=False)

    def mount(self, kind='fuse', source='mfs#euro-3.runpod.net:9421', root='/'):
        return patch('pathlib.Path.read_text', return_value=f'1 0 0:1 / / rw - overlay overlay rw\n2 1 0:2 {root} /workspace rw - {kind} {source} rw\n')

    def test_shared_cluster_totals_are_never_workspace_capacity(self):
        with self.mount():
            result = workspace_capacity('/workspace', self.disk, 52 * 1024**3)
        self.assertIsNone(result['total'])
        self.assertIsNone(result['free'])
        self.assertIsNone(result['pct'])
        self.assertEqual(result['used'], 52 * 1024**3)
        self.assertFalse(result['alert'])

    def test_configured_capacity_uses_workspace_files_not_cluster_usage(self):
        with self.mount(), patch.dict(os.environ, WORKSPACE_STORAGE_CAPACITY_GB='100'):
            result = workspace_capacity('/workspace', self.disk, 52 * 1024**3)
        self.assertEqual(result['total'], 100 * 1024**3)
        self.assertEqual(result['free'], 48 * 1024**3)
        self.assertEqual(result['pct'], 52)
        self.assertTrue(result['estimated'])

    def test_missing_usage_does_not_claim_empty_volume(self):
        with patch.dict(os.environ, WORKSPACE_STORAGE_CAPACITY_GB='100'):
            result = workspace_capacity('/workspace', self.disk, None)
        self.assertEqual(result['total'], 100 * 1024**3)
        self.assertIsNone(result['free'])
        self.assertIsNone(result['used'])
        self.assertIsNone(result['pct'])

    def test_over_capacity_is_clamped_and_alerts(self):
        with patch.dict(os.environ, WORKSPACE_STORAGE_CAPACITY_GB='10'):
            result = workspace_capacity('/workspace', self.disk, 52 * 1024**3)
        self.assertEqual((result['free'], result['pct'], result['alert']), (0, 100, True))

    def test_invalid_configuration_cannot_fall_back_to_cluster_capacity(self):
        for value in ['no', 'nan', 'inf', '-1', '0', '1e308']:
            with self.subTest(value=value), patch.dict(os.environ, WORKSPACE_STORAGE_CAPACITY_GB=value):
                self.assertIsNone(workspace_capacity('/workspace', self.disk, None)['total'])

    def test_dedicated_filesystem_keeps_its_capacity(self):
        with self.mount('ext4', '/dev/sda'):
            result = workspace_capacity('/workspace', self.disk, 52)
        self.assertEqual(result['total'], self.disk['total'])
        self.assertEqual(result['used'], self.disk['used'])
        self.assertFalse(result['estimated'])

    def test_runpod_host_bind_mount_is_not_an_allocation(self):
        with self.mount('ext4', '/dev/sda', '/pods/example'), patch.dict(os.environ, RUNPOD_POD_ID='example'):
            self.assertTrue(shared_workspace('/workspace'))

    def test_nested_mount_wins_and_paths_respect_directory_boundaries(self):
        mounts = '1 0 0:1 / / rw - overlay overlay rw\n2 1 0:2 / /workspace rw - nfs host:/volume rw\n3 2 0:3 / /workspace/local rw - ext4 /dev/sda rw'
        with patch('pathlib.Path.read_text', return_value=mounts):
            self.assertTrue(shared_workspace('/workspace/models'))
            self.assertFalse(shared_workspace('/workspace/local'))
            self.assertFalse(shared_workspace('/workspace-other'))

    def test_unreadable_mounts_on_runpod_do_not_expose_host_capacity(self):
        with patch('pathlib.Path.read_text', side_effect=OSError), patch.dict(os.environ, RUNPOD_POD_ID='example'):
            self.assertTrue(shared_workspace('/workspace'))

    def test_telemetry_serializes_unknown_capacity_without_changing_container_disk(self):
        from apps.Portal import app as portal
        from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as folder, patch.object(portal, 'WORKSPACE_ROOT', Path(folder)), \
                patch.object(portal, 'disk_usage', side_effect=lambda path: portal.DiskUsage(mount=path, **self.disk)), \
                patch.object(portal, 'workspace_data_used_bytes', return_value=52 * 1024**3), \
                patch.object(portal, 'get_gpus', return_value=[]), \
                patch('apps.Portal.services.storage_capacity.shared_workspace', return_value=True):
            response = TestClient(portal.app).get('/api/telemetry')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['disks'][0]['total'], self.disk['total'])
        self.assertIsNone(data['disks'][1]['total'])
        self.assertEqual(data['disks'][1]['used'], 52 * 1024**3)

    def test_failed_first_usage_measurement_is_unknown(self):
        from apps.Portal import app as portal
        with patch.object(portal, '_WS_DU_CACHE', dict(ts=0, val=None)), \
                patch.object(portal, '_du_bytes', side_effect=RuntimeError('timeout')):
            self.assertIsNone(portal.workspace_data_used_bytes('/workspace'))
