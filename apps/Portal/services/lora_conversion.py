"""Prepare ComfyUI copies with the converters bundled in the Kohya venv."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from fastapi import HTTPException

from .guided_training import complete_checkpoint
from .training_runs import under


def comparison_loras(models, run, names):
    module = {'anima': 'convert_anima_lora_to_comfy',
              'hunyuan_image21': 'convert_hunyuan_image_lora_to_comfy'}.get(run['spec']['family'])
    if not module:
        return names
    scripts = Path(os.environ.get('KOHYA_ROOT', '/opt/pilot/repos/kohya_ss')) / 'sd-scripts'
    converter = scripts / 'networks' / (module + '.py')
    if not converter.is_file():
        raise HTTPException(503, 'The Kohya LoRA conversion tool is missing. Check the installed Kohya version.')
    root = under(models, Path(models) / 'loras')
    cache = under(root, root / 'ControlPilot' / run['id'] / 'comfy')
    cache.mkdir(parents=True, exist_ok=True)
    tool_hash = hashlib.sha256(module.encode() + b'\0' + converter.read_bytes()).digest()
    targets, pending = [], []
    for name in names:
        source = under(root, root / name)
        with source.open('rb') as stream:
            digest = hashlib.sha256(tool_hash + hashlib.file_digest(stream, 'sha256').digest()).hexdigest()
        target = cache / digest / source.name
        if target.is_symlink():
            raise HTTPException(409, 'A converted LoRA destination is a symbolic link. Check the LoRA library.')
        target = under(root, target)
        targets.append(target.relative_to(root).as_posix())
        if target.exists():
            if not complete_checkpoint(target):
                raise HTTPException(409, 'A converted LoRA is incomplete. Remove that comparison copy and prepare it again.')
        else:
            pending.append((source, target))
    if not pending:
        return targets
    if shutil.disk_usage(cache).free < sum(source.stat().st_size for source, _ in pending) + 256 * 1024 ** 2:
        raise HTTPException(400, 'Not enough storage to create ComfyUI copies of the selected checkpoints.')
    # One interpreter for the batch; each source remains untouched.
    with tempfile.TemporaryDirectory(prefix='.conversion-', dir=cache) as temporary:
        pairs = [(str(source), str(Path(temporary) / f'{index}.partial'))
                 for index, (source, _) in enumerate(pending)]
        code = ('import json,sys\nfrom types import SimpleNamespace\n'
                f'from networks.{module} import main\n'
                'for source,target in json.loads(sys.argv[1]):\n'
                ' main(SimpleNamespace(src_path=source,dst_path=target,reverse=False))\n')
        try:
            subprocess.run([os.environ.get('TRAINPILOT_PYTHON_BIN', '/opt/venvs/kohya/bin/python'),
                            '-c', code, json.dumps(pairs)], cwd=scripts, check=True,
                           capture_output=True, timeout=180)
        except (OSError, subprocess.SubprocessError):
            raise HTTPException(503, 'Kohya could not convert these checkpoints. Check its installation and try a single checkpoint.') from None
        if any(not complete_checkpoint(Path(destination)) for _, destination in pairs):
            raise HTTPException(503, 'Kohya returned an incomplete comparison checkpoint. Original checkpoints are unchanged.')
        for (_, destination), (_, target) in zip(pairs, pending):
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(destination, target)
            except FileExistsError:
                raise HTTPException(409, 'A converted checkpoint already exists. Refresh the run before trying again.') from None
    return targets
