"""Persistent, single-worker dataset creation. GPU execution stays in ComfyUI."""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Literal

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageFilter, ImageOps, ImageStat
from pydantic import BaseModel, Field, ValidationError

from .comfy_access import internal_headers
from .dataset_generation import (CAPTION_MODEL, CHECKPOINT, MODEL_FILES, MODEL_SIZES, RECIPE_VERSION,
                                 reference_graph, shot_plan, validate_graph, variation_graph)
from .service_registry import local_url
from .training_runs import now, write_json

MAX_IMAGE = 32 * 1024 ** 2
ACTIVE = {'generating_reference', 'generating', 'checking', 'pausing'}


class BuildSpec(BaseModel):
    name: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
    trigger: str = Field(pattern=r'^[A-Za-z][A-Za-z0-9_]{0,39}$')
    source: Literal['prompt', 'photo'] = 'prompt'
    prompt: str = Field(default='', max_length=2000)
    count: int = Field(default=24, ge=4, le=40)
    goal: Literal['identity', 'character'] = 'identity'
    vary_clothes: bool = True
    vary_hair: bool = False


class ReferenceChoice(BaseModel):
    file: str


class ImageChoice(BaseModel):
    accepted: bool
    caption: str = Field(min_length=1, max_length=2000)


def safe_path(root, *parts):
    root = Path(root)
    path = root.joinpath(*parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise HTTPException(400, 'Path must stay in the dataset builder workspace')
    for entry in [path, *path.parents]:
        if entry.is_symlink():
            raise HTTPException(400, 'Symbolic links are not supported in dataset builder files')
        if entry == root:
            break
    return path


def save_image(data, destination):
    if len(data) > MAX_IMAGE:
        raise HTTPException(413, 'Choose an image smaller than 32 MB')
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 40_000_000 or min(image.size) < 256:
                raise ValueError('size')
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((1536, 1536))
            with open(destination, 'xb') as stream:
                image.save(stream, format='PNG')
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(400, 'Use a readable photo at least 256 px per side and below 40 megapixels') from exc


def image_checks(path):
    with Image.open(path) as image:
        gray = image.convert('L')
        thumb = list(gray.resize((9, 8)).getdata())
        bits = [thumb[row * 9 + col] > thumb[row * 9 + col + 1] for row in range(8) for col in range(8)]
        fingerprint = sum(int(bit) << i for i, bit in enumerate(bits))
        edges = gray.resize((256, 256)).filter(ImageFilter.FIND_EDGES).crop((2, 2, 254, 254))
        warnings = []
        if min(image.size) < 512:
            warnings.append('Small image: short side is below 512 px.')
        if ImageStat.Stat(edges).var[0] < 12:
            warnings.append('Possibly blurry or low-detail image; inspect it before keeping.')
        return fingerprint, warnings


class DatasetBuilder:
    def __init__(self, workspace, models, invalidate=lambda: None):
        self.workspace, self.models = Path(workspace), Path(models)
        self.root = safe_path(self.workspace, 'config', 'dataset-builder')
        self.invalidate = invalidate
        self.lock = threading.RLock()
        self.thread = None
        self.stop = threading.Event()
        self.closing = threading.Event()
        self.vision_process = None
        self.active_id = None

    def close(self):
        self.closing.set()
        self.stop.set()
        proc = self.vision_process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    def directory(self, job_id):
        if not re.fullmatch(r'[a-f0-9]{32}', job_id):
            raise HTTPException(404, 'Dataset creation job not found')
        return safe_path(self.workspace, 'config', 'dataset-builder', job_id)

    def read(self, job_id):
        path = safe_path(self.directory(job_id), 'state.json')
        if not path.is_file():
            raise HTTPException(404, 'Dataset creation job not found')
        data = json.loads(path.read_text())
        if data['status'] in ACTIVE and self.active_id != job_id:
            data['status'] = 'paused'
            data['message'] = 'Interrupted by a restart. Resume to recover the saved work.'
        return data

    def save(self, job):
        job['updated_at'] = now()
        write_json(safe_path(self.directory(job['id']), 'state.json'), job)

    def public(self, job):
        result = dict(job)
        result['accepted_count'] = sum(bool(x.get('accepted')) for x in job['items'])
        if self.stop.is_set() and self.active_id == job['id'] and job['status'] in ACTIVE:
            result.update(status='pausing', message='Pausing after the current image. Other ComfyUI jobs will not be interrupted.')
        return result

    def request(self, method, path, **kwargs):
        try:
            with httpx.Client(timeout=30, trust_env=False) as client:
                response = client.request(method, local_url('comfy') + '/' + path,
                                          headers=internal_headers(), **kwargs)
                if 400 <= response.status_code < 500:
                    raise HTTPException(409, 'ComfyUI rejected the dataset job. Check its logs in Services.')
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(503, 'ComfyUI is unavailable. Start it in Services and retry.') from exc

    def preflight(self, source):
        missing = []
        for name, (folder, filename) in MODEL_FILES.items():
            path = self.models / folder / filename
            if not path.is_file() or path.stat().st_size != MODEL_SIZES[name]:
                missing.append(name)
        caption = self.models / 'text_encoders' / CAPTION_MODEL
        required = ['config.json', 'preprocessor_config.json', 'video_preprocessor_config.json',
                    'tokenizer_config.json', 'tokenizer.json', 'chat_template.json', 'model.safetensors']
        shards = {'model.safetensors': 4255140312}
        if (not all((caption / name).is_file() for name in required)
                or any(not (caption / name).is_file() or (caption / name).stat().st_size != size for name, size in shards.items())):
            missing.append('dataset-local-captioner')
        checkpoint = self.models / 'checkpoints' / CHECKPOINT
        if source == 'prompt' and (not checkpoint.is_file() or checkpoint.stat().st_size != MODEL_SIZES['sdxl-base']):
            missing.append('sdxl-base')
        problems = []
        if missing:
            problems.append('Install missing models in Models: ' + ', '.join(missing))
        try:
            registry = self.request('GET', 'object_info')
            validate_graph(variation_graph('reference.png', 'test', 1, 'test'), registry)
            if source == 'prompt':
                validate_graph(reference_graph('test', 1, 'test'), registry)
        except HTTPException as exc:
            problems.append(str(exc.detail))
        return dict(ready=not problems, missing=missing, problems=problems, recipe=RECIPE_VERSION,
                    captioning='Local Qwen3-VL on CPU; no external captioning API.')

    def require_ready(self, source):
        result = self.preflight(source)
        if not result['ready']:
            raise HTTPException(409, ' '.join(result['problems']))

    def idle(self, job=None):
        if self.thread and self.thread.is_alive():
            raise HTTPException(409, 'A dataset job is already running. Pause it before making changes.')
        if job and job['status'] == 'saved':
            raise HTTPException(409, 'This dataset is already saved. Create a new job for another version.')

    def create(self, spec, photo):
        with self.lock:
            self.idle()
            if spec.source == 'prompt' and not spec.prompt.strip():
                raise HTTPException(400, 'Describe the character you want to create')
            if spec.source == 'photo' and not photo:
                raise HTTPException(400, 'Choose a reference photo')
            self.require_ready(spec.source)
            if shutil.disk_usage(self.workspace).free < (spec.count * 12 + 200) * 1024 ** 2:
                raise HTTPException(409, 'Not enough workspace space for this dataset. Free space in Storage.')
            job_id = uuid.uuid4().hex
            directory = self.directory(job_id)
            directory.mkdir(parents=True, mode=0o700)
            job = dict(id=job_id, spec=spec.model_dump(), status='reference_review', phase='reference',
                       message='Choose the reference to use for every variation.', references=[], reference=None,
                       items=[], pending=None, created_at=now(), recipe=RECIPE_VERSION)
            if spec.source == 'photo':
                save_image(photo, safe_path(directory, 'reference-upload.png'))
                job['references'] = ['reference-upload.png']
            self.save(job)
            if spec.source == 'prompt':
                self.start(job)
            return self.public(job)

    def start(self, job):
        self.idle(job)
        if self.closing.is_set():
            raise HTTPException(503, 'ControlPilot is restarting. Try again after it reconnects.')
        self.stop.clear()
        self.active_id = job['id']
        job['status'] = 'generating_reference' if job['phase'] == 'reference' else 'generating'
        job['message'] = 'Queued for generation. You can leave this page and return later.'
        self.save(job)
        self.thread = threading.Thread(target=self.work, args=(job,), daemon=True)
        self.thread.start()

    def generate(self, job, graph, filename):
        directory = self.directory(job['id'])
        target = safe_path(directory, filename)
        if target.is_file():
            with Image.open(target) as image:
                image.verify()
            return  # Recover a completed download if Portal stopped before recording it in state.json.
        pending = job.get('pending')
        if pending and pending['file'] != filename:
            raise RuntimeError('A previous image is still pending. Resume that image first.')
        if not pending:
            validate_graph(graph, self.request('GET', 'object_info'), uploaded=True)
            write_json(safe_path(directory, filename + '.workflow.json'), graph)
            # Save intent before submission; a lost HTTP response must not silently resubmit paid GPU work.
            job['pending'] = dict(file=filename, prompt_id=None)
            self.save(job)
            try:
                result = self.request('POST', 'prompt', json={'prompt': graph, 'client_id': job['id']})
            except HTTPException as exc:
                if exc.status_code == 409:  # A definite rejection is safe to retry; timeouts are not.
                    job['pending'] = None
                    self.save(job)
                raise
            if not isinstance(result.get('prompt_id'), str) or not result['prompt_id']:
                raise RuntimeError('ComfyUI submission outcome is unknown. Check its queue before starting a new dataset job.')
            job['pending']['prompt_id'] = result['prompt_id']
            self.save(job)
        prompt_id = job['pending']['prompt_id']
        if not prompt_id:
            raise RuntimeError('ComfyUI submission outcome is unknown. Check its queue before starting a new dataset job.')
        deadline = time.monotonic() + 3600
        while time.monotonic() < deadline:
            if self.closing.is_set():
                raise RuntimeError('ControlPilot restarted. Resume to recover the pending ComfyUI image.')
            history = self.request('GET', f'history/{prompt_id}').get(prompt_id)
            if history:
                if history.get('status', {}).get('status_str') == 'error':
                    for item in job['items']:
                        if filename == f'image-{item["slot"]:03d}-{item["attempts"]}.png':
                            item['attempts'] += 1
                            break
                    job['pending'] = None
                    self.save(job)
                    raise RuntimeError('ComfyUI generation failed. Check its logs, then resume.')
                images = [image for out in history.get('outputs', {}).values() for image in out.get('images', [])]
                if images:
                    image = images[0]
                    with httpx.Client(timeout=60, trust_env=False) as client:
                        with client.stream('GET', local_url('comfy') + '/view', headers=internal_headers(),
                                           params={key: image.get(key, '') for key in ('filename', 'subfolder', 'type')}) as response:
                            response.raise_for_status()
                            data = bytearray()
                            for chunk in response.iter_bytes():
                                data.extend(chunk)
                                if len(data) > MAX_IMAGE:
                                    raise RuntimeError('Generated image exceeded the size limit')
                    if not target.exists():
                        temporary = safe_path(directory, filename + '.download')
                        if temporary.exists():
                            temporary.unlink()
                        save_image(bytes(data), temporary)
                        os.replace(temporary, target)
                    return
            self.closing.wait(2)
        raise RuntimeError('ComfyUI is still pending after one hour. Resume later to recover the same image.')

    def review(self, job):
        directory = self.directory(job['id'])
        items = [x for x in job['items'] if x.get('file') and not x.get('review')]
        if not items:
            return
        job['status'], job['message'] = 'checking', 'Writing captions and checking identity locally on CPU. This can take several minutes.'
        self.save(job)
        write_json(safe_path(directory, 'vision-request.json'), dict(reference=job['reference'], goal=job['spec']['goal'], items=items))
        result_path = safe_path(directory, 'vision-result.json')
        write_json(result_path, {})
        core = Path('/opt/venvs/core/bin/python')
        python = str(core) if core.exists() else sys.executable
        log_path = safe_path(directory, 'vision.log')
        with os.fdopen(os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600), 'w') as log:
            proc = subprocess.Popen([python, str(Path(__file__).with_name('dataset_vision.py')), str(directory),
                                     str(self.models / 'text_encoders' / CAPTION_MODEL)], stdout=log, stderr=log,
                                    env={**os.environ, 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'})
            self.vision_process = proc
            deadline = time.monotonic() + 7200
            try:
                while proc.poll() is None:
                    if self.stop.wait(1) or time.monotonic() > deadline:
                        proc.terminate()
                        break
                proc.wait(timeout=15)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                self.vision_process = None
        results = json.loads(result_path.read_text())
        for item in items:
            result = results.get(item['file'])
            if not result or 'error' in result:
                item['warnings'] = ['Local checks incomplete. Resume to retry captioning.']
                continue
            fingerprint, warnings = image_checks(safe_path(directory, item['file']))
            for other in job['items']:
                if other is not item and 'fingerprint' in other and (fingerprint ^ other['fingerprint']).bit_count() <= 3:
                    warnings.append('Very similar to another image; check that it adds useful variation.')
                    break
            item['fingerprint'] = fingerprint
            if result['identity'] != 'consistent':
                warnings.append('Identity ' + result['identity'] + ': compare with the reference before keeping.')
            warnings.extend(result['issues'])
            item.update(review=result, warnings=warnings, caption=(job['spec']['trigger'] + ', ' + result['caption'])[:2000],
                        accepted=not warnings)
        self.save(job)
        if not self.stop.is_set() and any(not x.get('review') for x in items):
            raise RuntimeError('Local captioning/checks did not finish. Check the job vision.log, then Resume to retry. No external API was used.')

    def work(self, job):
        try:
            directory = self.directory(job['id'])
            if job['phase'] == 'reference':
                for index in range(len(job['references']), 4):
                    if self.stop.is_set():
                        break
                    filename = f'reference-{index}.png'
                    self.generate(job, reference_graph(job['spec']['prompt'], int(job['id'][:8], 16) + index,
                                                       f'DatasetBuilder/{job["id"]}/{filename[:-4]}'), filename)
                    job['references'].append(filename)
                    job['pending'] = None
                    self.save(job)
                job['status'] = 'paused' if self.stop.is_set() else 'reference_review'
                job['message'] = 'Choose the reference to use for every variation.'
            else:
                reference = safe_path(directory, job['reference'])
                with open(reference, 'rb') as stream:
                    upload = self.request('POST', 'upload/image', files={'image': (f'{job["id"]}.png', stream, 'image/png')},
                                          data={'type': 'input', 'subfolder': 'dataset-builder', 'overwrite': 'true'})
                image_name = '/'.join(filter(None, [upload.get('subfolder'), upload['name']]))
                for attempt in range(3):
                    for item in job['items']:
                        if self.stop.is_set():
                            break
                        if job.get('retry_slots') is not None and item['slot'] not in job['retry_slots']:
                            continue
                        # Existing files without a review are retried by the local worker, not regenerated.
                        if item.get('accepted') or (item.get('file') and not item.get('review')) or item['attempts'] >= 3:
                            continue
                        filename = f'image-{item["slot"]:03d}-{item["attempts"]}.png'
                        seed = int(job['id'][:8], 16) + item['slot'] * 10 + item['attempts']
                        job['status'], job['message'] = 'generating', f'Creating image {item["slot"] + 1} of {job["spec"]["count"]} (attempt {item["attempts"] + 1}/3).'
                        self.save(job)
                        self.generate(job, variation_graph(image_name, item['prompt'], seed,
                                                            f'DatasetBuilder/{job["id"]}/{filename[:-4]}'), filename)
                        item.pop('fingerprint', None)
                        item.update(file=filename, attempts=item['attempts'] + 1, review=None, accepted=False,
                                    caption='', warnings=[], user_reviewed=False, seed=seed)
                        job['pending'] = None
                        self.save(job)
                    if self.stop.is_set():
                        break
                    self.review(job)
                    if all(x.get('accepted') or x['attempts'] >= 3 for x in job['items']):
                        break
                job['status'] = 'paused' if self.stop.is_set() else 'review'
                accepted = sum(bool(x.get('accepted')) for x in job['items'])
                job['message'] = f'{accepted} of {job["spec"]["count"]} images passed automated checks. Review the contact sheet before saving.'
                if any(not x.get('file') and x['attempts'] >= 3 for x in job['items']):
                    job['message'] += ' A shot exhausted its three attempts without an image. Fix the ComfyUI error and create a new job.'
        except Exception as exc:
            job['status'] = 'paused' if self.stop.is_set() else 'failed'
            job['message'] = str(exc.detail) if isinstance(exc, HTTPException) else str(exc)
        finally:
            with self.lock:
                self.save(job)
                self.active_id = None

    def finish(self, job):
        self.idle()
        if job['status'] == 'saved':
            return self.public(job)
        if len(job['items']) != job['spec']['count'] or any(not x.get('accepted') or not x.get('caption', '').strip() or not x.get('review') for x in job['items']):
            raise HTTPException(409, 'Keep and caption every requested image before saving. Flagged images need your review.')
        directory = self.directory(job['id'])
        datasets = safe_path(self.workspace, 'datasets')
        datasets.mkdir(parents=True, exist_ok=True)
        name = '1_' + job['spec']['name']
        target = safe_path(datasets, name)
        if target.exists():
            # Recover a crash after publication but before the job state was saved.
            metadata = safe_path(target, 'generation.json')
            try:
                published = json.loads(metadata.read_text()) if metadata.is_file() else {}
            except (ValueError, OSError):
                published = {}
            matches = published.get('id') == job['id'] and published.get('items') == job['items']
            for item in job['items'] if matches else []:
                basename = f'{item["slot"] + 1:03d}'
                photo = safe_path(target, basename + '.png')
                caption = safe_path(target, basename + '.txt')
                matches = (matches and photo.is_file() and caption.is_file()
                           and photo.read_bytes() == safe_path(directory, item['file']).read_bytes()
                           and caption.read_text() == item['caption'].strip() + '\n')
            if not matches:
                raise HTTPException(409, 'That dataset name already exists. Rename it in Datasets before saving this version.')
            return self.mark_saved(job, name)
        staging = safe_path(directory, 'export')
        staging.mkdir(exist_ok=True)
        for item in job['items']:
            source = safe_path(directory, item['file'])
            basename = f'{item["slot"] + 1:03d}'
            shutil.copyfile(source, safe_path(staging, basename + '.png'))
            safe_path(staging, basename + '.txt').write_text(item['caption'].strip() + '\n')
        write_json(safe_path(staging, 'generation.json'), job)
        # Atomic publication within /workspace: incomplete jobs never appear as training datasets.
        if target.exists():
            raise HTTPException(409, 'The dataset name was just taken. Choose a different name.')
        os.rename(staging, target)
        return self.mark_saved(job, name)

    def mark_saved(self, job, name):
        job.update(status='saved', dataset=name, message='Dataset saved. Ready for guided training.')
        self.save(job)
        self.invalidate()
        return self.public(job)


def create_router(workspace, models, invalidate=lambda: None):
    builder = DatasetBuilder(workspace, models, invalidate)
    router = APIRouter(prefix='/api/dataset-builder')
    router.add_event_handler('shutdown', builder.close)

    @router.get('/preflight')
    def preflight(source: Literal['prompt', 'photo'] = 'prompt'):
        return builder.preflight(source)

    @router.get('/jobs')
    def jobs():
        with builder.lock:
            root = safe_path(builder.workspace, 'config', 'dataset-builder')
            entries = sorted(root.glob('*/state.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:100]
            return [builder.public(builder.read(p.parent.name)) for p in entries]

    @router.post('/jobs')
    def create(spec: str = Form(...), photo: UploadFile | None = File(None)):
        try:
            options = BuildSpec.model_validate_json(spec)
        except ValidationError as exc:
            raise HTTPException(422, 'Use a short dataset name and trigger word with letters, numbers or underscores, and 4–40 images.') from exc
        data = photo.file.read(MAX_IMAGE + 1) if photo else None
        return builder.create(options, data)

    @router.get('/jobs/{job_id}')
    def get(job_id: str):
        with builder.lock:
            return builder.public(builder.read(job_id))

    @router.get('/jobs/{job_id}/images/{filename}')
    def image(job_id: str, filename: str):
        with builder.lock:
            job = builder.read(job_id)
            names = job['references'] + [x['file'] for x in job['items'] if x.get('file')]
            if filename not in names:
                raise HTTPException(404, 'Image not found')
            return FileResponse(safe_path(builder.directory(job_id), filename), media_type='image/png')

    @router.post('/jobs/{job_id}/reference')
    def approve(job_id: str, choice: ReferenceChoice):
        with builder.lock:
            job = builder.read(job_id)
            builder.idle(job)
            if job['phase'] != 'reference' or choice.file not in job['references'] or job.get('pending'):
                raise HTTPException(409, 'Choose an available reference after generation finishes')
            builder.require_ready('photo')
            job['reference'] = choice.file
            job['phase'] = 'variations'
            job['items'] = shot_plan(job['spec']['count'], job['spec']['goal'], job['spec']['vary_clothes'], job['spec']['vary_hair'])
            builder.start(job)
            return builder.public(job)

    @router.post('/jobs/{job_id}/resume')
    def resume(job_id: str):
        with builder.lock:
            job = builder.read(job_id)
            builder.idle(job)
            builder.require_ready(job['spec']['source'] if job['phase'] == 'reference' else 'photo')
            job.pop('retry_slots', None)
            builder.start(job)
            return builder.public(job)

    @router.post('/jobs/{job_id}/pause')
    def pause(job_id: str):
        with builder.lock:
            if builder.active_id != job_id:
                raise HTTPException(409, 'This job is not running')
            builder.stop.set()
            return {'message': 'Pausing after the current image. Other ComfyUI jobs will not be interrupted.'}

    @router.patch('/jobs/{job_id}/images/{slot}')
    def choose(job_id: str, slot: int, choice: ImageChoice):
        with builder.lock:
            job = builder.read(job_id)
            builder.idle(job)
            if slot < 0 or slot >= len(job['items']) or not job['items'][slot].get('review'):
                raise HTTPException(409, 'Wait for local checks and captions before reviewing this image')
            job['items'][slot].update(accepted=choice.accepted, caption=choice.caption, user_reviewed=True)
            builder.save(job)
            return builder.public(job)

    @router.post('/jobs/{job_id}/images/{slot}/regenerate')
    def regenerate(job_id: str, slot: int):
        with builder.lock:
            job = builder.read(job_id)
            builder.idle(job)
            if slot < 0 or slot >= len(job['items']) or job.get('pending'):
                raise HTTPException(409, 'Resume the pending image before regenerating')
            item = job['items'][slot]
            if item.get('file') and not item.get('review'):
                raise HTTPException(409, 'Resume local checks before regenerating this image')
            if item['attempts'] >= 3:
                raise HTTPException(409, 'Three attempts used for this shot. Review the last image or start a new job with a better reference.')
            builder.require_ready('photo')
            item['accepted'] = False
            job['retry_slots'] = [slot]
            builder.start(job)
            return builder.public(job)

    @router.post('/jobs/{job_id}/finish')
    def finish(job_id: str):
        with builder.lock:
            return builder.finish(builder.read(job_id))

    return router, builder
