"""Portable experiment packages built from an explicit file and settings allowlist."""
import io
import hashlib
import json
import os
import shutil
import stat
import tempfile
import tomllib
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi import HTTPException
from PIL import Image
from pydantic import BaseModel, Field

from .training_runs import under

SETTING_KEYS = {'network_dim', 'network_alpha', 'conv_dim', 'conv_alpha', 'network_dropout',
                'learning_rate', 'learning_rate_te', 'learning_rate_te1', 'learning_rate_te2',
                'train_batch_size', 'gradient_accumulation_steps', 'max_train_steps', 'max_train_epochs',
                'gradient_checkpointing', 'cache_latents', 'cache_text_encoder_outputs', 'blocks_to_swap',
                'seed', 'resolution', 'mixed_precision', 'save_precision', 'optimizer_type',
                'lr_scheduler', 'network_module', 'max_token_length'}


class ExportRequest(BaseModel):
    artifact: str = Field(min_length=1, max_length=255)
    trigger_words: str = Field(default='', max_length=500)
    sample_prompt: str = Field(default='', max_length=4000)
    images: list[int] = Field(default_factory=list, max_length=65)


def regular_file(root, path):
    for component in [path, *path.parents]:
        if component.is_symlink():
            raise HTTPException(400, 'Export files must not be symbolic links')
        if component == root:
            break
    path = under(root, path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise HTTPException(400, 'Export requires a regular file')
        return os.fdopen(fd, 'rb')
    except OSError:
        raise HTTPException(409, 'An export file is no longer available. Preview again.')


def portable_settings(run, directory):
    config = run['template']
    output = Path(run['output_dir'])
    path = output / f'{output.name}.toml' if run['spec']['family'] == 'sdxl' else directory / 'effective.toml'
    if path.exists():
        with regular_file(output if run['spec']['family'] == 'sdxl' else directory, path) as source:
            try:
                config = tomllib.loads(source.read(1024 * 1024).decode())
            except (ValueError, UnicodeError):
                raise HTTPException(409, 'The saved training settings cannot be read. Check the run configuration.')
    return {key: value for key, value in config.items() if key in SETTING_KEYS
            and isinstance(value, (int, float, bool, str))
            and (not isinstance(value, str) or (len(value) <= 100 and '/' not in value and '\\' not in value))}


def export_plan(workspace, models, directory, run, paths, request, comparison):
    if run['status'] in {'queued', 'running', 'stopping'}:
        raise HTTPException(409, 'Wait for training to stop before exporting')
    if request.artifact not in paths:
        raise HTTPException(404, 'Checkpoint not found')
    checkpoint = paths[request.artifact]
    root = models if checkpoint.is_relative_to(models) else workspace / 'outputs'
    with regular_file(root, checkpoint) as source:
        size = os.fstat(source.fileno()).st_size
    files = [(root, checkpoint, 'checkpoint/' + checkpoint.name, size)]
    available = comparison.get('images', [])
    for index in sorted(set(request.images)):
        if not 0 <= index < len(available):
            raise HTTPException(400, 'Comparison selection changed. Preview again.')
        url = urlsplit(available[index]['url'])
        query = parse_qs(url.query)
        folder = query.get('subfolder', [''])[0]
        filename = query.get('filename', [''])[0]
        if (url.scheme or url.netloc or url.path != '/proxy/comfy/view'
                or folder != f'LoRA-Pilot/{run["id"]}' or Path(filename).name != filename
                or Path(filename).suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}):
            raise HTTPException(400, 'Comparison image does not belong to this run')
        root = workspace / 'outputs/comfy'
        path = root / folder / filename
        with regular_file(root, path) as source:
            size = os.fstat(source.fileno()).st_size
        if size > 32 * 1024 ** 2:
            raise HTTPException(413, 'Comparison image is too large to export')
        files.append((root, path, f'samples/{index:02d}.png', size))
    metadata = dict(format_version=1, name=run['spec']['output_name'], family=run['spec']['family'],
                    profile=run['spec']['profile'], checkpoint='checkpoint/' + checkpoint.name,
                    trigger_words=request.trigger_words, sample_prompt=request.sample_prompt,
                    settings=portable_settings(run, directory),
                    model_requirements=[dict(kind=item['kind'], filename=Path(item['value']).name,
                                             catalog_id=item.get('model_name')) for item in run.get('models', [])],
                    samples=[dict(file=f'samples/{index:02d}.png', label=available[index]['label'])
                             for index in sorted(set(request.images))])
    if request.images:
        metadata['comparison'] = {key: comparison.get('request', {}).get(key)
                                  for key in ('prompt', 'seed', 'strength')}
    return files, metadata


def build_archive(directory, files, metadata):
    size = sum(item[3] for item in files)
    if shutil.disk_usage(directory).free < size + 256 * 1024 ** 2:
        raise HTTPException(400, 'Not enough workspace space to prepare this export')
    archive = tempfile.TemporaryFile(dir=directory)
    try:
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as output:
            output.writestr('experiment.json', json.dumps(metadata, indent=2))
            output.writestr('README.md', '# ' + metadata['name'] + '\n\n'
                'Place the checkpoint in your LoRA library and use the base model listed in experiment.json. '
                'Use the recorded trigger words in your prompt. Model weights are not included.\n\n'
                'experiment.json contains selected training settings and sample prompts. Dataset files, '
                'credentials, logs and local paths are excluded. Sample image metadata is removed. '
                'This package is for using and reproducing the experiment, not resuming optimizer state.\n')
            for root, path, name, expected_size in files:
                with regular_file(root, path) as source:
                    before = os.fstat(source.fileno())
                    if before.st_size != expected_size:
                        raise HTTPException(409, 'An export file changed. Preview again.')
                    if name.startswith('samples/'):
                        with Image.open(source) as image:
                            if image.width * image.height > 40_000_000:
                                raise HTTPException(413, 'Comparison image is too large')
                            pixels = image.convert('RGB')
                            pixels.info.clear()
                            buffer = io.BytesIO()
                            pixels.save(buffer, 'PNG')
                            output.writestr(name, buffer.getvalue())
                    else:
                        with output.open(name, 'w', force_zip64=True) as target:
                            shutil.copyfileobj(source, target, length=1024 * 1024)
                    after = os.fstat(source.fileno())
                    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                        raise HTTPException(409, 'An export file changed. Preview again.')
        archive.seek(0)
        return archive
    except Exception:
        archive.close()
        raise


def preview_token(files, metadata):
    stamps = [(name, size, path.stat().st_mtime_ns) for _, path, name, size in files]
    return hashlib.sha256(json.dumps([stamps, metadata], sort_keys=True).encode()).hexdigest()
