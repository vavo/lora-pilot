import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from fastapi import HTTPException
from apps.Portal.services.training_runs import TrainingRuns


class TrainingRunsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'history'
        self.conflicts = Mock(return_value=[])
        self.proc = Mock(pid=99999999)
        self.proc.poll.return_value = None
        self.launch = Mock(return_value=self.proc)
        self.prepare = lambda spec, rid, directory: {'spec': spec, 'config': 'snapshot'}
        self.queue = self.make_queue()
        self.queue.start(background=False)

    def make_queue(self):
        queue = TrainingRuns(self.root, self.prepare, self.launch, self.conflicts)
        self.addCleanup(queue.close)
        return queue

    def submit(self, name='example'):
        return self.queue.submit({'output_name': name})

    def test_runs_are_serial_and_failures_do_not_discard_the_next_run(self):
        first, second = self.submit('one'), self.submit('two')
        self.queue.tick()
        self.assertEqual(self.queue.get(first['id'])['status'], 'running')
        self.queue.tick()
        self.assertEqual(self.launch.call_count, 1)
        self.proc.poll.return_value = 1
        self.queue.tick()
        self.assertEqual(self.queue.get(first['id'])['status'], 'failed')
        self.assertEqual(self.queue.get(second['id'])['status'], 'running')
        self.assertEqual(self.launch.call_count, 2)

    def test_conflicts_block_launch_then_recheck_before_dispatch(self):
        run = self.submit()
        self.conflicts.return_value = ['Other GPU process']
        self.queue.tick()
        self.launch.assert_not_called()
        self.assertEqual(self.queue.get(run['id'])['status'], 'queued')
        self.conflicts.return_value = []
        self.queue.tick()
        self.launch.assert_called_once()

    def test_restart_marks_active_interrupted_and_pauses_pending(self):
        active, pending = self.submit(), self.submit('pending')
        self.queue.tick()
        self.queue.close()
        restarted = self.make_queue()
        restarted.start(background=False)
        self.assertEqual(restarted.get(active['id'])['status'], 'interrupted')
        self.assertEqual(restarted.get(pending['id'])['status'], 'queued')
        self.assertTrue(restarted.paused)
        restarted.tick()
        self.assertEqual(self.launch.call_count, 1)
        restarted.set_paused(False)
        restarted.tick()
        self.assertEqual(self.launch.call_count, 2)

    def test_completed_history_and_logs_survive_restart(self):
        run = self.submit()
        self.queue.tick()
        (self.queue.directory(run['id']) / 'run.log').write_text('step 1\rstep 2\n')
        self.proc.poll.return_value = 0
        self.queue.tick()
        self.queue.close()
        restarted = self.make_queue()
        restarted.start(background=False)
        self.assertEqual(restarted.get(run['id'])['status'], 'succeeded')
        self.assertEqual(restarted.logs(run['id']), ['step 1', 'step 2'])
        self.assertEqual(restarted.get(run['id'])['config'], 'snapshot')

    def test_cancel_and_pause_do_not_launch_or_stop_unrelated_work(self):
        run = self.submit()
        self.queue.set_paused(True)
        self.queue.tick()
        self.launch.assert_not_called()
        self.queue.cancel(run['id'])
        self.queue.set_paused(False)
        self.queue.tick()
        self.launch.assert_not_called()
        self.assertEqual(self.queue.get(run['id'])['status'], 'cancelled')

    def test_second_worker_is_rejected(self):
        second = self.make_queue()
        with self.assertRaises(HTTPException) as error:
            second.start(background=False)
        self.assertEqual(error.exception.status_code, 503)

    def test_invalid_ids_and_external_symlinks_are_rejected(self):
        for rid in ['../outside', '/tmp/test', 'not-a-run']:
            with self.assertRaises(HTTPException):
                self.queue.get(rid)
        rid = 'a' * 32
        self.queue.directory(rid).symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaises(HTTPException):
            self.queue.get(rid)

    def test_launch_failure_is_saved(self):
        run = self.submit()
        self.launch.side_effect = OSError('missing executable')
        self.queue.tick()
        saved = self.queue.get(run['id'])
        self.assertEqual(saved['status'], 'failed')
        self.assertIn('missing executable', saved['error'])

    def test_real_process_writes_durable_logs_and_can_be_stopped(self):
        def launch(run, stream):
            return subprocess.Popen([sys.executable, '-u', '-c',
                                     'import time; print("started"); time.sleep(60)'],
                                    stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        self.queue.launch = launch
        run = self.submit()
        self.queue.tick()
        proc = self.queue.proc
        self.addCleanup(lambda: proc.poll() is None and self.queue._terminate(proc))
        self.queue.cancel(run['id'])
        self.queue.tick()
        self.assertEqual(self.queue.get(run['id'])['status'], 'stopped')
        self.assertIsNotNone(proc.poll())


if __name__ == '__main__':
    unittest.main()
