"""ControlPilot history, queue and LoRA comparison endpoints."""
import json
import filecmp
import os
import shutil
import stat
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel

from . import gpu_guard
from .training_timing import timing
from .guided_training import GuidedTraining, TrainingRequest
from .lora_comparison import ComparisonRequest, checkpoint_order, comparison_outputs, comfy, graph, result_images
from .training_runs import TrainingRuns, under, write_json, now


class QueueRequest(BaseModel):
    paused: bool


class LibraryRequest(BaseModel):
    action: Literal['copy', 'move'] = 'copy'


def create_router(workspace, models, resolve_dataset, resolve_config, model_name, legacy_conflicts):
    router = APIRouter(prefix='/api/training')
    workspace, models = Path(workspace).resolve(), Path(models).resolve()
    recipe = GuidedTraining(workspace, models, resolve_dataset, resolve_config, model_name)
    queue = TrainingRuns(under(workspace, workspace / 'config/training'), recipe.prepare, recipe.launch,
                         lambda: legacy_conflicts() + gpu_guard.conflicts())

    def managed_conflicts():
        reasons = legacy_conflicts()
        if queue.proc and queue.proc.poll() is None:
            reasons.append('A guided training run is active.')
        if queue.owner:
            reasons.extend(queue.orphan_conflicts())
        return reasons

    gpu_guard.managed_conflicts = managed_conflicts

    def ready():
        queue.start()

    def artifact_paths(run):
        output = under(workspace / 'outputs', Path(run['output_dir']))
        library = under(models, models / 'loras/ControlPilot' / run['id'])
        paths = {}
        for name in run.get('library_files', []):
            path = library / Path(name).name
            if name == path.relative_to(models / 'loras').as_posix() and not path.is_symlink() and path.is_file():
                paths[path.name] = under(library, path)
        for path in output.glob('*.safetensors'):
            if not path.is_symlink() and path.is_file():
                paths[path.name] = under(output, path)
        return paths

    def artifacts(run):
        paths = artifact_paths(run)
        final_names = {run['spec']['output_name'] + '.safetensors', Path(run['output_dir']).name + '.safetensors'}
        return [dict(name=name, size_bytes=paths[name].stat().st_size,
                     in_output=paths[name].parent == Path(run['output_dir']))
                for name in sorted(paths, key=lambda name: (name in final_names, checkpoint_order(name)))]

    def public(run, detail=False):
        data = {key: value for key, value in run.items() if key not in {'template', 'dataset_fingerprint', 'process_identity'}}
        recovery = recipe.recovery(run)
        data['recovery_option'] = {key: value for key, value in recovery.items() if key != 'path'} if recovery else None
        if detail:
            data['library_destination'] = str(models / 'loras/ControlPilot' / run['id'])
            data['comparison_workflow'] = (queue.directory(run['id']) / 'comparison-workflow.json').is_file()
            data['artifacts'] = artifacts(run)
            data['lines'] = queue.logs(run['id'])
            log = queue.directory(run['id']) / 'run.log'
            data['timing'] = timing(run, data['lines'], log.stat().st_mtime if log.is_file() else None)
            data['config_text'] = under(queue.directory(run['id']), queue.directory(run['id']) / 'template.toml').read_text()
            output = under(workspace / 'outputs', Path(run['output_dir']))
            effective = output / f'{output.name}.toml' if run['spec']['family'] == 'sdxl' else queue.directory(run['id']) / 'effective.toml'
            effective = under(workspace, effective)
            if effective.is_file():
                data['effective_config'] = effective.read_text()
        return data

    @router.on_event('startup')
    def recover():
        if queue.root.exists():
            ready()

    @router.on_event('shutdown')
    def close():
        queue.close()

    @router.get('/runs')
    def list_runs(search: str = Query('', max_length=200), family: str = '', status: str = '',
                  offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
        ready()
        with queue.lock:
            runs = queue.list()
            term = search.strip().casefold()
            matching = [run for run in runs if (not family or run['spec']['family'] == family)
                        and (not status or run['status'] == status)
                        and (not term or term in (run['spec']['output_name'] + ' ' + run['spec']['dataset_name']).casefold())]
            return {'runs': [public(run) for run in matching[offset:offset + limit]], 'paused': queue.paused,
                    'conflicts': queue.reason, 'active_id': queue.current, 'total': len(matching),
                    'queued_count': sum(run['status'] == 'queued' for run in runs)}

    @router.get('/runs/{run_id}/artifacts/{filename}')
    def download_artifact(run_id: str, filename: str):
        ready()
        with queue.lock:
            run = queue.get(run_id)
            if run['status'] in {'queued', 'running', 'stopping'}:
                raise HTTPException(409, 'Wait for training to stop before downloading a checkpoint')
            selected = next((item for item in artifacts(run) if item['name'] == filename), None)
            if not selected:
                raise HTTPException(404, 'Checkpoint not found')
            filename = selected['name']
            path = artifact_paths(run)[filename]
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            except OSError:
                raise HTTPException(404, 'Checkpoint unavailable')
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                os.close(fd)
                raise HTTPException(400, 'Checkpoint must be a regular file')
            stream = os.fdopen(fd, 'rb')
        def chunks():
            try:
                while data := stream.read(1024 * 1024):
                    yield data
            finally:
                stream.close()
        from urllib.parse import quote
        return StreamingResponse(chunks(), background=BackgroundTask(stream.close), media_type='application/octet-stream', headers={
            'Content-Length': str(info.st_size), 'Content-Disposition': "attachment; filename*=UTF-8''" + quote(filename, safe='')})

    @router.post('/preflight')
    def preflight(req: TrainingRequest):
        config = None
        if req.source_run_id:
            ready()
            old = queue.get(req.source_run_id)
            if old['spec']['family'] != req.family:
                raise HTTPException(400, 'Saved configuration belongs to a different model family')
            config = old['template']
        checks = recipe.requirements(req.model_dump(), config)
        return dict(checks, conflicts=managed_conflicts() + gpu_guard.conflicts(),
                    note='FLUX.1 dev uses full-size weights and substantial GPU/system memory. Block swapping is enabled.'
                         if req.family == 'flux1' else 'SDXL uses the existing Kohya profiles.')

    @router.post('/runs')
    def submit(req: TrainingRequest):
        ready()
        spec = req.model_dump()
        if req.source_run_id:
            old = queue.get(req.source_run_id)
            if old['spec']['family'] != req.family:
                raise HTTPException(400, 'Saved configuration belongs to a different model family')
            spec['_template'] = dict(old['template'])
            if req.family == 'flux1' and req.profile != old['spec']['profile']:
                profile = recipe.template(spec)
                for key in ('network_dim', 'network_alpha', 'max_train_steps'):
                    spec['_template'][key] = profile[key]
        return public(queue.submit(spec))

    @router.post('/queue')
    def set_queue(req: QueueRequest):
        ready()
        queue.set_paused(req.paused)
        return {'paused': queue.paused}

    @router.get('/runs/{run_id}')
    def get_run(run_id: str):
        ready()
        with queue.lock:
            return public(queue.get(run_id), detail=True)

    @router.post('/runs/{run_id}/cancel')
    def cancel_run(run_id: str):
        ready()
        return public(queue.cancel(run_id))

    @router.post('/runs/{run_id}/repeat')
    def repeat_run(run_id: str):
        ready()
        with queue.lock:
            old = queue.get(run_id)
            return public(queue.submit(dict(old['spec'], _template=old['template'])))

    @router.post('/runs/{run_id}/resume')
    def resume_run(run_id: str):
        ready()
        with gpu_guard.LAUNCH_LOCK, queue.lock:
            old = queue.get(run_id)
            if queue.orphan_conflicts():
                raise HTTPException(409, 'An interrupted training process is still running. Stop it before resuming.')
            if any(run.get('recovery', {}).get('source_run_id') == run_id and run['status'] in {'queued', 'running', 'stopping'}
                   for run in queue.list() if run.get('recovery')):
                raise HTTPException(409, 'This run already has a queued or active continuation')
            recovery = recipe.recovery(old)
            if not recovery:
                raise HTTPException(409, 'No saved training state or checkpoint is available. Use Repeat run to start again.')
            dataset = recipe.resolve_dataset(old['spec']['dataset_name']).resolve()
            if recipe.fingerprint(dataset, recipe.dataset_files(dataset)) != old['dataset_fingerprint']:
                raise HTTPException(409, 'The dataset changed. Use Repeat run to train with the current dataset.')
            recovery['source_run_id'] = run_id
            return public(queue.submit(dict(old['spec'], _template=old['template'], _recovery=recovery,
                                            _expected_fingerprint=old['dataset_fingerprint'])))

    def publish_lora(run, name):
        selected = next((item for item in artifacts(run) if item['name'] == name), None)
        if selected is None or run['status'] != 'succeeded':
            raise HTTPException(400, 'Select a saved artifact from a successful training run')
        filename = selected['name']
        source = artifact_paths(run)[filename]
        target_dir = under(models, models / 'loras' / 'ControlPilot' / run['id'])
        target_dir.mkdir(parents=True, exist_ok=True)
        target = under(target_dir, target_dir / filename)
        if target.exists():
            # Never overwrite a user-edited library copy.
            if not filecmp.cmp(target, source, shallow=False):
                raise HTTPException(409, 'A different LoRA already exists in the library destination')
        else:
            temporary = target_dir / (filename + '.partial')
            created = False
            try:
                with temporary.open('xb') as dest:
                    created = True
                    with source.open('rb') as src:
                        shutil.copyfileobj(src, dest)
                os.link(temporary, target)
            except FileExistsError:
                raise HTTPException(409, 'LoRA library destination already exists; retry after checking it')
            finally:
                if created:
                    temporary.unlink(missing_ok=True)
        name = target.relative_to(models / 'loras').as_posix()
        run['library_files'] = sorted(set(run.get('library_files', []) + [name]))
        queue.save(run)
        return name

    @router.post('/runs/{run_id}/library')
    def publish_run(run_id: str, req: LibraryRequest = LibraryRequest()):
        ready()
        with queue.lock:
            run = queue.get(run_id)
            names = [publish_lora(run, item['name']) for item in artifacts(run)]
            if not names:
                raise HTTPException(400, 'No trained files are available')
            run['library_files'] = names
            queue.save(run)
            # Copy and validate every destination before removing any originals.
            if req.action == 'move':
                for item in artifacts(run):
                    if item['in_output']:
                        artifact_paths(run)[item['name']].unlink()
            return {'files': names, 'action': req.action, 'destination': str(models / 'loras/ControlPilot' / run_id)}

    def comparison_file(run_id):
        return under(queue.directory(run_id), queue.directory(run_id) / 'comparison.json')

    @router.post('/runs/{run_id}/comparison/prepare')
    def prepare_comparison(run_id: str, req: ComparisonRequest):
        ready()
        with queue.lock:
            run = queue.get(run_id)
            selected = [item['name'] for item in artifacts(run)] if req.all_checkpoints else [req.artifact]
            if not selected or any(name is None for name in selected):
                raise HTTPException(400, 'Select a checkpoint or compare all checkpoints')
            if len(selected) > 64:
                raise HTTPException(400, 'Compare a single checkpoint for runs with more than 64 saved files')
            names = [publish_lora(run, name) for name in selected]
            # Refresh after publishing: loader dropdowns are the runtime source of truth.
            registry = comfy('GET', 'object_info')
            prompt = graph(run, req, names, registry)
            path = under(queue.directory(run_id), queue.directory(run_id) / 'comparison-workflow.json')
            write_json(path, prompt)
            return {'workflow': prompt}

    @router.get('/runs/{run_id}/comparison/workflow')
    def get_workflow(run_id: str):
        ready()
        queue.get(run_id)
        path = under(queue.directory(run_id), queue.directory(run_id) / 'comparison-workflow.json')
        if not path.exists():
            raise HTTPException(404, 'Prepare a comparison first')
        return JSONResponse(json.loads(path.read_text()), headers={'Content-Disposition': 'attachment; filename="lora-comparison.json"'})

    @router.get('/runs/{run_id}/comparison')
    def comparison_status(run_id: str):
        ready()
        with queue.lock:
            queue.get(run_id)
            path = comparison_file(run_id)
            if not path.exists():
                return {'status': 'none', 'images': []}
            data = json.loads(path.read_text())
            if data['status'] not in {'queued', 'running'}:
                return data
            history = comfy('GET', 'history/' + data['prompt_id']).get(data['prompt_id'])
            if history:
                data['images'] = result_images(history, data.get('outputs'))
                expected_count = len(data.get('outputs', [])) or 2
                status = history.get('status', {})
                if status.get('status_str') == 'error':
                    data.update(status='failed', error='ComfyUI generation failed. Inspect its execution log.')
                elif status.get('completed'):
                    data.update(status='succeeded' if len(data['images']) == expected_count else 'failed')
                    if len(data['images']) != expected_count:
                        data['error'] = 'ComfyUI completed without all comparison images.'
            else:
                jobs = comfy('GET', 'queue')
                running = [item[1] for item in jobs.get('queue_running', [])]
                pending = [item[1] for item in jobs.get('queue_pending', [])]
                data['status'] = 'running' if data['prompt_id'] in running else 'queued' if data['prompt_id'] in pending else 'unavailable'
                if data['status'] == 'unavailable':
                    data['error'] = 'ComfyUI no longer has this job. Check its history before generating again.'
            write_json(path, data)
            return data

    @router.post('/runs/{run_id}/comparison/reset')
    def reset_comparison(run_id: str):
        ready()
        with queue.lock:
            queue.get(run_id)
            jobs = comfy('GET', 'queue')
            if jobs.get('queue_running') or jobs.get('queue_pending'):
                raise HTTPException(409, 'Wait until the ComfyUI queue is empty before resetting an unconfirmed comparison')
            state = {'status': 'none', 'images': []}
            write_json(comparison_file(run_id), state)
            return state

    @router.post('/runs/{run_id}/comparison')
    def generate_comparison(run_id: str, req: ComparisonRequest):
        ready()
        with gpu_guard.LAUNCH_LOCK, queue.lock:
            current = comparison_status(run_id)
            if current['status'] in {'queued', 'running', 'submitting', 'unknown'}:
                raise HTTPException(409, 'A comparison is active or its submission is unconfirmed. Check ComfyUI before retrying.')
            blockers = managed_conflicts()
            if blockers:
                raise HTTPException(409, ' '.join(blockers))
            prompt = prepare_comparison(run_id, req)['workflow']
            state = dict(status='submitting', created_at=now(), request=req.model_dump(), images=[],
                         outputs=comparison_outputs(prompt))
            write_json(comparison_file(run_id), state)
            try:
                result = comfy('POST', 'prompt', json={'prompt': prompt, 'client_id': 'controlpilot-' + run_id})
                if not result.get('prompt_id') or result.get('node_errors'):
                    raise HTTPException(400, 'ComfyUI could not validate the comparison workflow')
                state.update(status='queued', prompt_id=result['prompt_id'])
            except HTTPException as error:
                state.update(status='unknown' if error.status_code == 503 else 'failed', error=str(error.detail))
                write_json(comparison_file(run_id), state)
                raise
            write_json(comparison_file(run_id), state)
            return state

    return router, queue
