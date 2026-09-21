"""Keep shared filesystem statistics separate from a workspace allocation."""
import math
import os
import re
from pathlib import Path


def shared_workspace(path):
    path = Path(path).resolve()
    mounts = []
    try:
        for line in Path('/proc/self/mountinfo').read_text().splitlines():
            before, after = line.split(' - ', 1)
            fields, device = before.split(), after.split()
            mount = Path(re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), fields[4]))
            if mount == path or mount in path.parents:
                mounts.append((len(mount.parts), fields[3], device[0], device[1]))
    except (OSError, ValueError, IndexError):
        return bool(os.environ.get('RUNPOD_POD_ID'))
    if not mounts:
        return bool(os.environ.get('RUNPOD_POD_ID'))
    _, root, kind, source = max(mounts, key=lambda item: item[0])
    return (kind in {'nfs', 'nfs4', 'cifs', 'ceph', 'fuse.mfs', 'fuse.moosefs', 'fuse.lizardfs'}
            or source.startswith('mfs#')
            or (bool(os.environ.get('RUNPOD_POD_ID')) and root != '/'))


def workspace_capacity(path, disk, data_used):
    result = dict(disk, capacity_source='filesystem', estimated=False, note='')
    configured = os.environ.get('WORKSPACE_STORAGE_CAPACITY_GB', '').strip()
    if configured:
        try:
            gb = float(configured)
            if not math.isfinite(gb) or gb <= 0:
                raise ValueError('Invalid capacity')
            total = int(gb * 1024 ** 3)
            if total <= 0:
                raise ValueError('Invalid capacity')
        except (ValueError, OverflowError):
            return dict(result, total=None, free=None, used=data_used, pct=None, alert=False,
                        capacity_source='unknown', note='Workspace capacity setting is invalid.')
        free = max(0, total - data_used) if data_used is not None else None
        pct = min(100, int(data_used / total * 100)) if data_used is not None else None
        return dict(result, total=total, used=data_used, free=free, pct=pct,
                    alert=pct is not None and pct >= 80, capacity_source='configured', estimated=True,
                    note='Configured volume capacity; remaining space is estimated from workspace files.')
    if shared_workspace(path):
        return dict(result, total=None, free=None, used=data_used, pct=None, alert=False,
                    capacity_source='unknown', note='Volume capacity is unavailable inside this container. Check your storage provider.')
    return result
