"""Read-only storage inventory and reviewed cleanup of terminal guided-run files."""
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import time
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .gpu_guard import LAUNCH_LOCK
from .training_runs import ACTIVE


class Selection(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=200)


class Confirmation(BaseModel):
    token: str = Field(min_length=32, max_length=64)


def identity(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink]


@contextmanager
def parent_fd(root, relative):
    # Traverse every directory through a descriptor: no symlink can redirect removal.
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(part in {'.', '..'} for part in parts):
        raise HTTPException(409, 'Invalid cleanup path')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd, parts[-1]
    finally:
        os.close(fd)


class Storage:
    def __init__(self, workspace, models, training, downloads, conflicts):
        self.root = Path(workspace).resolve()
        self.models = Path(models).resolve()
        self.training, self.downloads, self.conflicts = training, downloads, conflicts
        self.plans = {}
        self.lock = RLock()

    def inventory(self):
        records, links, warnings, seen = [], [], [], set()
        count = 0
        roots = [('Models', self.models), ('Datasets', self.root / 'datasets'),
                 ('Training snapshots', self.root / 'config/training'), ('Outputs', self.root / 'outputs'),
                 ('Caches', self.root / 'cache')]
        totals = {name: 0 for name, _ in roots}
        def failed(error):
            warnings.append('Some files could not be read. Cleanup is unavailable until the scan is complete.')
        for category, root in roots:
            if root.is_symlink():
                warnings.append(f'{category} is linked; its contents are protected and excluded from totals.')
                continue
            if not root.exists():
                continue
            for directory, dirs, files in os.walk(root, followlinks=False, onerror=failed):
                for name in dirs + files:
                    count += 1
                    if count > 200000:
                        raise HTTPException(409, 'Storage scan exceeds 200,000 entries. Review large folders manually.')
                    path = Path(directory) / name
                    try:
                        info = path.lstat()
                        if stat.S_ISLNK(info.st_mode):
                            if category == 'Models':
                                links.append(path.resolve())
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            continue
                        inode = (info.st_dev, info.st_ino)
                        if inode not in seen:
                            totals[category] += info.st_size
                            seen.add(inode)
                        records.append(dict(path=path, category=category, fingerprint=identity(info),
                                            size_bytes=info.st_size, reclaim_bytes=getattr(info, 'st_blocks', 0) * 512))
                    except OSError as error:
                        failed(error)
        runs = self.training.list()
        candidates = []
        by_run = {}
        for record in records:
            path = record['path']
            if self.models == path or self.models in path.parents:
                continue
            if record['category'] == 'Training snapshots':
                run_id = path.relative_to(self.root / 'config/training').parts[0]
            elif record['category'] == 'Outputs':
                run_id = path.parent.name.rsplit('-', 1)[-1]
            else:
                continue
            by_run.setdefault(run_id, []).append(record)
        for run in runs:
            if run['status'] not in {'succeeded', 'failed', 'stopped', 'cancelled', 'interrupted'} or not re.fullmatch(r'[a-f0-9]{32}', run['id']):
                continue
            history = self.root / 'config/training' / run['id']
            output = self.root / 'outputs' / f'{run["spec"]["output_name"]}-{run["id"]}'
            if str(output) != run['output_dir'] or output.parent != self.root / 'outputs':
                continue
            groups = {}
            for record in by_run.get(run['id'], []):
                path = record['path']
                if record['fingerprint'][-1] != 1 or any(path == link or link in path.parents for link in links):
                    continue
                group = None
                if any(base in path.parents for base in (history / 'images', history / 'training-images')):
                    group = 'Training caches' if path.suffix == '.npz' else 'Dataset snapshot'
                elif path.parent == output and path.suffix == '.safetensors':
                    group = path.name
                if group:
                    groups.setdefault(group, []).append(record)
            for group, files in groups.items():
                key = hashlib.sha256((run['id'] + ':' + group).encode()).hexdigest()
                fingerprint = hashlib.sha256(json.dumps(sorted((str(f['path']), f['fingerprint']) for f in files)).encode()).hexdigest()
                candidates.append(dict(id=key, run_id=run['id'], label=f'{run["spec"]["output_name"]} · {group}',
                    category=group if group in {'Dataset snapshot', 'Training caches'} else 'Checkpoint',
                    file_count=len(files), size_bytes=sum(f['size_bytes'] for f in files),
                    reclaim_bytes=sum(f['reclaim_bytes'] for f in files), fingerprint=fingerprint, files=files))
        disk = shutil.disk_usage(self.root)
        return dict(categories=[dict(name=name, size_bytes=size) for name, size in totals.items()],
                    disk=dict(total=disk.total, free=disk.free, used=disk.used),
                    warnings=list(dict.fromkeys(warnings)), candidates=candidates)

    @staticmethod
    def public_item(item):
        return {key: value for key, value in item.items() if key not in {'files', 'fingerprint'}}

    def check_idle(self):
        if any(run['status'] in ACTIVE for run in self.training.list()):
            raise HTTPException(409, 'Finish or cancel queued and active training before cleanup.')
        if any(job.state in {'running', 'queued'} for job in self.downloads.jobs.values()):
            raise HTTPException(409, 'Wait for model downloads to finish before cleanup.')
        try:
            blocked = self.training.orphan_conflicts() + self.conflicts()
        except Exception:
            raise HTTPException(409, 'Workload status is unavailable. Cleanup is blocked.')
        if blocked:
            raise HTTPException(409, 'Stop active workloads and resolve service status checks before cleanup.')

    def select(self, ids):
        data = self.inventory()
        if data['warnings']:
            raise HTTPException(409, 'The scan is incomplete. Review the storage warnings before cleanup.')
        by_id = {item['id']: item for item in data['candidates']}
        if len(set(ids)) != len(ids) or any(key not in by_id for key in ids):
            raise HTTPException(409, 'The selection changed or contains protected files. Scan again.')
        return [by_id[key] for key in ids]

    def preview(self, ids):
        with self.lock, LAUNCH_LOCK, self.training.lock, self.downloads.lock:
            self.check_idle()
            items = self.select(ids)
            self.plans = {key: value for key, value in self.plans.items() if value['expires'] > time.time()}
            if len(self.plans) >= 20:
                self.plans.pop(next(iter(self.plans)))
            token = secrets.token_hex(24)
            self.plans[token] = dict(expires=time.time() + 300, items=items)
            return dict(token=token, items=[self.public_item(item) for item in items],
                        reclaim_bytes=sum(item['reclaim_bytes'] for item in items),
                        file_count=sum(item['file_count'] for item in items))

    def cleanup(self, token):
        with self.lock, LAUNCH_LOCK, self.training.lock, self.downloads.lock:
            plan = self.plans.pop(token, None)
            if not plan or plan['expires'] < time.time():
                raise HTTPException(409, 'Cleanup preview expired. Review your selection again.')
            self.check_idle()
            items = self.select([item['id'] for item in plan['items']])
            if any(old['fingerprint'] != new['fingerprint'] for old, new in zip(plan['items'], items)):
                raise HTTPException(409, 'Selected files changed after preview. Nothing was removed; scan again.')
            files = [file for item in items for file in item['files']]
            # Validate all selected paths before removing anything.
            try:
                for file in files:
                    with parent_fd(self.root, file['path'].relative_to(self.root)) as (fd, name):
                        if identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != file['fingerprint']:
                            raise OSError('Changed file')
            except OSError:
                raise HTTPException(409, 'Selected files changed. Nothing was removed; scan again.')
            removed, removed_bytes = 0, 0
            for file in files:
                try:
                    with parent_fd(self.root, file['path'].relative_to(self.root)) as (fd, name):
                        if identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != file['fingerprint']:
                            raise OSError('Changed file')
                        os.unlink(name, dir_fd=fd)
                    removed += 1
                    removed_bytes += file['reclaim_bytes']
                except OSError:
                    return dict(removed_files=removed, estimated_reclaimed_bytes=removed_bytes, complete=False,
                                message='Cleanup stopped because a file changed or could not be removed. Scan again to review remaining files.')
            return dict(removed_files=removed, estimated_reclaimed_bytes=removed_bytes, complete=True,
                        message='Selected files removed. Original datasets, shared models and run history were kept.')


def create_router(workspace, models, training, downloads, conflicts):
    router = APIRouter(prefix='/api/storage')
    storage = Storage(workspace, models, training, downloads, conflicts)

    @router.get('')
    def inventory():
        data = storage.inventory()
        data['candidates'] = [storage.public_item(item) for item in data['candidates']]
        return data

    @router.post('/preview')
    def preview(req: Selection):
        return storage.preview(req.ids)

    @router.post('/cleanup')
    def cleanup(req: Confirmation):
        return storage.cleanup(req.token)

    return router
