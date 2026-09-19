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

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
FLUX_MODELS = {
    'pretrained_model_name_or_path': ('flux1-dev', 'diffusion_models/flux1-dev.safetensors'),
    'ae': ('flux1-ae', 'vae/ae.safetensors'),
    'clip_l': ('flux-clip-l', 'text_encoders/clip_l.safetensors'),
    't5xxl': ('flux-t5xxl-fp16', 'text_encoders/t5xxl_fp16.safetensors'),
}


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
        config = raw.get('_template') or self.template(spec)
        requirements = self.requirements(spec, config)
        if requirements['missing']:
            raise HTTPException(400, 'Download the missing training models before adding this run')
        output = under(self.workspace / 'outputs', self.workspace / 'outputs' / f'{spec["output_name"]}-{run_id}')
        output.mkdir(parents=True, exist_ok=False)
        config_text = toml.dumps(config)
        (directory / 'template.toml').write_text(config_text)
        return dict(spec=spec, template=config, output_dir=str(output), dataset=str(dataset),
                    dataset_fingerprint=self.fingerprint(dataset, files), models=requirements['items'])

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
        kohya = Path(os.environ.get('KOHYA_ROOT', '/opt/pilot/repos/kohya_ss'))
        python = os.environ.get('TRAINPILOT_PYTHON_BIN', '/opt/venvs/kohya/bin/python')
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        if spec['family'] == 'flux1':
            subsets = sorted({str((images / p.relative_to(dataset)).parent) for p in files if p.suffix.lower() in IMAGE_EXTENSIONS})
            dataset_config = directory / 'dataset.toml'
            dataset_config.write_text(toml.dumps({'datasets': [dict(resolution=1024, batch_size=1, enable_bucket=True,
                subsets=[dict(image_dir=path, num_repeats=1, caption_extension='.txt') for path in subsets])]}))
            config.update(dataset_config=str(dataset_config), output_dir=str(output), output_name=spec['output_name'],
                          logging_dir=str(output / '_logs'), log_with='tensorboard')
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
