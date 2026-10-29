import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from PIL import Image

from apps.Portal.services.dataset_builder import DatasetBuilder, create_router, image_checks, safe_path
from apps.Portal.services.dataset_generation import MODEL_FILES, MODEL_SIZES, reference_graph, variation_graph, shot_plan, validate_graph
from apps.Portal.services.tagpilot_local import parse_review


def photo_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (768, 1024), '#bc9475').save(buffer, 'PNG')
    return buffer.getvalue()


class DatasetBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        router, self.builder = create_router(self.root, self.root / 'models')
        app = FastAPI(); app.include_router(router)
        self.client = TestClient(app); self.addCleanup(self.client.close)
        self.ready = patch.object(self.builder, 'require_ready')
        self.ready.start(); self.addCleanup(self.ready.stop)
        capacity = patch('apps.Portal.services.dataset_builder.shutil.disk_usage', return_value=Mock(free=1024 ** 3))
        capacity.start(); self.addCleanup(capacity.stop)

    def create(self, **extra):
        spec = dict(name='character', trigger='ohwxperson', source='photo', count=4, **extra)
        response = self.client.post('/api/dataset-builder/jobs', data={'spec': json.dumps(spec)},
                                    files={'photo': ('person.jpg', photo_bytes(), 'image/jpeg')})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def prepare_review(self, job):
        job['reference'] = job['references'][0]
        job['phase'], job['status'] = 'variations', 'review'
        job['items'] = shot_plan(4, 'identity', True, False)
        for item in job['items']:
            name = f'image-{item["slot"]}.png'
            (self.builder.directory(job['id']) / name).write_bytes(photo_bytes())
            item.update(file=name, caption='ohwxperson, standing in daylight', accepted=True,
                        attempts=1, review={'identity': 'consistent', 'issues': [], 'caption': 'standing in daylight'})
        self.builder.save(job)
        return job

    def test_photo_requires_explicit_reference_approval(self):
        job = self.create()
        self.assertEqual(job['status'], 'reference_review')
        self.assertIsNone(job['reference'])
        self.assertFalse((self.root / 'datasets').exists())
        self.assertEqual(self.client.get(f'/api/dataset-builder/jobs/{job["id"]}/images/reference-upload.png').status_code, 200)
        with patch.object(self.builder, 'start') as start:
            response = self.client.post(f'/api/dataset-builder/jobs/{job["id"]}/reference', json={'file': job['references'][0]})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(start.call_args.args[0]['items']), 4)
        self.assertEqual(self.client.post(f'/api/dataset-builder/jobs/{job["id"]}/reference', json={'file': '../state.json'}).status_code, 409)

    def test_invalid_upload_and_name_cannot_escape_workspace(self):
        for name in ['../outside', '/tmp/outside', 'bad name']:
            result = self.client.post('/api/dataset-builder/jobs', data={'spec': json.dumps(dict(name=name, trigger='x', source='photo'))},
                                      files={'photo': ('a.png', photo_bytes())})
            self.assertEqual(result.status_code, 422)
        result = self.client.post('/api/dataset-builder/jobs', data={'spec': json.dumps(dict(name='valid', trigger='x', source='photo'))},
                                  files={'photo': ('fake.png', b'not an image')})
        self.assertEqual(result.status_code, 400)

    def test_low_disk_space_blocks_before_creating_job(self):
        with patch('apps.Portal.services.dataset_builder.shutil.disk_usage', return_value=Mock(free=0)):
            response = self.client.post('/api/dataset-builder/jobs',
                data={'spec': json.dumps(dict(name='lowspace', trigger='person', source='photo', count=4))},
                files={'photo': ('a.png', photo_bytes())})
        self.assertEqual(response.status_code, 409)
        self.assertIn('Free space', response.json()['detail'])
        self.assertFalse(self.builder.root.exists())

    def test_finish_publishes_exact_accepted_count_for_tagpilot(self):
        job = self.prepare_review(self.create())
        for item in job['items']:
            item.pop('caption', None)
        job['items'][0]['accepted'] = False; self.builder.save(job)
        url = f'/api/dataset-builder/jobs/{job["id"]}'
        self.assertEqual(self.client.post(url + '/finish').status_code, 409)
        self.assertFalse((self.root / 'datasets/1_character').exists())
        result = self.client.patch(url + '/images/0', json={'accepted': True})
        self.assertEqual(result.status_code, 200, result.text)
        result = self.client.post(url + '/finish')
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['dataset'], '1_character')
        target = self.root / 'datasets/1_character'
        self.assertEqual(len(list(target.glob('*.png'))), 4)
        self.assertEqual(len(list(target.glob('*.txt'))), 0)
        self.assertEqual(json.loads((target / 'generation.json').read_text())['spec']['trigger'], 'ohwxperson')
        self.assertTrue((target / 'generation.json').is_file())
        self.assertEqual(self.client.patch(url + '/images/0', json={'accepted': False, 'caption': 'x'}).status_code, 409)

    def test_publish_preserves_existing_user_dataset(self):
        job = self.prepare_review(self.create())
        target = self.root / 'datasets/1_character'; target.mkdir(parents=True)
        (target / 'user.txt').write_text('keep this')
        self.assertEqual(self.client.post(f'/api/dataset-builder/jobs/{job["id"]}/finish').status_code, 409)
        self.assertEqual((target / 'user.txt').read_text(), 'keep this')

    def test_publication_recovers_after_crash_without_overwriting(self):
        job = self.prepare_review(self.create())
        with patch.object(self.builder, 'mark_saved', side_effect=RuntimeError('restart')):
            with self.assertRaisesRegex(RuntimeError, 'restart'):
                self.builder.finish(job)
        restored = self.builder.read(job['id'])
        self.assertEqual(self.builder.finish(restored)['status'], 'saved')
        self.assertEqual(self.builder.finish(self.builder.read(job['id']))['status'], 'saved')

    def test_publication_recovery_preserves_user_edits(self):
        job = self.prepare_review(self.create())
        with patch.object(self.builder, 'mark_saved', side_effect=RuntimeError('restart')):
            with self.assertRaises(RuntimeError):
                self.builder.finish(job)
        caption = self.root / 'datasets/1_character/001.txt'
        caption.write_text('edited by user')
        self.assertEqual(self.client.post(f'/api/dataset-builder/jobs/{job["id"]}/finish').status_code, 409)
        self.assertEqual(caption.read_text(), 'edited by user')

    def test_symlink_job_and_export_are_rejected(self):
        job = self.prepare_review(self.create())
        outside = self.root / 'outside'; outside.mkdir()
        (self.builder.directory(job['id']) / 'export').symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.client.post(f'/api/dataset-builder/jobs/{job["id"]}/finish').status_code, 400)
        self.assertEqual(list(outside.iterdir()), [])
        with self.assertRaises(HTTPException):
            safe_path(self.root, '..', 'escape')

    def test_restart_marks_job_paused_and_keeps_prompt_id(self):
        job = self.create()
        job.update(status='generating', pending={'file': 'candidate.png', 'prompt_id': 'already-submitted'})
        self.builder.save(job)
        restarted = DatasetBuilder(self.root, self.root / 'models')
        restored = restarted.read(job['id'])
        self.assertEqual(restored['status'], 'paused')
        self.assertEqual(restored['pending']['prompt_id'], 'already-submitted')

    def test_recover_download_does_not_submit_again(self):
        job = self.create()
        filename = job['references'][0]
        with patch.object(self.builder, 'request') as request:
            self.builder.generate(job, {}, filename)
        request.assert_not_called()

    def test_unknown_submission_does_not_spend_again(self):
        job = self.create()
        job['pending'] = {'file': 'candidate.png', 'prompt_id': None}
        with patch.object(self.builder, 'request') as request, self.assertRaisesRegex(RuntimeError, 'unknown'):
            self.builder.generate(job, {}, 'candidate.png')
        request.assert_not_called()

    def test_definite_comfy_rejection_can_be_retried(self):
        job = self.create()
        with patch.object(self.builder, 'request', side_effect=[{}, HTTPException(409, 'rejected')]), \
             self.assertRaises(HTTPException):
            self.builder.generate(job, {}, 'candidate.png')
        self.assertIsNone(self.builder.read(job['id'])['pending'])

    def test_failed_gpu_execution_counts_toward_attempt_limit(self):
        job = self.create()
        job.update(phase='variations', items=shot_plan(4, 'identity', True, False))
        replies = [{}, {'prompt_id': 'submitted'}, {'submitted': {'status': {'status_str': 'error'}}}]
        with patch.object(self.builder, 'request', side_effect=replies), self.assertRaisesRegex(RuntimeError, 'generation failed'):
            self.builder.generate(job, {}, 'image-000-0.png')
        self.assertEqual(job['items'][0]['attempts'], 1)
        self.assertIsNone(job['pending'])

    def test_caption_worker_results_are_gated_and_offline(self):
        job = self.prepare_review(self.create())
        for item in job['items']:
            item['review'] = None
            item['accepted'] = False
        for item in job['items']:
            item.pop('caption', None)
        results = {item['file']: {'identity': 'uncertain', 'issues': ['face partly hidden']}
                   for item in job['items']}
        def worker(*args, **kwargs):
            self.assertEqual(kwargs['env']['HF_HUB_OFFLINE'], '1')
            (self.builder.directory(job['id']) / 'vision-result.json').write_text(json.dumps(results))
            return Mock(poll=Mock(return_value=0), wait=Mock(return_value=0))
        with patch('apps.Portal.services.dataset_builder.subprocess.Popen', side_effect=worker):
            self.builder.review(job)
        self.assertTrue(all(not item['accepted'] for item in job['items']))
        self.assertTrue(all('caption' not in item for item in job['items']))
        self.assertIn('Identity uncertain', ' '.join(job['items'][0]['warnings']))
        self.assertIn('Very similar', ' '.join(job['items'][1]['warnings']))
        self.assertIsNone(self.builder.vision_process)

    def test_incomplete_captioning_never_passes_as_ready(self):
        job = self.prepare_review(self.create())
        for item in job['items']:
            item.update(review=None, accepted=False)
        with patch('apps.Portal.services.dataset_builder.subprocess.Popen', return_value=Mock(poll=Mock(return_value=1), wait=Mock(return_value=1))), \
             self.assertRaisesRegex(RuntimeError, 'did not finish'):
            self.builder.review(job)
        self.assertTrue(all(not item['accepted'] and not item['review'] for item in job['items']))

    def test_shutdown_stops_local_worker_without_interrupting_comfy(self):
        self.builder.vision_process = Mock(poll=Mock(return_value=None))
        with patch.object(self.builder, 'request') as request:
            self.builder.close()
        self.builder.vision_process.terminate.assert_called_once()
        request.assert_not_called()
        self.assertTrue(self.builder.closing.is_set())

    def test_retry_only_requests_selected_slot_and_is_bounded(self):
        job = self.prepare_review(self.create())
        url = f'/api/dataset-builder/jobs/{job["id"]}/images/2/regenerate'
        with patch.object(self.builder, 'start') as start:
            self.assertEqual(self.client.post(url).status_code, 200)
            self.assertEqual(start.call_args.args[0]['retry_slots'], [2])
        job['items'][2]['attempts'] = 3; self.builder.save(job)
        self.assertEqual(self.client.post(url).status_code, 409)

    def test_full_generation_uses_original_reference_and_stops_at_budget(self):
        job = self.create()
        job.update(reference=job['references'][0], phase='variations', items=shot_plan(4, 'identity', True, False))
        calls = []
        def generate(current, graph, filename):
            calls.append(graph)
            (self.builder.directory(current['id']) / filename).write_bytes(photo_bytes())
        def review(current):
            for item in current['items']:
                item.update(review={'identity': 'different'}, caption='ohwxperson, portrait', accepted=False)
        with patch.object(self.builder, 'request', return_value={'subfolder': 'dataset-builder', 'name': 'original.png'}), \
             patch.object(self.builder, 'generate', side_effect=generate), patch.object(self.builder, 'review', side_effect=review):
            self.builder.work(job)
        self.assertEqual(len(calls), 12)
        self.assertTrue(all(graph['4']['inputs']['image'] == 'dataset-builder/original.png' for graph in calls))
        self.assertEqual(job['status'], 'review')
        self.assertTrue(all(item['attempts'] == 3 and not item['accepted'] for item in job['items']))

    def test_local_review_failure_is_not_accepted(self):
        with self.assertRaises(ValueError):
            parse_review('{"identity":"perfect", "issues":[], "caption":"a person"}')
        with self.assertRaises(ValueError):
            parse_review('{"identity":"consistent", "issues":"not a list"}')
        self.assertEqual(parse_review('{"identity":"consistent", "issues":[]}'), {'identity': 'consistent', 'issues': []})
        data = parse_review('```json\n{"identity":"uncertain", "issues":["face hidden"], "caption":"a rear view"}\n```')
        self.assertEqual(data['identity'], 'uncertain')

    def test_native_workflows_and_shot_plan(self):
        graph = variation_graph('original.png', 'turn left', 1, 'test')
        self.assertEqual(graph['6']['inputs']['image1'], ['5', 0])
        self.assertEqual(graph['11']['inputs']['steps'], 40)
        self.assertNotIn('LoraLoaderModelOnly', [n['class_type'] for n in graph.values()])
        with self.assertRaises(HTTPException):
            validate_graph(graph, {})
        plan = shot_plan(24, 'character', True, True)
        self.assertEqual(len(set(x['shot'] for x in plan)), 18)
        self.assertTrue(all('keep the original clothing exactly' in x['prompt'] for x in plan))
        self.assertEqual(reference_graph('portrait', 1, 'test')['1']['class_type'], 'CheckpointLoaderSimple')

    def test_required_models_reuse_canonical_manifest_files(self):
        manifest = Path(__file__).resolve().parents[1] / 'config/models.manifest'
        rows = {line.split('|')[0]: line.split('|') for line in manifest.read_text().splitlines() if line and not line.startswith('#')}
        for name, (folder, filename) in MODEL_FILES.items():
            self.assertEqual(rows[name][2].split(':', 1)[1].split('/')[-1], filename)
            self.assertEqual(rows[name][3], folder)
            self.assertEqual(int(rows[name][5]), MODEL_SIZES[name])
        self.assertEqual(int(rows['sdxl-base'][5]), MODEL_SIZES['sdxl-base'])

    def test_image_checks_find_duplicates(self):
        path = self.root / 'image.png'; path.write_bytes(photo_bytes())
        other = self.root / 'copy.png'; other.write_bytes(photo_bytes())
        self.assertEqual(image_checks(path)[0], image_checks(other)[0])

    def test_missing_dependencies_are_actionable(self):
        with patch.object(self.builder, 'request', side_effect=HTTPException(503, 'Start ComfyUI in Services')):
            result = self.builder.preflight('prompt')
        self.assertFalse(result['ready'])
        self.assertIn('dataset-local-captioner', result['missing'])
        self.assertIn('sdxl-base', result['missing'])
        self.assertIn('Start ComfyUI in Services', result['problems'])
