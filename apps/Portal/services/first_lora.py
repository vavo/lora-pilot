"""Optional first-run guide using the original orange robot video dataset."""
import hashlib
import json
import shutil
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .dataset_quality import review_dataset
from .training_runs import under, write_json

BUNDLE = Path(__file__).resolve().parents[1] / 'samples/orange-robot'
DATASET = '1_orange_robot_demo'


def create_router(workspace, queue, recipe, invalidate):
    router = APIRouter(prefix='/first-lora')
    lock = threading.RLock()
    workspace = Path(workspace).resolve()
    state_path = under(workspace, workspace / 'config/first-lora.json')

    def read_state():
        if state_path.is_symlink():
            raise HTTPException(400, 'Invalid guide state path')
        return json.loads(state_path.read_text()) if state_path.exists() else {}

    def signature(dataset):
        return recipe.fingerprint(dataset, recipe.dataset_files(dataset))

    def state():
        saved = read_state()
        manifest = json.loads((BUNDLE / 'manifest.json').read_text())
        result = {key: manifest[key] for key in ('title', 'trigger_word', 'family', 'profile', 'sample_prompt')}
        result.update(dataset=None, reviewed=False, trained=False, compared=False, run_id=None, run_status=None)
        dataset = workspace / 'datasets' / DATASET
        if not saved.get('installed') or dataset.is_symlink() or not dataset.is_dir():
            return result
        dataset = under(workspace / 'datasets', dataset)
        result['dataset'] = DATASET
        try:
            fingerprint = signature(dataset)
        except HTTPException:
            return result
        result['reviewed'] = saved.get('reviewed') == fingerprint
        runs = [run for run in queue.list() if run.get('dataset') == str(dataset)
                and run.get('dataset_fingerprint') == fingerprint and run['spec']['family'] == 'sdxl']
        if runs:
            run = next((run for run in runs if run['status'] == 'succeeded'), runs[0])
            result.update(run_id=run['id'], run_status=run['status'], trained=run['status'] == 'succeeded')
            path = under(queue.directory(run['id']), queue.directory(run['id']) / 'comparison.json')
            if result['trained'] and path.is_file():
                comparison = json.loads(path.read_text())
                result['compared'] = comparison.get('status') == 'succeeded' and len(comparison.get('images', [])) >= 2
        return result

    @router.get('')
    def status():
        with lock:
            return state()

    @router.get('/preview')
    def preview():
        return FileResponse(BUNDLE / 'ceramic_robot_00001_.png', media_type='image/png')

    @router.post('/install')
    def install():
        with lock:
            if state()['dataset']:
                return state()
            target = under(workspace / 'datasets', workspace / 'datasets' / DATASET)
            if target.exists():
                raise HTTPException(409, 'A dataset named orange_robot_demo already exists. Rename it before installing the sample.')
            manifest = json.loads((BUNDLE / 'manifest.json').read_text())
            target.mkdir(parents=True, exist_ok=False)
            try:
                for name, digest in manifest['files'].items():
                    if Path(name).name != name:
                        raise HTTPException(500, 'Invalid bundled dataset manifest')
                    source = BUNDLE / name
                    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                        raise HTTPException(500, 'Bundled dataset failed its integrity check')
                    shutil.copyfile(source, target / name)
                state_path.parent.mkdir(parents=True, exist_ok=True)
                write_json(state_path, dict(installed=True, reviewed=None))
            except Exception:
                shutil.rmtree(target)
                raise
            invalidate()
            return state()

    @router.post('/reviewed')
    def reviewed():
        with lock:
            current = state()
            if not current['dataset']:
                raise HTTPException(409, 'Install the sample dataset first')
            dataset = recipe.resolve_dataset(DATASET)
            report = review_dataset(dataset)
            if not report['complete'] or report['findings'] or report['images'] == 0:
                raise HTTPException(409, 'Resolve dataset quality findings before marking the captions reviewed')
            write_json(state_path, dict(installed=True, reviewed=signature(dataset)))
            return state()

    return router
