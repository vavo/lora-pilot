"""Approved, bounded operations using the existing Portal queue and GPU lock."""
import copy
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import threading
import time
import zipfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

from .files import Rejected, canonical, digest
from .store import ROOT
try:
    from ..services import gpu_guard
    from ..services.lora_comparison import ComparisonRequest, comfy, graph, comparison_outputs
    from ..services.training_runs import process_identity
except ImportError:
    from services import gpu_guard
    from services.lora_comparison import ComparisonRequest, comfy, graph, comparison_outputs
    from services.training_runs import process_identity

GIB = 1024 ** 3
TERMINAL = {'succeeded', 'failed', 'stopped', 'cancelled', 'interrupted'}
BASE_MODEL = 'checkpoints/sd_xl_base_1.0.safetensors'


def checkpoint_header(source, size):
    """Inspect format structure only; never deserialize model objects."""
    length = int.from_bytes(source.read(8), 'little')
    if not 2 <= length <= min(16 * 1024 ** 2, size - 8):
        raise Rejected('INVALID_CHECKPOINT')
    raw = source.read(length)
    header = json.loads(raw)
    if not isinstance(header, dict):
        raise Rejected('INVALID_CHECKPOINT')
    ranges = []
    for name, tensor in header.items():
        if name == '__metadata__':
            continue
        if (not isinstance(tensor, dict) or not isinstance(tensor.get('dtype'), str)
                or not isinstance(tensor.get('shape'), list)
                or any(type(n) is not int or n < 0 for n in tensor['shape'])):
            raise Rejected('INVALID_CHECKPOINT')
        offsets = tensor.get('data_offsets')
        if (not isinstance(offsets, list) or len(offsets) != 2
                or any(type(n) is not int for n in offsets)
                or not 0 <= offsets[0] <= offsets[1] <= size - 8 - length):
            raise Rejected('INVALID_CHECKPOINT')
        ranges.append(offsets)
    end = 0
    for start, finish in sorted(ranges):
        if start != end:
            raise Rejected('INVALID_CHECKPOINT')
        end = finish
    if not ranges or end != size - 8 - length:
        raise Rejected('INVALID_CHECKPOINT')
    return header, raw


class Execution:
    def __init__(self, facade, budget_bytes, provider=comfy):
        self.facade, self.store, self.files = facade, facade.store, facade.files
        self.queue, self.provider = facade.queue, provider
        self.budget = budget_bytes
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='mcp-preparation')
        self.lock = threading.Lock()
        self.closed = False
        self.started = {}
        self.queue.mcp_authorize = self.authorize_run
        self.queue.mcp_launch = self.launch
        self.queue.mcp_monitor = self.monitor
        self.queue.mcp_conflicts = gpu_guard.conflicts
        facade.execution = self

    def close(self):
        self.closed = True
        self.pool.shutdown(wait=True, cancel_futures=True)

    def capacity(self, requested, own_id=None):
        if not self.budget or requested < 0:
            raise Rejected('CAPACITY_UNKNOWN')
        data = self.store.read()
        reserved = sum(op['payload'].get('allocation_bytes', 0) for op in data['operations'].values() if op['id'] != own_id)
        if reserved + requested > self.budget or shutil.disk_usage(self.files.root).free < requested + GIB:
            raise Rejected('LIMIT_EXCEEDED')

    def call(self, principal, name, request):
        if self.closed or self.store.owner is None:
            raise Rejected('UNAVAILABLE')
        if name.endswith('_plan'):
            return getattr(self, name)(principal, request)
        if name == 'run_cancel':
            self.facade.run(principal, request['run_id'])
        scope = {'training_start': 'training:submit', 'run_cancel': 'training:cancel',
                 'comparison_start': 'comparison:submit', 'export_create': 'artifacts:export'}[name]
        # Serialize capacity reservations with acceptance, but never hold this lock in the queue worker.
        with self.lock:
            if name != 'run_cancel':
                data = self.store.read()
                plan = data['plans'].get(request['plan_id'])
                key = digest([data['workspace_id'], principal['id'], request['request_id']])
                if key not in data['operations'] and plan and plan['principal'] == principal['id']:
                    self.capacity(plan['payload'].get('allocation_bytes', 0))
            op, created = self.store.accept(principal['id'], name, request, scope)
            if created:
                self.pool.submit(self.execute, op)
        return self.facade.operation_get(principal, op['id'])

    def training_plan(self, principal, request):
        manifest, review = self.facade.dataset_manifest(principal, request['dataset_id'], inspect_images=True)
        if not review['images']:
            raise Rejected('INVALID_INPUT')
        # Only this bundled recipe and base-model location are executable in v1.
        model_relative = (self.facade.models / BASE_MODEL).relative_to(self.files.root).as_posix()
        model = dict(path=model_relative, **self.files.digest(model_relative))
        allocation = 4 * GIB + review['size_bytes']
        self.capacity(allocation)
        payload = dict(request, manifest=manifest, model=model, allocation_bytes=allocation, recipe_version=1)
        return self.store.plan(principal['id'], 'training', payload, dict(
            dataset=self.facade.dataset_path(principal, request['dataset_id']).split('/', 1)[1],
            image_count=review['images'], family='sdxl', profile='quick_test',
            max_steps=request['max_steps'], max_seconds=request['max_seconds'],
            output_name=request['output_name'], reserved_bytes=allocation, base_model='sdxl-base'))

    def selected_checkpoint(self, principal, request):
        run = self.facade.run(principal, request['run_id'])
        if run['status'] not in TERMINAL or run['spec']['family'] != 'sdxl':
            raise Rejected('CONFLICT')
        checkpoint = self.facade.checkpoints(run).get(request['checkpoint_id'])
        if not checkpoint:
            raise Rejected()
        checkpoint = dict(checkpoint, **self.files.digest(checkpoint['path']))
        # Parse the bounded safetensors header without unpickling anything.
        with self.files.open(checkpoint['path']) as source:
            checkpoint_header(source, checkpoint['size_bytes'])
        return run, checkpoint

    def comparison_plan(self, principal, request):
        run, checkpoint = self.selected_checkpoint(principal, request)
        # Existing arbitrary UI templates are not promoted into trusted MCP graphs.
        if not run.get('mcp_recipe') or run['mcp_recipe'].get('version') != 1:
            raise Rejected('UNAPPROVED_RECIPE')
        allocation = checkpoint['size_bytes'] + 256 * 1024 ** 2
        self.capacity(allocation)
        return self.store.plan(principal['id'], 'comparison', dict(request, checkpoint=checkpoint,
            model=run['mcp_recipe']['model'], allocation_bytes=allocation),
            dict(run_id=run['id'], checkpoint=checkpoint['name'], prompt=request['prompt'],
                 seed=request['seed'], strength=request['strength'], images=2, steps=20, reserved_bytes=allocation))

    def export_plan(self, principal, request):
        run, checkpoint = self.selected_checkpoint(principal, request)
        images = []
        if request['images']:
            if not request['comparison_id'] or len(set(request['images'])) != len(request['images']):
                raise Rejected('INVALID_INPUT')
            comparison = self.observe(self.store.operation(principal['id'], request['comparison_id']))
            if comparison['tool'] != 'comparison_start' or comparison['state'] != 'succeeded' or comparison['payload']['run_id'] != run['id']:
                raise Rejected()
            available = comparison.get('images', [])
            for index in request['images']:
                if type(index) is not int or not 0 <= index < len(available):
                    raise Rejected('INVALID_INPUT')
                item = available[index]
                images.append(dict(path=item['path'], **self.files.digest(item['path'], max_bytes=32 * 1024 ** 2)))
        allocation = checkpoint['size_bytes'] * 2 + 256 * 1024 ** 2 + sum(item['size_bytes'] for item in images) * 2
        self.capacity(allocation)
        return self.store.plan(principal['id'], 'export', dict(request, checkpoint=checkpoint, selected_images=images, allocation_bytes=allocation),
            dict(run_id=run['id'], files=[checkpoint['name'], 'experiment.json', 'README.md', *[f'samples/{i}.png' for i in range(len(images))]],
                 sample_prompt=request['sample_prompt'], reserved_bytes=allocation,
                 disclosure='This sends trained weights and selected text to the client. A LoRA may retain training information. Original datasets, logs and optimizer state are excluded.'))

    def check_dispatch(self, op):
        data = self.store.read()
        principal = self.store.principal(op['principal'], data)
        if data['generation'] != op['generation'] or principal['version'] != op['grant_version']:
            raise Rejected('NOT_AUTHORIZED')
        return principal

    def execute(self, op):
        try:
            self.check_dispatch(op)
            if op['tool'] == 'training_start':
                self.prepare_training(op)
            elif op['tool'] == 'comparison_start':
                self.compare(op)
            elif op['tool'] == 'export_create':
                self.export(op)
            else:
                self.cancel(op)
        except Exception as error:
            # Once dispatching, absence of a reply is not proof of absence of an effect.
            code = error.code if isinstance(error, Rejected) else 'UNAVAILABLE'
            try:
                current = next(item for item in self.store.read()['operations'].values() if item['id'] == op['id'])
                self.store.update_operation(op['id'], state='failed' if current['state'] == 'accepted' else 'unknown', error=code)
            except Exception:
                pass  # Durable dispatching record becomes unknown during startup reconciliation.

    def prepare_training(self, op):
        payload = op['payload']
        principal = self.check_dispatch(op)
        manifest, _ = self.facade.dataset_manifest(principal, payload['dataset_id'], inspect_images=True)
        if manifest != payload['manifest']:
            raise Rejected('PLAN_STALE')
        self.capacity(payload['allocation_bytes'], op['id'])
        directory = ROOT + '/jobs/' + op['id']
        self.files.new_directory(directory)
        dataset_root = self.facade.dataset_path(principal, payload['dataset_id'])
        snapshot = directory + '/images'
        copied = []
        for item in manifest:
            relative = item['path'][len(dataset_root) + 1:]
            target = snapshot + '/' + relative
            self.files.copy_verified(item['path'], target, item)
            copied.append(dict(item, path=target))
        copied_paths = {item['path'] for item in copied}
        for item in list(copied):
            converted = str(Path(item['path']).with_suffix('.txt'))
            if item['path'].endswith('.caption') and converted not in copied_paths:
                self.files.copy_verified(item['path'], converted, item)
                copied.append(dict(item, path=converted))
        # Re-read membership/content after the copy; a mixed unapproved snapshot never dispatches.
        if self.facade.dataset_manifest(principal, payload['dataset_id'])[0] != manifest:
            raise Rejected('PLAN_STALE')
        if self.files.digest(payload['model']['path']) != {key: payload['model'][key] for key in ('sha256', 'size_bytes')}:
            raise Rejected('PLAN_STALE')
        output_relative = 'outputs/mcp-' + op['id']
        self.files.new_directory(output_relative)
        config = dict(pretrained_model_name_or_path=str(self.files.root / payload['model']['path']),
            network_module='networks.lora', network_dim=16, network_alpha=16, network_train_unet_only=True,
            learning_rate=0.0001, optimizer_type='AdamW', lr_scheduler='constant',
            train_batch_size=1, gradient_accumulation_steps=1, max_train_steps=payload['max_steps'],
            mixed_precision='bf16', save_precision='bf16', save_model_as='safetensors',
            save_every_n_steps=100, gradient_checkpointing=True, sdpa=True, seed=31337,
            max_data_loader_n_workers=0, output_dir=str(self.files.root / output_relative),
            output_name=payload['output_name'], save_state=False)
        subsets = sorted({str((self.files.root / item['path']).parent) for item in copied
                          if Path(item['path']).suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}})
        dataset = {'datasets': [dict(resolution=1024, batch_size=1, enable_bucket=True,
            subsets=[dict(image_dir=path, num_repeats=1, caption_extension='.txt') for path in subsets])]}
        import toml
        self.files.write(directory + '/dataset.toml', toml.dumps(dataset).encode())
        config['dataset_config'] = str(self.files.root / directory / 'dataset.toml')
        self.files.write(directory + '/effective.toml', toml.dumps(config).encode())
        configs = [dict(path=directory + '/' + name, **self.files.digest(directory + '/' + name))
                   for name in ('effective.toml', 'dataset.toml')]
        prepared = dict(spec={key: payload[key] for key in ('output_name', 'family', 'profile')},
            template=config, output_dir=str(self.files.root / output_relative), dataset=str(self.files.root / snapshot),
            dataset_fingerprint=digest(manifest), models=[],
            mcp_recipe=dict(version=1, principal=op['principal'], model=payload['model'],
                snapshot=copied, configs=configs, directory=directory,
                max_seconds=payload['max_seconds'], allocation_bytes=payload['allocation_bytes']))
        prepared['spec'].update(dataset_name=self.facade.dataset_path(principal, payload['dataset_id']).split('/', 1)[1], hardware={})
        with gpu_guard.LAUNCH_LOCK:
            self.check_dispatch(op)
            self.store.update_operation(op['id'], state='dispatching', prepared_digest=digest(prepared))
            self.queue.start()
            with self.files.directory('config/training', private=False):
                pass
            run = self.queue.submit({}, run_id=op['id'], origin_operation_id=op['id'], prepared=prepared)
            with self.store.transaction(control=True) as data:
                client = self.store.principal(op['principal'], data)
                if run['id'] not in client['runs']:
                    client['runs'].append(run['id'])
            self.store.update_operation(op['id'], state='running', result=dict(run_id=run['id']))

    def authorize_run(self, run):
        try:
            op = self.store.operation(run['mcp_recipe']['principal'], run['origin_operation_id'])
            self.check_dispatch(op)
            prepared = {key: run[key] for key in ('spec', 'template', 'output_dir', 'dataset',
                        'dataset_fingerprint', 'models', 'mcp_recipe')}
            return (not self.closed and op['state'] in {'dispatching', 'running'} and op['id'] == run['id']
                    and digest(prepared) == op.get('prepared_digest'))
        except Exception:
            return False

    def launch(self, run, stream):
        # Called under the existing queue/GPU lock; no source copying or network calls here.
        if not self.authorize_run(run):
            raise Rejected('NOT_AUTHORIZED')
        recipe = run['mcp_recipe']
        op = self.store.operation(recipe['principal'], run['origin_operation_id'])
        principal = self.check_dispatch(op)
        if self.facade.dataset_manifest(principal, op['payload']['dataset_id'])[0] != op['payload']['manifest']:
            raise Rejected('PLAN_STALE')
        for item in [*recipe['snapshot'], *recipe['configs']]:
            if self.files.digest(item['path']) != {key: item[key] for key in ('sha256', 'size_bytes')}:
                raise Rejected('PLAN_STALE')
        # Models are trusted owner-installed files. Reject replacement at launch.
        model = recipe['model']
        if self.files.digest(model['path']) != {key: model[key] for key in ('sha256', 'size_bytes')}:
            raise Rejected('PLAN_STALE')
        path = self.files.root / recipe['directory'] / 'effective.toml'
        script = Path(os.environ.get('KOHYA_ROOT', '/opt/pilot/repos/kohya_ss')) / 'sd-scripts/sdxl_train_network.py'
        if not script.is_file():
            raise Rejected('TRAINER_UNAVAILABLE')
        # The trusted backend owns the command and environment, never the caller.
        env = {key: value for key, value in os.environ.items() if key in
               {'PATH', 'HOME', 'LD_LIBRARY_PATH', 'CUDA_VISIBLE_DEVICES', 'NVIDIA_VISIBLE_DEVICES', 'LANG'}}
        env.update(PYTHONUNBUFFERED='1', HF_HUB_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', WANDB_DISABLED='true')
        proc = subprocess.Popen([os.environ.get('TRAINPILOT_PYTHON_BIN', '/opt/venvs/kohya/bin/python'),
            '-u', str(script), '--config_file', str(path)], cwd=script.parent, env=env,
            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        self.started[run['id']] = time.monotonic()
        return proc

    def monitor(self, run, proc):
        recipe = run['mcp_recipe']
        elapsed = time.monotonic() - self.started.get(run['id'], 0)
        used, pending, visited = 0, [Path(run['output_dir']).relative_to(self.files.root).as_posix()], 0
        while pending:
            path = pending.pop()
            for name, info in self.files.listdir(path):
                visited += 1
                if visited > 5000 or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                    used = recipe['allocation_bytes']
                    pending.clear()
                    break
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path + '/' + name)
                else:
                    used += info.st_size
        if elapsed <= recipe['max_seconds'] and used < recipe['allocation_bytes'] - GIB and shutil.disk_usage(self.files.root).free >= GIB:
            return
        if not run.get('process_identity') or process_identity(proc.pid) != run['process_identity']:
            raise Rejected('PROCESS_IDENTITY_UNAVAILABLE')
        run['status'] = 'stopping'
        self.queue._terminate(proc)

    def cancel(self, op):
        with gpu_guard.LAUNCH_LOCK, self.queue.lock:
            principal = self.check_dispatch(op)
            run = self.facade.run(principal, op['payload']['run_id'])
            if run['status'] not in TERMINAL:
                if run['status'] != 'queued' and (not run.get('process_identity') or process_identity(run.get('pid')) != run['process_identity']):
                    raise Rejected('PROCESS_IDENTITY_UNAVAILABLE')
                self.store.update_operation(op['id'], state='dispatching')
                self.queue.cancel(run['id'])
            self.store.update_operation(op['id'], state='succeeded', result=dict(run_id=run['id']))

    def compare(self, op):
        payload = op['payload']
        principal = self.check_dispatch(op)
        run, checkpoint = self.selected_checkpoint(principal, payload)
        if checkpoint != payload['checkpoint']:
            raise Rejected('PLAN_STALE')
        if self.files.digest(payload['model']['path']) != {key: payload['model'][key] for key in ('sha256', 'size_bytes')}:
            raise Rejected('PLAN_STALE')
        self.capacity(payload['allocation_bytes'], op['id'])
        destination = (self.facade.models / 'loras/ControlPilot-MCP' / op['id'] / checkpoint['name']).relative_to(self.files.root).as_posix()
        self.files.new_directory(str(Path(destination).parent))
        self.files.copy_verified(checkpoint['path'], destination, checkpoint)
        registry = self.provider('GET', 'object_info')
        safe_run = dict(id=op['id'], spec={'family': 'sdxl'},
                        template={'pretrained_model_name_or_path': str(self.files.root / payload['model']['path'])})
        request = ComparisonRequest(artifact=checkpoint['name'], prompt=payload['prompt'], seed=payload['seed'], strength=payload['strength'])
        workflow = graph(safe_run, request, 'ControlPilot-MCP/' + op['id'] + '/' + checkpoint['name'], registry)
        with gpu_guard.LAUNCH_LOCK:
            self.check_dispatch(op)
            if gpu_guard.managed_conflicts() or gpu_guard.conflicts():
                raise Rejected('CONFLICT')
            self.store.update_operation(op['id'], state='dispatching')
            result = self.provider('POST', 'prompt', json={'prompt': workflow, 'client_id': 'mcp-' + op['id']})
            if (not isinstance(result.get('prompt_id'), str) or result.get('node_errors')
                    or str(uuid.UUID(result['prompt_id'])) != result['prompt_id']):
                raise Rejected('OUTCOME_UNKNOWN')
            self.store.update_operation(op['id'], state='running', provider_id=result['prompt_id'],
                result=dict(run_id=run['id']), outputs=comparison_outputs(workflow))

    def export(self, op):
        payload = op['payload']
        principal = self.check_dispatch(op)
        run, checkpoint = self.selected_checkpoint(principal, payload)
        if checkpoint != payload['checkpoint']:
            raise Rejected('PLAN_STALE')
        self.capacity(payload['allocation_bytes'], op['id'])
        directory = ROOT + '/jobs/' + op['id']
        self.files.new_directory(directory)
        source = directory + '/checkpoint.safetensors'
        self.files.copy_verified(checkpoint['path'], source, checkpoint)
        samples = []
        for index, item in enumerate(payload['selected_images']):
            path = directory + f'/sample-{index}'
            self.files.copy_verified(item['path'], path, item)
            samples.append(path)
        metadata = dict(format_version=1, name=run['spec']['output_name'], family='sdxl',
                        checkpoint='checkpoint/LoRA.safetensors', sample_prompt=payload['sample_prompt'])
        # New archive inode, never an existing user destination.
        with self.files.directory(directory, private=True) as fd:
            raw = os.open('experiment.zip', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            with os.fdopen(raw, 'wb') as target:
                with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as archive:
                    archive.writestr('experiment.json', json.dumps(metadata))
                    archive.writestr('README.md', 'This package contains selected trained weights and text. Original datasets, logs and optimizer state are excluded. A LoRA may retain training information.\n')
                    for index, path in enumerate(samples):
                        with self.files.open(path, max_bytes=32 * 1024 ** 2) as stream, Image.open(stream) as image:
                            if image.width * image.height > 40_000_000:
                                raise Rejected('LIMIT_EXCEEDED')
                            pixels = image.convert('RGB')
                            pixels.info.clear()
                            buffer = io.BytesIO()
                            pixels.save(buffer, 'PNG')
                            archive.writestr(f'samples/{index}.png', buffer.getvalue())
                    with archive.open('checkpoint/LoRA.safetensors', 'w', force_zip64=True) as entry, self.files.open(source) as stream:
                        header, raw = checkpoint_header(stream, checkpoint['size_bytes'])
                        if '__metadata__' in header:
                            # Trainer metadata can contain dataset names, paths and full training settings.
                            del header['__metadata__']
                            raw = canonical(header)
                            raw += b' ' * (-len(raw) % 8)
                        entry.write(len(raw).to_bytes(8, 'little'))
                        entry.write(raw)
                        shutil.copyfileobj(stream, entry, length=1024 * 1024)
                target.flush()
                os.fsync(target.fileno())
            os.fsync(fd)
        archive_path = directory + '/experiment.zip'
        verified = self.files.digest(archive_path)
        with gpu_guard.LAUNCH_LOCK:
            self.check_dispatch(op)
            self.store.update_operation(op['id'], state='succeeded', artifact=dict(path=archive_path,
                **verified, expires_at=self.store.clock() + 86400),
                result=dict(run_id=run['id'], artifact_id=op['id']))

    def observe(self, op):
        if op['tool'] == 'training_start' and op['state'] in {'running', 'unknown'}:
            try:
                run = self.files.json('config/training/' + op['id'] + '/run.json')
                if run.get('origin_operation_id') != op['id']:
                    return op
                if run['status'] in TERMINAL:
                    state = 'succeeded' if run['status'] == 'succeeded' else 'cancelled' if run['status'] in {'stopped', 'cancelled'} else 'failed'
                    return self.store.update_operation(op['id'], state=state, result={'run_id': run['id']})
            except (OSError, ValueError, Rejected):
                pass
        if op['tool'] == 'comparison_start' and op['state'] == 'running':
            try:
                history = self.provider('GET', 'history/' + op['provider_id']).get(op['provider_id'])
                if not history:
                    jobs = self.provider('GET', 'queue')
                    ids = {item[1] for group in ('queue_running', 'queue_pending') for item in jobs.get(group, [])}
                    if op['provider_id'] not in ids:
                        return self.store.update_operation(op['id'], state='unknown', error='OUTCOME_UNKNOWN')
                elif history.get('status', {}).get('status_str') == 'error':
                    return self.store.update_operation(op['id'], state='failed', error='GENERATION_FAILED')
                elif history.get('status', {}).get('completed'):
                    images = []
                    for output in op['outputs']:
                        result = history.get('outputs', {}).get(output['node_id'], {}).get('images', [])
                        if len(result) != 1:
                            raise Rejected('OUTCOME_UNKNOWN')
                        item = result[0]
                        if (item.get('subfolder') != 'LoRA-Pilot/' + op['id'] or item.get('type') != 'output'
                                or not isinstance(item.get('filename'), str) or Path(item['filename']).name != item['filename']
                                or Path(item['filename']).suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}):
                            raise Rejected('OUTCOME_UNKNOWN')
                        path = 'outputs/comfy/' + item['subfolder'] + '/' + item['filename']
                        with self.files.open(path, max_bytes=32 * 1024 ** 2):
                            pass
                        images.append(dict(path=path, label=output['label']))
                    return self.store.update_operation(op['id'], state='succeeded', images=images,
                        result=dict(run_id=op['payload']['run_id'], comparison_id=op['id'], image_count=len(images)))
            except Exception:
                # Observation cannot authorize another dispatch, including on provider outages.
                return op
        return op
