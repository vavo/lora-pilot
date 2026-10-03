"""Small allowlisted projections over Portal services; no HTTP loopback bypass."""
import base64
import hashlib
import hmac
import io
import json
import stat
import time
from pathlib import Path

from PIL import Image

from .contracts import MUTATIONS, TOOLS
from .files import Files, Rejected, canonical, digest

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
DATA_SUFFIXES = IMAGE_SUFFIXES | {'.txt', '.caption'}


class Facade:
    def __init__(self, store, queue, models, manifest, status=lambda: {}, writes=False):
        self.store, self.queue = store, queue
        self.files = store.files
        self.models, self.manifest = Path(models), Path(manifest)
        self.status = status
        self.writes = writes
        self.execution = None

    def allowed(self, principal, name):
        if name not in TOOLS:
            return False
        if name in MUTATIONS or name.endswith('_plan'):
            if not self.writes:
                return False
        return TOOLS[name][1] <= set(principal['scopes'])

    def call(self, principal_id, name, arguments, cancelled=None):
        self.files.local.cancelled = cancelled
        try:
            principal = self.store.principal(principal_id)
            if not self.allowed(principal, name):
                raise Rejected('NOT_AUTHORIZED')
            payload = TOOLS[name][0].model_validate(arguments).model_dump()
            if name in MUTATIONS or name.endswith('_plan'):
                return self.execution.call(principal, name, payload)
            return getattr(self, name)(principal, **payload)
        finally:
            self.files.local.cancelled = None

    def page(self, principal, kind, items, cursor, limit):
        # Bind cursors to principal, list contents and current grant version.
        stamp = digest([principal['id'], principal['version'], kind, items])
        start = 0
        if cursor is not None:
            try:
                value = json.loads(base64.urlsafe_b64decode(cursor))
                if value['stamp'] != stamp or type(value['offset']) is not int or not 0 <= value['offset'] <= len(items):
                    raise ValueError()
                start = value['offset']
            except (ValueError, KeyError, TypeError):
                raise Rejected('INVALID_INPUT')
        next_cursor = None
        if start + limit < len(items):
            next_cursor = base64.urlsafe_b64encode(canonical(dict(stamp=stamp, offset=start + limit))).decode()
        return dict(items=items[start:start + limit], next_cursor=next_cursor)

    def workspace_status(self, principal):
        # Caller supplies an already projected in-process status, never raw env/process output.
        value = self.status()
        return dict(schema_version=1, mcp_enabled=True, execution_enabled=self.writes,
                    queue_paused=bool(self.queue.paused),
                    gpu_available=value.get('gpu_available'))

    def dataset_path(self, principal, dataset_id):
        name = principal['datasets'].get(dataset_id)
        if not isinstance(name, str) or Path(name).name != name or name in {'', '.', '..'}:
            raise Rejected()
        return 'datasets/' + name

    def datasets_list(self, principal, cursor=None, limit=50):
        items = []
        for key, name in sorted(principal['datasets'].items()):
            try:
                with self.files.directory(self.dataset_path(principal, key)):
                    items.append(dict(dataset_id=key, name=name))
            except (OSError, Rejected):
                pass
        return self.page(principal, 'datasets', items, cursor, limit)

    def dataset_manifest(self, principal, dataset_id, inspect_images=False):
        root = self.dataset_path(principal, dataset_id)
        pending, manifest, seen = [root], [], 0
        total, images, captions, small, empty = 0, 0, set(), 0, 0
        image_stems, hashes = set(), set()
        duplicates = 0
        deadline = time.monotonic() + 30
        while pending:
            directory = pending.pop()
            if len(directory.split('/')) > 16:
                raise Rejected('LIMIT_EXCEEDED')
            for name, info in self.files.listdir(directory):
                seen += 1
                if seen > 5000 or time.monotonic() > deadline:
                    raise Rejected('LIMIT_EXCEEDED')
                relative = directory + '/' + name
                self.files.checkpoint()
                if stat.S_ISDIR(info.st_mode):
                    pending.append(relative)
                    continue
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise Rejected('UNSAFE_FILE')
                suffix = Path(name).suffix.lower()
                if suffix not in DATA_SUFFIXES:
                    continue
                if total + info.st_size > 256 * 1024 ** 2:
                    raise Rejected('LIMIT_EXCEEDED')
                with self.files.open(relative, max_bytes=32 * 1024 ** 2) as source:
                    raw = source.read(32 * 1024 ** 2 + 1)
                total += len(raw)
                if len(raw) > 32 * 1024 ** 2 or total > 256 * 1024 ** 2:
                    raise Rejected('LIMIT_EXCEEDED')
                item = dict(path=relative, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
                manifest.append(item)
                stem = str(Path(relative).with_suffix(''))
                if suffix in IMAGE_SUFFIXES:
                    images += 1
                    image_stems.add(stem)
                    duplicates += item['sha256'] in hashes
                    hashes.add(item['sha256'])
                    if inspect_images:
                        with Image.open(io.BytesIO(raw)) as image:
                            if image.width * image.height > 40_000_000:
                                raise Rejected('LIMIT_EXCEEDED')
                            image.verify()
                            small += min(image.size) < 512
                else:
                    captions.add(stem)
                    empty += not raw.strip()
        manifest.sort(key=lambda row: row['path'])
        return manifest, dict(images=images, complete=True, size_bytes=total,
                              counts=dict(small=small, duplicate=duplicates, empty_caption=empty,
                                          missing_caption=len(image_stems - captions), orphan_caption=len(captions - image_stems)))

    def dataset_review(self, principal, dataset_id):
        _, review = self.dataset_manifest(principal, dataset_id, inspect_images=True)
        return dict(dataset_id=dataset_id, **review)

    def models_list(self, principal, cursor=None, limit=50):
        try:
            from ..services.models import parse_manifest
        except ImportError:
            from services.models import parse_manifest
        catalog = parse_manifest(self.manifest, self.manifest, self.models,
                                 self.files.root / 'config', read_only=True)
        items = [dict(catalog_id=item.name, kind=item.kind, installed=item.installed,
                      size_bytes=item.size_bytes) for item in catalog]
        return self.page(principal, 'models', items, cursor, limit)

    def run(self, principal, run_id):
        if run_id not in principal['runs']:
            raise Rejected()
        data = self.files.json('config/training/' + run_id + '/run.json')
        if data.get('id') != run_id:
            raise Rejected()
        return data

    def checkpoints(self, run):
        output = Path(run['output_dir'])
        try:
            relative = output.relative_to(self.files.root / 'outputs')
        except ValueError:
            raise Rejected()
        if relative.is_absolute() or '..' in relative.parts:
            raise Rejected()
        directory = 'outputs/' + relative.as_posix()
        items = {}
        try:
            for name, info in self.files.listdir(directory):
                if Path(name).suffix != '.safetensors' or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    continue
                identifier = digest([run['id'], name])[:32]
                items[identifier] = dict(path=directory + '/' + name, name=name, size_bytes=info.st_size)
        except FileNotFoundError:
            pass
        return items

    def run_summary(self, run):
        return dict(run_id=run['id'], state=run['status'],
                    name=run['spec']['output_name'], family=run['spec']['family'],
                    created_at=run.get('created_at'), started_at=run.get('started_at'), finished_at=run.get('finished_at'))

    def runs_list(self, principal, cursor=None, limit=50):
        items = []
        for run_id in sorted(principal['runs']):
            try:
                items.append(self.run_summary(self.run(principal, run_id)))
            except (OSError, Rejected):
                pass
        return self.page(principal, 'runs', items, cursor, limit)

    def run_get(self, principal, run_id):
        run = self.run(principal, run_id)
        return dict(**self.run_summary(run), checkpoints=[dict(checkpoint_id=key,
                    name=value['name'], size_bytes=value['size_bytes']) for key, value in self.checkpoints(run).items()])

    def operation_get(self, principal, operation_id):
        op = self.store.operation(principal['id'], operation_id)
        if self.execution:
            op = self.execution.observe(op)
        result = dict(op.get('result', {}))
        if result.get('run_id') not in principal['runs']:
            result.pop('run_id', None)
            result.pop('artifact_id', None)
        if 'artifacts:read' not in principal['scopes']:
            result.pop('artifact_id', None)
            result.pop('download_url', None)
        return dict(schema_version=1, operation_id=op['id'], state=op['state'],
                    result=result, next_poll_after_ms=3000, error=op.get('error'))
