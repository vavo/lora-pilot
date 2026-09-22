import unittest
import subprocess
import sys
from pathlib import Path
from apps.Portal.services.activity import progress
from apps.Portal.services.training_timing import timing


class TimingTests(unittest.TestCase):
    def test_oversized_log_records_cannot_stall_progress_parsers(self):
        script = '''
from apps.Portal.services.training_timing import timing
from apps.Portal.services.activity import progress
records = [
    'steps: ' + '9' * 131072,
    'steps: ' + '9' * 5000 + '/100 [00:40<02:40]',
    'steps: 20/' + '9' * 5000 + ' [00:40<02:40]',
    'steps: 20' + ' ' * 131072 + '/100 [00:40<02:40]',
    'steps: 20/100 [' + '9' * 5000 + '<02:40]',
    'steps: 20/100 [00:40<' + '9' * 5000 + ']',
    'steps: ' + 'encoding ' * 16000,
    'steps: ' + '\\u0669' * 131072,
]
for record in records:
    result = timing({'status': 'running'}, [record])
    assert result['stage'] == 'Starting trainer', result
    assert result['remaining_seconds'] is None, result
    assert progress([record]) is None
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_progress_length_boundary_preserves_valid_records_and_skips_oversized_ones(self):
        run = dict(status='running')
        record = 'INFO steps: 20%|\x1b[32m####\x1b[0m| 20 / 100 [1:02:03<2:03:04, 1.0s/it]'
        record = ' ' * (1024 - len(record)) + record
        valid = timing(run, [record], 100, clock=lambda:100)
        self.assertEqual(valid['remaining_seconds'], 7384)
        self.assertEqual(progress([record]), 20)
        self.assertEqual(timing(run, [record + ' '])['stage'], 'Starting trainer')
        self.assertIsNone(progress([record + ' ']))
        self.assertEqual(timing(run, [record, 'steps: ' + '9' * 5000], 100, clock=lambda:100), valid)
        self.assertEqual(progress([record, 'steps: ' + '9' * 5000]), 20)
        self.assertEqual(progress(['steps: ٢٠ / ١٠٠']), 20)

    def test_oversized_numeric_fields_are_not_parsed_as_partial_values(self):
        for digits in (13, 400):
            for record in ('steps: ' + '9' * digits + '/100 [00:40<02:40]',
                           'steps: 20/' + '9' * digits + ' [00:40<02:40]'):
                with self.subTest(record=record):
                    self.assertIsNone(progress([record]))
                    self.assertEqual(timing(dict(status='running'), [record])['stage'], 'Starting trainer')
        for record in ('steps: 20/100 [' + '9' * 400 + '<02:40]',
                       'steps: 20/100 [00:40<' + '9' * 400 + ']'):
            self.assertIsNone(timing(dict(status='running'), [record], 100, clock=lambda:100)['remaining_seconds'])

    def test_startup_cache_and_stable_training_estimates(self):
        run = dict(status='running', started_at='1970-01-01T00:01:00+00:00')
        self.assertEqual(timing(run, [], clock=lambda:100)['stage'], 'Starting trainer')
        self.assertEqual(timing(run, ['caching latents'], clock=lambda:100)['stage'], 'Preparing caches')
        lines = ['steps: 20%| 20/100 [00:40<02:40, 0.50it/s]']
        value = timing(run, lines, 100, clock=lambda:100)
        self.assertEqual(value['elapsed_seconds'], 40)
        self.assertEqual(value['remaining_seconds'], 160)
        self.assertIsNone(timing(run, lines, 10, clock=lambda:100)['remaining_seconds'])
        self.assertIsNone(timing(run, ['steps: 1%| 1/100 [00:02<03:18]'], 100, clock=lambda:100)['remaining_seconds'])

    def test_finished_and_queued_runs_never_show_live_estimates(self):
        self.assertIsNone(timing(dict(status='queued'), [])['elapsed_seconds'])
        run = dict(status='succeeded', started_at='1970-01-01T00:01:00+00:00', finished_at='1970-01-01T00:02:00+00:00')
        result = timing(run, ['steps: 99%| 99/100 [00:40<00:01]'], 100, clock=lambda:1000)
        self.assertEqual(result['elapsed_seconds'], 60)
        self.assertIsNone(result['remaining_seconds'])

        del run['finished_at']
        self.assertIsNone(timing(run, [], clock=lambda:1000)['elapsed_seconds'])
