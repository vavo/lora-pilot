import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from PIL import Image

from apps.Portal.services.dataset_builder import DatasetBuilder, create_router, image_checks, safe_path
from apps.Portal.services.dataset_generation import MODEL_FILES, MODEL_SIZES, REFERENCE_MODELS, reference_graph, variation_graph, shot_plan, validate_graph
from apps.Portal.services.tagpilot_local import parse_review


def photo_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (768, 1024), '#bc9475').save(buffer, 'PNG')
    return buffer.getvalue()


class DatasetBuilderTests(unittest.TestCase):
    def test_plan_matches_the_existing_recipe_without_creating_a_job(self):
        for count in (4, 15, 30, 50, 100):
            response = self.client.get('/api/dataset-builder/plan', params={'count': count})
            self.assertEqual(response.status_code, 200)
            plan = response.json()
            self.assertEqual(sum(plan['framing'].values()), count)
            self.assertEqual(sum(plan['angles'].values()), count)
            for shot in shot_plan(count, 'identity', True, False):
                frame, angle = shot['shot'].split(', ', 1)
                self.assertIn(frame, plan['framing'])
                self.assertIn(angle, plan['angles'])
        fixed = self.client.get('/api/dataset-builder/plan?goal=character&vary_clothes=true&vary_hair=true').json()
        self.assertFalse(fixed['vary_clothes'])
        self.assertFalse(fixed['vary_hair'])
        self.assertFalse((self.root / 'config' / 'dataset-builder').exists())
        for query in ('count=3', 'count=101', 'goal=unsupported'):
            self.assertEqual(self.client.get('/api/dataset-builder/plan?' + query).status_code, 422)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.downloads = Mock()
        router, self.builder = create_router(self.root, self.root / 'models', downloads=self.downloads)
        self.missing = patch.object(self.builder, 'missing_models', return_value=[])
        self.missing.start(); self.addCleanup(self.missing.stop)
        app = FastAPI(); app.include_router(router)
        self.client = TestClient(app); self.addCleanup(self.client.close)
        self.ready = patch.object(self.builder, 'require_ready')
        self.ready.start(); self.addCleanup(self.ready.stop)
        capacity = patch('apps.Portal.services.dataset_builder.shutil.disk_usage', return_value=Mock(free=64 * 1024 ** 3))
        capacity.start(); self.addCleanup(capacity.stop)

    def create(self, **extra):
        spec = dict(name='character', trigger='ohwxperson', source='photo', count=4, **extra)
        response = self.client.post('/api/dataset-builder/jobs', data={'spec': json.dumps(spec)},
                                    files={'photo': ('person.jpg', photo_bytes(), 'image/jpeg')})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def prepare_review(self, job):
        job['reference'] = job['references'][0]
        job['trial_approved'] = True
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

    def test_setup_failure_resumes_uploaded_photo_without_generating_candidates(self):
        self.builder.missing_models.return_value = ['anima-vae']
        self.downloads.start.side_effect = [{'state': 'error'}, {'state': 'queued'}]
        self.downloads.status.return_value = {'state': 'done'}
        with patch.object(self.builder, 'generate') as generate:
            job = self.create()
            self.builder.thread.join(3)
            failed = self.builder.read(job['id'])
            self.assertEqual((failed['phase'], failed['status']), ('setup', 'failed'))
            self.assertNotIn('anima-vae', failed['message'])
            result = self.client.post(f'/api/dataset-builder/jobs/{job["id"]}/resume')
            self.assertEqual(result.status_code, 200, result.text)
            self.builder.thread.join(3)
            done = self.builder.read(job['id'])
            self.assertEqual(done['status'], 'reference_review')
            self.assertEqual(done['references'], ['reference-upload.png'])
            generate.assert_not_called()

    def test_prompt_setup_continues_into_reference_generation(self):
        self.builder.missing_models.return_value = ['anima-vae']
        self.downloads.start.return_value = {'state': 'done'}
        with patch.object(self.builder, 'generate') as generate:
            response = self.client.post('/api/dataset-builder/jobs', data={'spec': json.dumps(
                dict(name='portrait', trigger='ohwx', source='prompt', count=100, prompt='An orange robot'))})
            self.assertEqual(response.status_code, 200, response.text)
            self.builder.thread.join(3)
            self.downloads.start.assert_called_once_with('anima-vae', 'anima-vae')
            self.assertEqual(self.builder.read(response.json()['id'])['status'], 'reference_review')
            self.assertEqual(generate.call_count, 4)

    def test_invalid_upload_and_name_cannot_escape_workspace(self):
        for name in ['../outside', '/tmp/outside', 'bad name']:
            result = self.client.post('/api/dataset-builder/jobs', data={'spec': json.dumps(dict(name=name, trigger='x', source='photo'))},
                                      files={'photo': ('a.png', photo_bytes())})
            self.assertEqual(result.status_code, 422)
        result = self.client.post('/api/dataset-builder/jobs', data={'spec': json.dumps(dict(name='valid', trigger='x', source='photo'))},
                                  files={'photo': ('fake.png', b'not an image')})
        self.assertEqual(result.status_code, 400)

    def test_first_download_checks_storage_before_starting(self):
        self.builder.missing_models.return_value = ['dataset-qwen-edit']
        with patch('apps.Portal.services.dataset_builder.shutil.disk_usage', return_value=Mock(free=5 * 1024 ** 3)):
            response = self.client.post('/api/dataset-builder/jobs', data={'spec': json.dumps(
                dict(name='test', trigger='ohwx', prompt='An orange robot'))})
        self.assertEqual(response.status_code, 409)
        self.assertIn('model download', response.json()['detail'])
        self.downloads.start.assert_not_called()

    def test_low_disk_space_blocks_before_creating_job(self):
        with patch('apps.Portal.services.dataset_builder.shutil.disk_usage', return_value=Mock(free=0)):
            response = self.client.post('/api/dataset-builder/jobs',
                data={'spec': json.dumps(dict(name='lowspace', trigger='person', source='photo', count=4))},
                files={'photo': ('a.png', photo_bytes())})
        self.assertEqual(response.status_code, 409)
        self.assertIn('Free space', response.json()['detail'])
        self.assertFalse(self.builder.root.exists())

    def test_finish_publishes_only_kept_images_for_tagpilot(self):
        job = self.prepare_review(self.create())
        for item in job['items']:
            item.pop('caption', None)
        job['items'][0]['accepted'] = False; self.builder.save(job)
        url = f'/api/dataset-builder/jobs/{job["id"]}'
        result = self.client.post(url + '/finish')
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['dataset'], '1_character')
        target = self.root / 'datasets/1_character'
        self.assertEqual(len(list(target.glob('*.png'))), 3)
        self.assertFalse((target / '001.png').exists())
        self.assertEqual(result.json()['exported_count'], 3)
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
        restarted = DatasetBuilder(self.root, self.root / 'models', downloads=self.downloads)
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
            item.update(review=None, accepted=False, caption='')
        with patch('apps.Portal.services.dataset_builder.subprocess.Popen', return_value=Mock(poll=Mock(return_value=1), wait=Mock(return_value=1))):
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
            self.assertEqual(start.call_args.args[0]['regenerate_slots'], [2])
            self.assertFalse(start.call_args.kwargs['fill_missing'])
        job['items'][2]['attempts'] = 3; self.builder.save(job)
        self.assertEqual(self.client.post(url).status_code, 409)

    def test_trial_uses_original_reference_and_does_not_retry_rejections(self):
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
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(graph['4']['inputs']['image'] == 'dataset-builder/original.png' for graph in calls))
        self.assertEqual(job['status'], 'trial_review')
        self.assertEqual([item['attempts'] for item in job['items']], [1, 1, 1, 0])

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
        self.assertEqual(graph['4']['inputs']['image'], 'original.png')
        self.assertEqual(graph['5']['inputs']['image'], ['4', 0])
        self.assertEqual(graph['6']['inputs']['image1'], ['5', 0])
        self.assertEqual(graph['7']['inputs']['image1'], ['5', 0])
        self.assertEqual(graph['10']['inputs']['pixels'], ['5', 0])
        self.assertEqual(graph['11']['inputs']['latent_image'], ['10', 0])
        self.assertEqual(graph['11']['inputs']['steps'], 40)
        self.assertNotIn('LoraLoaderModelOnly', [n['class_type'] for n in graph.values()])
        with self.assertRaises(HTTPException):
            validate_graph(graph, {})
        plan = shot_plan(24, 'character', True, True)
        self.assertEqual(len(set(x['shot'] for x in plan)), 18)
        self.assertTrue(all('keep the original clothing exactly' in x['prompt'] for x in plan))
        self.assertEqual(reference_graph('portrait', 1, 'test')['1']['class_type'], 'CheckpointLoaderSimple')

    def test_nonhuman_recipe_and_reference_styles(self):
        plan = shot_plan(15, 'identity', True, True, 'character')
        for item in plan:
            for human in ('skin', 'hair', 'shirt', 'smile', 'clothing'):
                self.assertNotIn(human, item['prompt'])
            self.assertIn('exact same non-human character', item['prompt'])
        self.assertEqual(len({x['shot'].split(', ')[1] for x in plan[:3]}), 3)
        photo = reference_graph('a robot', 1, 'test')
        illustration = reference_graph('a robot', 1, 'test', 'illustration')
        self.assertIn('Photorealistic photograph', photo['2']['inputs']['text'])
        self.assertIn('cartoon', photo['3']['inputs']['text'])
        self.assertNotIn('Photorealistic', illustration['2']['inputs']['text'])
        self.assertNotIn('illustration', illustration['3']['inputs']['text'])
        plan = self.client.get('/api/dataset-builder/plan?subject=character').json()
        self.assertFalse(plan['vary_clothes'])

    def test_trial_gate_survives_resume_and_approval_keeps_trial_files(self):
        job = self.create()
        url = f'/api/dataset-builder/jobs/{job["id"]}'
        with patch.object(self.builder, 'start'):
            job = self.client.post(url + '/reference', json={'file': job['references'][0]}).json()
        calls = []
        def generate(current, graph, filename):
            calls.append(filename)
            (self.builder.directory(current['id']) / filename).write_bytes(photo_bytes())
        with patch.object(self.builder, 'request', return_value={'name': 'original.png'}), \
             patch.object(self.builder, 'generate', side_effect=generate), patch.object(self.builder, 'review'):
            self.builder.work(job)
            self.assertEqual(len(calls), 3)
            self.assertEqual(job['status'], 'trial_review')
            self.assertEqual(self.client.post(url + '/approve-trial').status_code, 409)
            self.assertEqual(self.client.post(url + '/resume').status_code, 200)
            self.builder.thread.join(3)
            self.assertEqual(len(calls), 3)
            for slot in range(3):
                response = self.client.patch(url + f'/images/{slot}', json={'accepted': True, 'confirm_unchecked': True})
                self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(self.client.post(url + '/approve-trial').status_code, 200)
            self.builder.thread.join(3)
        finished = self.builder.read(job['id'])
        self.assertTrue(finished['trial_approved'])
        self.assertEqual(len(calls), 4)
        self.assertEqual([x['attempts'] for x in finished['items']], [1, 1, 1, 1])

    def test_unchecked_image_can_be_kept_directly_and_exported_alone(self):
        job = self.prepare_review(self.create())
        for item in job['items']:
            item.update(review=None, accepted=False, caption='')
        self.builder.save(job)
        url = f'/api/dataset-builder/jobs/{job["id"]}'
        self.assertEqual(self.client.post(url + '/finish').status_code, 409)
        self.assertEqual(self.client.patch(url + '/images/0', json={'accepted': True,
                                                                   'file': 'stale.png'}).status_code, 409)
        self.assertEqual(self.client.patch(url + '/images/0', json={'accepted': True}).status_code, 200)
        result = self.client.post(url + '/finish')
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['exported_count'], 1)
        self.assertEqual(len(list((self.root / 'datasets/1_character').glob('*.png'))), 1)
        self.assertEqual(len(list((self.root / 'datasets/1_character').glob('*.txt'))), 0)

    def test_flagged_image_can_be_kept_without_losing_specific_warnings(self):
        job = self.prepare_review(self.create())
        warning = 'Possibly blurry or low-detail image; inspect it before keeping.'
        job['items'][0].update(accepted=False, warnings=[warning])
        self.builder.save(job)
        response = self.client.patch(f'/api/dataset-builder/jobs/{job["id"]}/images/0',
                                     json={'accepted': True, 'file': 'image-0.png'})
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()['items'][0]
        self.assertTrue(item['accepted'])
        self.assertTrue(item['user_reviewed'])
        self.assertEqual(item['warnings'], [warning])

    def test_review_cannot_overwrite_a_manual_exclusion(self):
        job = self.prepare_review(self.create())
        item = job['items'][0]; item.update(review=None, accepted=False)
        def worker(*args, **kwargs):
            item.update(user_reviewed=True, accepted=False)
            (self.builder.directory(job['id']) / 'vision-result.json').write_text(
                json.dumps({item['file']: {'identity': 'consistent', 'issues': []}}))
            return Mock(poll=Mock(return_value=0), wait=Mock(return_value=0))
        with patch('apps.Portal.services.dataset_builder.subprocess.Popen', side_effect=worker):
            self.builder.review(job)
        self.assertFalse(item['accepted'])
        self.assertTrue(item['user_reviewed'])

    def test_interrupted_save_and_stale_selection_can_be_retried(self):
        job = self.prepare_review(self.create())
        job.update(status='generating', finish_requested=True, finish_slots=[0], busy_slot=1)
        self.builder.save(job)
        recovered = self.builder.read(job['id'])
        self.assertEqual(recovered['status'], 'paused')
        self.assertNotIn('finish_requested', recovered)
        self.assertNotIn('busy_slot', recovered)
        self.assertEqual(self.builder.public(recovered)['status'], 'paused')
        recovered.update(status='failed', finish_slots=[0])
        for item in recovered['items']:
            item['accepted'] = item['slot'] == 2
        self.builder.save(recovered)
        result = self.client.post(f'/api/dataset-builder/jobs/{job["id"]}/finish')
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['exported_slots'], [2])

    def test_active_review_and_regeneration_share_one_worker(self):
        job = self.prepare_review(self.create())
        job['items'][1].update(file=None, review=None, accepted=False)
        entered, release = threading.Event(), threading.Event()
        calls = []
        def generate(current, graph, filename):
            calls.append(filename)
            if len(calls) == 1:
                entered.set()
                self.assertTrue(release.wait(5))
            (self.builder.directory(current['id']) / filename).write_bytes(photo_bytes())
        url = f'/api/dataset-builder/jobs/{job["id"]}'
        with patch.object(self.builder, 'request', return_value={'name': 'original.png'}), \
             patch.object(self.builder, 'generate', side_effect=generate), patch.object(self.builder, 'review'):
            self.builder.start(job)
            try:
                self.assertTrue(entered.wait(3))
                response = self.client.patch(url + '/images/0', json={'accepted': False})
                self.assertEqual(response.status_code, 200, response.text)
                response = self.client.post(url + '/images/2/regenerate', json={'file': 'image-2.png'})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['regenerate_slots'], [2])
                self.assertEqual(self.client.post(url + '/images/2/regenerate').status_code, 409)
            finally:
                release.set()
                self.builder.thread.join(3)
        restored = self.builder.read(job['id'])
        self.assertEqual(len(calls), 2)
        self.assertFalse(restored['items'][0]['accepted'])
        self.assertTrue(restored['items'][0]['user_reviewed'])
        self.assertEqual(restored['regenerate_slots'], [])
        self.assertEqual(restored['items'][2]['attempts'], 2)

    def test_stop_and_save_freezes_selected_subset(self):
        job = self.prepare_review(self.create())
        job['items'][1].update(file=None, review=None, accepted=False)
        job['items'][2]['accepted'] = False
        entered, release = threading.Event(), threading.Event()
        def generate(current, graph, filename):
            entered.set()
            self.assertTrue(release.wait(5))
            (self.builder.directory(current['id']) / filename).write_bytes(photo_bytes())
        url = f'/api/dataset-builder/jobs/{job["id"]}'
        with patch.object(self.builder, 'request', return_value={'name': 'original.png'}), \
             patch.object(self.builder, 'generate', side_effect=generate):
            self.builder.start(job)
            try:
                self.assertTrue(entered.wait(3))
                response = self.client.post(url + '/finish')
                self.assertEqual(response.status_code, 200, response.text)
                self.assertTrue(response.json()['finish_requested'])
                self.assertEqual(self.client.patch(url + '/images/0', json={'accepted': False}).status_code, 409)
            finally:
                release.set()
                self.builder.thread.join(3)
        saved = self.builder.read(job['id'])
        self.assertEqual(saved['status'], 'saved', saved['message'])
        self.assertEqual(saved['exported_slots'], [0, 3])
        self.assertEqual(len(list((self.root / 'datasets/1_character').glob('*.png'))), 2)

    def test_keeping_last_image_cancels_failed_queued_regeneration(self):
        job = self.prepare_review(self.create())
        job.update(status='failed', regenerate_slots=[0])
        job['items'][0].update(attempts=3, accepted=False)
        self.builder.save(job)
        url = f'/api/dataset-builder/jobs/{job["id"]}'
        response = self.client.patch(url + '/images/0', json={'accepted': True, 'file':'image-0.png'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['regenerate_slots'], [])
        self.assertTrue(response.json()['items'][0]['accepted'])
        self.assertEqual(self.client.post(url + '/images/0/regenerate').status_code, 409)

    def test_finish_saves_the_client_selection_not_later_autoaccepted_images(self):
        job = self.prepare_review(self.create())
        url = f'/api/dataset-builder/jobs/{job["id"]}/finish'
        self.assertEqual(self.client.post(url, json={'files':['stale.png']}).status_code, 409)
        self.assertEqual(self.client.post(url, json={'files':[]}).status_code, 409)
        result = self.client.post(url, json={'files':['image-2.png']})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['exported_slots'], [2])
        self.assertEqual(len(list((self.root / 'datasets/1_character').glob('*.png'))), 1)

    def test_required_models_reuse_canonical_manifest_files(self):
        manifest = Path(__file__).resolve().parents[1] / 'config/models.manifest'
        rows = {line.split('|')[0]: line.split('|') for line in manifest.read_text().splitlines() if line and not line.startswith('#')}
        for name, (folder, filename) in MODEL_FILES.items():
            self.assertEqual(rows[name][2].split(':', 1)[1].split('/')[-1], filename)
            self.assertEqual(rows[name][3], folder)
            self.assertEqual(int(rows[name][5]), MODEL_SIZES[name])
        for name, filename in REFERENCE_MODELS.values():
            self.assertEqual(rows[name][2].split(':', 1)[1], filename)
            self.assertEqual(rows[name][3], 'checkpoints')
        for name in ('sdxl-base', 'realvisxl-v5', 'dataset-local-captioner'):
            self.assertEqual(int(rows[name][5]), MODEL_SIZES[name])

    def test_reference_settings_are_style_specific(self):
        for style, model, width, height, sampler, scheduler in (
            ('photo', 'RealVisXL_V5.0_fp16.safetensors', 896, 1152, 'dpmpp_sde', 'karras'),
            ('illustration', 'sd_xl_base_1.0.safetensors', 768, 1024, 'dpmpp_2m', 'normal'),
        ):
            with self.subTest(style=style):
                graph = reference_graph('a robot', 42, 'reference', style)
                self.assertEqual(graph['1']['inputs']['ckpt_name'], model)
                self.assertEqual(graph['4']['inputs'], dict(width=width, height=height, batch_size=1))
                self.assertEqual(graph['5']['inputs'], dict(model=['1', 0], positive=['2', 0],
                    negative=['3', 0], latent_image=['4', 0], seed=42, steps=30, cfg=7.0,
                    sampler_name=sampler, scheduler=scheduler, denoise=1.0))

    def test_style_checkpoint_download_and_reuse(self):
        self.missing.stop()
        # Small stand-ins exercise the real file-size checks without downloading weights.
        with patch.dict(MODEL_SIZES, {name: 10 for name in MODEL_SIZES}), \
             patch('apps.Portal.services.dataset_builder.model_ready', return_value=True):
            for folder, filename in MODEL_FILES.values():
                path = self.builder.models / folder / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'0' * 10)
            for style, (name, filename) in REFERENCE_MODELS.items():
                with self.subTest(style=style):
                    self.assertEqual(self.builder.missing_models('prompt', style), [name])
                    self.assertEqual(self.builder.missing_models('photo', style), [])
                    path = self.builder.models / 'checkpoints' / filename
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'partial')
                    self.assertEqual(self.builder.missing_models('prompt', style), [name])
                    def download(model, job_id):
                        self.assertEqual((model, job_id), (name, name))
                        path.write_bytes(b'0' * 10)
                        return {'state': 'done'}
                    self.downloads.start.side_effect = download
                    self.downloads.start.reset_mock()
                    with patch.object(self.builder, 'generate') as generate:
                        response = self.client.post('/api/dataset-builder/jobs', data={'spec': json.dumps(
                            dict(name=style, trigger='ohwx', prompt='A robot', style=style))})
                        self.assertEqual(response.status_code, 200, response.text)
                        self.builder.thread.join(3)
                        self.assertFalse(self.builder.thread.is_alive())
                        self.assertEqual(self.builder.read(response.json()['id'])['status'], 'reference_review')
                        self.downloads.start.assert_called_once_with(name, name)
                        self.assertEqual(generate.call_count, 4)
                        for call in generate.call_args_list:
                            self.assertEqual(call.args[1]['1']['inputs']['ckpt_name'], filename)
                    self.assertEqual(self.builder.missing_models('prompt', style), [])
                    with patch.object(self.builder, 'start'):
                        response = self.client.post('/api/dataset-builder/jobs', data={'spec': json.dumps(
                            dict(name=style + 'again', trigger='ohwx', prompt='A robot', style=style))})
                    self.assertEqual(response.json()['phase'], 'reference')
                    self.builder.require_ready.assert_called_with('prompt', style)

    def test_preflight_and_resume_use_selected_style(self):
        with patch.object(self.builder, 'request', return_value={}), \
             patch('apps.Portal.services.dataset_builder.validate_graph') as validate:
            for style in REFERENCE_MODELS:
                response = self.client.get('/api/dataset-builder/preflight', params={'style': style})
                self.assertTrue(response.json()['ready'])
                self.assertEqual(validate.call_args.args[0], reference_graph('test', 1, 'test', style))
        self.assertEqual(self.client.get('/api/dataset-builder/preflight?style=invalid').status_code, 422)
        job = self.create(style='illustration')
        job['spec']['source'] = 'prompt'
        job['status'] = 'paused'
        self.builder.save(job)
        with patch.object(self.builder, 'start'):
            self.assertEqual(self.client.post(f'/api/dataset-builder/jobs/{job["id"]}/resume').status_code, 200)
        self.builder.require_ready.assert_called_with('prompt', 'illustration')

    def test_image_checks_find_duplicates(self):
        path = self.root / 'image.png'; path.write_bytes(photo_bytes())
        other = self.root / 'copy.png'; other.write_bytes(photo_bytes())
        self.assertEqual(image_checks(path)[0], image_checks(other)[0])

    def test_missing_dependencies_are_actionable(self):
        self.missing.stop()
        with patch.object(self.builder, 'request', side_effect=HTTPException(503, 'Start ComfyUI in Services')):
            result = self.builder.preflight('prompt')
        self.assertFalse(result['ready'])
        self.assertIn('dataset-local-captioner', result['missing'])
        self.assertIn('realvisxl-v5', result['missing'])
        self.assertNotIn('sdxl-base', result['missing'])
        self.assertIn('Start ComfyUI in Services', result['problems'])
        self.assertEqual(set(self.builder.missing_models('photo')), set(result['missing']) - {'realvisxl-v5'})
