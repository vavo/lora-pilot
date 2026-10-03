import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from apps.Portal.services.training_performance import recommendation, gpu_snapshot, sample, finish
import test_guided_training


class TrainingPerformanceTests(unittest.TestCase):
    def test_recommendation_requires_successful_matching_measurements(self):
        gpu = dict(name='RTX 4090', total_mib=24564, used_mib=3000)
        evidence = dict(gpu=gpu, samples=50, elapsed_seconds=240, peak_device_mib=19000,
                        settings=dict(train_batch_size=3, network_dim=40, gradient_accumulation_steps=2))
        run = dict(id='a'*32, spec=dict(family='sdxl', profile='regular', output_name='robot'),
                   status='succeeded', performance=evidence)
        result = recommendation('sdxl', 'regular', [run], gpu)
        self.assertTrue(result['measured'])
        self.assertEqual(result['settings']['train_batch_size'], 3)
        for change in [dict(status='failed'), dict(recovery={'mode':'state'}),
                       dict(spec=dict(family='flux1', profile='regular')),
                       dict(performance=dict(evidence, samples=1))]:
            self.assertFalse(recommendation('sdxl', 'regular', [dict(run, **change)], gpu)['measured'])
        self.assertFalse(recommendation('sdxl', 'regular', [run], dict(gpu, total_mib=16000))['measured'])
        with patch('apps.Portal.services.training_performance.build_identity', return_value={'revision':'b'*40}):
            self.assertFalse(recommendation('sdxl', 'regular', [run], gpu)['measured'])

    def test_no_gpu_uses_explicit_unmeasured_starting_point(self):
        result = recommendation('flux1', 'quick_test', [], None)
        self.assertFalse(result['measured'])
        self.assertIsNone(result['evidence'])
        self.assertEqual(result['settings']['train_batch_size'], 1)

    def test_peak_is_sampled_whole_device_memory(self):
        run = {}
        with patch('apps.Portal.services.training_performance.gpu_snapshot', side_effect=[
            dict(name='A40', total_mib=48000, used_mib=1000),
            dict(name='A40', total_mib=48000, used_mib=27000), None]):
            sample(run); sample(run); sample(run)
        self.assertEqual(run['performance']['peak_device_mib'], 27000)
        self.assertEqual(run['performance']['samples'], 2)

    def test_multiple_or_unavailable_gpus_do_not_invent_capacity(self):
        for output in ['A40, 48000, 4000\nA40, 48000, 1000', 'A40, N/A, N/A', '']:
            with patch('subprocess.run', return_value=Mock(returncode=0, stdout=output)):
                self.assertIsNone(gpu_snapshot())

    def test_finish_reads_effective_not_requested_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'effective.toml').write_text('train_batch_size = 2\nnetwork_dim = 32\n')
            run = dict(performance={}, template={'train_batch_size': 1}, spec={'family': 'flux1'}, output_dir=temp,
                       started_at='2026-10-03T00:00:00+00:00', finished_at='2026-10-03T00:01:00+00:00')
            run['performance'] = {'samples': 2}
            finish(run, path)
            self.assertEqual(run['performance']['settings']['train_batch_size'], 2)
            self.assertEqual(run['performance']['elapsed_seconds'], 60)

    def test_sdxl_wrapper_applies_explicit_overrides_before_step_calculation(self):
        script = Path('apps/TrainPilot/trainpilot.sh').read_text()
        section = script.split('      # Guided runs can explicitly override', 1)[1].split('      # Big datasets', 1)[0]
        section = section[section.index('\n'):]
        result = subprocess.run(['bash', '-c', 'set -eu\nbatch=4; ga=1; net_dim=64; net_alpha=32; conv_dim=64; conv_alpha=32\n'
                                 + section + '\nprintf "%s %s %s %s" "$batch" "$ga" "$net_dim" "$conv_dim"'],
                                env=dict(os.environ, TRAINPILOT_OVERRIDE_TRAIN_BATCH_SIZE='1',
                                         TRAINPILOT_OVERRIDE_GRADIENT_ACCUMULATION_STEPS='4', TRAINPILOT_OVERRIDE_NETWORK_DIM='16'),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '1 4 16 16')


class HardwareLaunchTests(unittest.TestCase):
    setUp = test_guided_training.GuidedTrainingTests.setUp

    def test_flux_swap_limit_leaves_required_blocks_resident(self):
        from apps.Portal.services.guided_training import HardwareOverrides
        from pydantic import ValidationError
        self.assertEqual(HardwareOverrides(blocks_to_swap=35).blocks_to_swap, 35)
        with self.assertRaises(ValidationError):
            HardwareOverrides(blocks_to_swap=36)

    def test_flux_batch_size_is_used_by_dataset_and_effective_config(self):
        import tomllib
        kohya = self.root / 'kohya/sd-scripts'; kohya.mkdir(parents=True)
        (kohya / 'flux_train_network.py').touch()
        spec = dict(self.spec, hardware=dict(train_batch_size=2, network_dim=24, blocks_to_swap=0))
        run = self.recipe.prepare(spec, self.rid, self.directory); run['id'] = self.rid
        with patch.dict(os.environ, KOHYA_ROOT=str(kohya.parent)), patch('subprocess.Popen'):
            self.recipe.launch(run, None)
        config = tomllib.loads((self.directory / 'effective.toml').read_text())
        dataset = tomllib.loads((self.directory / 'dataset.toml').read_text())
        self.assertEqual(config['train_batch_size'], 2)
        self.assertEqual(config['network_dim'], 24)
        self.assertEqual(config['blocks_to_swap'], 0)
        self.assertEqual(dataset['datasets'][0]['batch_size'], 2)
