import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from apps.Portal import app as portal


class TensorBoardStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = {'WORKSPACE_ROOT': self.root, 'TENSORBOARD_ROOT': self.root / 'logs/tensorboard',
                      'DIFFPIPE_LOGDIR': self.root / 'logs/diffpipe',
                      'TRAINPILOT_TENSORBOARD_PATH': self.root / 'logs/trainpilot',
                      'KOHYA_TENSORBOARD_PATH': self.root / 'outputs',
                      'AI_TOOLKIT_TENSORBOARD_PATH': self.root / 'outputs/ai-toolkit'}
        for key, value in self.paths.items():
            value.mkdir(parents=True, exist_ok=True)
            p = patch.object(portal, key, value)
            p.start(); self.addCleanup(p.stop)
        self.state = patch.object(portal, 'supervisor_status', return_value=SimpleNamespace(state='STOPPED'))
        self.state.start(); self.addCleanup(self.state.stop)
        p = patch.dict(os.environ, {'DIFFPIPE_CONFIG': ''})
        p.start(); self.addCleanup(p.stop)

    def event(self, relative, age=0):
        path = self.root / relative / 'events.out.tfevents.test'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'event fixture')
        os.utime(path, (time.time()-age, time.time()-age))
        return path

    def status(self, loaded=(), reachable=True):
        response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: list(loaded))
        with patch.object(portal.httpx, 'get', return_value=response,
                          side_effect=None if reachable else portal.httpx.ConnectError('offline')):
            return portal.tensorboard_status()

    def test_stopped_server_and_old_logs_are_separate(self):
        self.event('logs/trainpilot/old', age=3600)
        result = self.status(reachable=False)
        self.assertTrue(result['server']['can_start'])
        run = result['sources']['trainpilot']['runs'][0]
        self.assertFalse(run['recent'])
        self.assertFalse(run['loaded'])
        self.assertTrue(result['sources']['trainpilot']['ready'])

    def test_source_ownership_and_registered_diffpipe_output(self):
        self.event('outputs/ai-toolkit/aitk')
        event = self.event('outputs/custom-diffpipe/run')
        (self.paths['TENSORBOARD_ROOT'] / 'diffpipe-run-abc').symlink_to(event.parent.parent)
        self.event('outputs/kohya-run')
        result = self.status(['ai-toolkit/aitk', 'diffpipe-run-abc/run', 'kohya/kohya-run'])
        for source in ['ai-toolkit', 'diffpipe', 'kohya']:
            runs = result['sources'][source]['runs']
            self.assertEqual(len(runs), 1, source)
            self.assertTrue(runs[0]['loaded'])

    def test_no_runs_and_pending_server_load(self):
        result = self.status()
        self.assertFalse(result['sources']['trainpilot']['ready'])
        self.event('logs/trainpilot/new')
        result = self.status()
        self.assertTrue(result['sources']['trainpilot']['runs'][0]['recent'])
        self.assertFalse(result['sources']['trainpilot']['runs'][0]['loaded'])

    def test_start_does_not_launch_configured_training_or_restart_running_service(self):
        with patch.object(portal, '_run_supervisorctl') as start:
            with patch.dict(os.environ, {'DIFFPIPE_CONFIG': 'train.toml'}):
                with self.assertRaises(portal.HTTPException): portal.start_tensorboard()
            start.assert_not_called()
            with patch.object(portal, 'supervisor_status', return_value=SimpleNamespace(state='RUNNING')):
                with self.assertRaises(portal.HTTPException): portal.start_tensorboard()
            start.assert_not_called()
            self.assertEqual(portal.start_tensorboard()['status'], 'starting')
            start.assert_called_once_with('start', 'diffpipe')
