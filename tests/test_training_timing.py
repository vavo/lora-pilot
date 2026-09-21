import unittest
from apps.Portal.services.training_timing import timing


class TimingTests(unittest.TestCase):
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
