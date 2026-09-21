"""Reviewed SDXL and FLUX.1-dev recipes for the persistent training queue."""
import hashlib
import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

try:
    from ..dpipe_api import toml
except ImportError:
    from dpipe_api import toml
from .training_runs import under
from .lora_comparison import checkpoint_order

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
FLUX_MODELS = {
    'pretrained_model_name_or_path': ('flux1-dev', 'diffusion_models/flux1-dev.safetensors'),
    'ae': ('flux1-ae', 'vae/ae.safetensors'),
    'clip_l': ('flux-clip-l', 'text_encoders/clip_l.safetensors'),
    't5xxl': ('flux-t5xxl-fp16', 'text_encoders/t5xxl_fp16.safetensors'),
}


def complete_checkpoint(path):
    try:
        if path.is_symlink():
            return False
        with path.open('rb') as stream:
            size = int.from_bytes(stream.read(8), 'little')
            if not 2 <= size <= 16 * 1024 * 1024:
                return False
            header = json.loads(stream.read(size))
        offsets = [value['data_offsets'][1] for key, value in header.items() if key != '__metadata__']
        return bool(offsets) and 8 + size + max(offsets) == path.stat().st_size
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError):
        return False


class TrainingRequest(BaseModel):
    dataset_name: str = Field(min_length=1, max_length=200)
    output_name: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')
    family: Literal['sdxl', 'flux1'] = 'sdxl'
    profile: Literal['quick_test', 'regular', 'high_quality'] = 'regular'
    toml_path: str = ''
    source_run_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')


class GuidedTraining:
    def __init__(self, workspace, models, resolve_dataset, resolve_config, model_name):
        self.workspace = Path(workspace).resolve()
        self.models = Path(models).resolve()
        self.resolve_dataset = resolve_dataset
        self.resolve_config = resolve_config
        self.model_name = model_name

    def recovery(self, run):
        if run['status'] not in {'stopped', 'failed', 'interrupted', 'cancelled'}:
            return None
        output = under(self.workspace / 'outputs', Path(run['output_dir']))
        states = []
        for path in output.glob('*-state'):
            if path.is_symlink() or not path.is_dir():
                continue
            files = list(path.rglob('*'))
            if any(p.is_symlink() for p in files):
                continue
            required = ['train_state.json', 'optimizer.bin', 'scheduler.bin', 'random_states_0.pkl']
            if not all((path / name).is_file() and (path / name).stat().st_size for name in required):
                continue
            if not any((path / name).is_file() and (path / name).stat().st_size for name in ['model.safetensors', 'pytorch_model.bin']):
                continue
            try:
                step = json.loads((path / 'train_state.json').read_text())['current_step']
                if type(step) is int and step > 0:
                    states.append((step, path))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        if states:
            step, path = max(states, key=lambda item: item[0])
            return dict(mode='state', path=str(path), step=step, label='Resume training',
                        message=f'Resume from saved training state at step {step}. Work since that save is lost. A new run keeps the original files and logs intact.')
        checkpoints = [path for path in output.glob('*.safetensors') if complete_checkpoint(path)]
        if checkpoints:
            path = max(checkpoints, key=lambda p: (p.name in {run['spec']['output_name'] + '.safetensors', output.name + '.safetensors'}, checkpoint_order(p.name)))
            return dict(mode='weights', path=str(path), label='Continue from checkpoint',
                        message=f'Continue from {path.name} in a new run. The optimizer and learning-rate schedule restart, and the full selected training schedule runs again. Original files and logs are kept.')
        return None

    def template(self, spec):
        if spec['family'] == 'flux1':
            steps, rank = {'quick_test': (600, 16), 'regular': (1200, 32), 'high_quality': (2400, 64)}[spec['profile']]
            return dict(
                **{key: str(self.models / relative) for key, (_, relative) in FLUX_MODELS.items()},
                network_module='networks.lora_flux', network_dim=rank, network_alpha=rank,
                network_train_unet_only=True, learning_rate=0.0001, optimizer_type='AdamW8bit',
                lr_scheduler='constant', train_batch_size=1, max_train_steps=steps,
                mixed_precision='bf16', save_precision='bf16', save_model_as='safetensors',
                save_every_n_steps=200, gradient_checkpointing=True, sdpa=True,
                cache_latents=True, cache_latents_to_disk=True, cache_text_encoder_outputs=True,
                cache_text_encoder_outputs_to_disk=True, blocks_to_swap=18,
                guidance_scale=1.0, timestep_sampling='flux_shift', model_prediction_type='raw',
                seed=31337, max_data_loader_n_workers=2,
            )
        path = self.resolve_config(spec.get('toml_path', ''))
        try:
            return tomllib.loads(path.read_text())
        except (OSError, ValueError):
            raise HTTPException(400, 'Training configuration is missing or invalid TOML')

    def requirements(self, spec, config=None):
        config = config if config is not None else self.template(spec)
        keys = list(FLUX_MODELS) if spec['family'] == 'flux1' else ['pretrained_model_name_or_path', 'vae']
        items = []
        for key in keys:
            raw = config.get(key, '')
            path = under(self.models, Path(raw)) if raw else None
            exists = bool(path and path.is_file() and path.stat().st_size > 0)
            name = FLUX_MODELS[key][0] if spec['family'] == 'flux1' else self.model_name(path) if path else None
            items.append(dict(kind=key, key=key, value=str(path) if path else '', exists=exists,
                              model_name=name, reason=None if exists else 'Required model file is missing'))
        return {'items': items, 'missing': [item for item in items if not item['exists']]}

    def dataset_files(self, dataset):
        files = []
        for base, directories, names in os.walk(dataset, followlinks=False):
            for name in directories + names:
                if (Path(base) / name).is_symlink():
                    raise HTTPException(400, 'Remove symlinks from the dataset before training')
            for name in names:
                path = Path(base) / name
                if path.suffix.lower() in IMAGE_EXTENSIONS | {'.txt', '.caption'}:
                    files.append(under(dataset, path))
        if not any(path.suffix.lower() in IMAGE_EXTENSIONS for path in files):
            raise HTTPException(400, 'The dataset has no supported images')
        return sorted(files)

    def fingerprint(self, dataset, files):
        rows = [(str(p.relative_to(dataset)), p.stat().st_size, p.stat().st_mtime_ns) for p in files]
        return hashlib.sha256(json.dumps(rows).encode()).hexdigest()

    def prepare(self, raw, run_id, directory):
        spec = TrainingRequest(**raw).model_dump()
        dataset = self.resolve_dataset(spec['dataset_name']).resolve()
        spec['dataset_name'] = dataset.name
        files = self.dataset_files(dataset)
        fingerprint = self.fingerprint(dataset, files)
        if raw.get('_expected_fingerprint') and fingerprint != raw['_expected_fingerprint']:
            raise HTTPException(409, 'The dataset changed while preparing recovery. Repeat the original run instead.')
        config = raw.get('_template') or self.template(spec)
        config = dict(config)
        if raw.get('_recovery'):
            for key in ('resume', 'network_weights', 'initial_step', 'initial_epoch', 'skip_until_initial_step'):
                config.pop(key, None)
        requirements = self.requirements(spec, config)
        if requirements['missing']:
            raise HTTPException(400, 'Download the missing training models before adding this run')
        output = under(self.workspace / 'outputs', self.workspace / 'outputs' / f'{spec["output_name"]}-{run_id}')
        output.mkdir(parents=True, exist_ok=False)
        config_text = toml.dumps(config)
        (directory / 'template.toml').write_text(config_text)
        return dict(spec=spec, template=config, output_dir=str(output), dataset=str(dataset),
                    dataset_fingerprint=fingerprint, models=requirements['items'],
                    recovery=raw.get('_recovery'))

    def launch(self, run, stream):
        spec = TrainingRequest(**run['spec']).model_dump()
        directory = under(self.workspace, self.workspace / 'config/training' / run['id'])
        output = under(self.workspace / 'outputs', Path(run['output_dir']))
        dataset = self.resolve_dataset(spec['dataset_name']).resolve()
        files = self.dataset_files(dataset)
        if self.fingerprint(dataset, files) != run['dataset_fingerprint']:
            raise HTTPException(409, 'Dataset changed while queued. Use these settings to create a new run.')
        if self.requirements(spec, run['template'])['missing']:
            raise HTTPException(400, 'A required model was removed while this run was queued')
        size = sum(path.stat().st_size for path in files)
        if shutil.disk_usage(directory).free < size + 1024 ** 3:
            raise HTTPException(400, 'Not enough workspace space for the dataset copy and training output')
        images = under(directory, directory / 'images')
        images.mkdir(exist_ok=True)
        for source in files:
            relative = source.relative_to(dataset)
            target = under(images, images / relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if target.suffix.lower() == '.caption' and not target.with_suffix('.txt').exists():
                shutil.copy2(target, target.with_suffix('.txt'))
        config = dict(run['template'])
        if not config.get('save_every_n_steps'):
            config['save_every_n_steps'] = 200
        config.update(save_state=True, save_last_n_epochs_state=1,
                      save_last_n_steps_state=int(config['save_every_n_steps']))
        recovery = run.get('recovery')
        if recovery:
            original = Path(recovery['path'])
            source = under(self.workspace / 'outputs', original)
            if original.is_symlink():
                raise HTTPException(400, 'Training recovery path must not be a symlink')
            if not source.exists():
                raise HTTPException(409, 'The saved training state or checkpoint was removed. Repeat the original run to start again.')
            if recovery['mode'] == 'state':
                if any(p.is_symlink() for p in source.rglob('*')):
                    raise HTTPException(400, 'Training state must not contain symlinks')
                config.update(resume=str(source), skip_until_initial_step=True)
            else:
                if not complete_checkpoint(source):
                    raise HTTPException(409, 'The saved checkpoint is incomplete or changed. Choose another run.')
                config['network_weights'] = str(source)
        kohya = Path(os.environ.get('KOHYA_ROOT', '/opt/pilot/repos/kohya_ss'))
        python = os.environ.get('TRAINPILOT_PYTHON_BIN', '/opt/venvs/kohya/bin/python')
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['HF_HUB_ENABLE_HF_TRANSFER'] = '0'
        if spec['family'] == 'flux1':
            subsets = sorted({str((images / p.relative_to(dataset)).parent) for p in files if p.suffix.lower() in IMAGE_EXTENSIONS})
            dataset_config = directory / 'dataset.toml'
            dataset_config.write_text(toml.dumps({'datasets': [dict(resolution=1024, batch_size=1, enable_bucket=True,
                subsets=[dict(image_dir=path, num_repeats=1, caption_extension='.txt') for path in subsets])]}))
            config.update(dataset_config=str(dataset_config), output_dir=str(output), output_name=spec['output_name'],
                          logging_dir=str(self.workspace / 'logs/TrainPilot' / output.name), log_with='tensorboard')
            path = directory / 'effective.toml'
            path.write_text(toml.dumps(config))
            script = kohya / 'sd-scripts/flux_train_network.py'
            if not script.is_file():
                raise HTTPException(400, 'Kohya FLUX training script is unavailable in this image')
            command = [python, '-u', str(script), '--config_file', str(path)]
            cwd = kohya
        else:
            # The existing SDXL wrapper applies its reviewed profile to this private copy.
            config.update(train_data_dir=str(directory / 'training-images'))
            path = directory / 'effective.toml'
            path.write_text(toml.dumps(config))
            bundled = Path(__file__).resolve().parents[2] / 'TrainPilot/trainpilot.sh'
            script = Path('/opt/pilot/apps/TrainPilot/trainpilot.sh')
            if not script.exists():
                script = bundled
            env.update(NO_CONFIRM='1', DATASET_NAME=str(images), OUTPUT_NAME=output.name,
                       PROFILE=spec['profile'], TOML=str(path), WORKSPACE_ROOT=str(self.workspace),
                       DATASET_ROOT=str(self.workspace / 'datasets'), OUTS_BASE=str(self.workspace / 'outputs'),
                       IMAGES_DIR=str(directory / 'training-images'), PYTHON_BIN=python)
            command, cwd = [str(script)], script.parent
        return subprocess.Popen(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                env=env, start_new_session=True)
