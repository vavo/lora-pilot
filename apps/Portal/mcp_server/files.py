"""Descriptor-relative file access. Client input never selects a filesystem root."""
import hashlib
import json
import os
import stat
import uuid
import threading
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


class Rejected(Exception):
    def __init__(self, code='NOT_FOUND'):
        self.code = code
        super().__init__(code)


def parts(relative):
    value = str(relative)
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or '\\' in value or '\0' in value
            or any(piece in {'', '.', '..'} for piece in value.split('/'))):
        raise Rejected('INVALID_INPUT')
    return path.parts


class Files:
    def __init__(self, root):
        # Root is administrator configuration, never a tool argument.
        self.root = Path(root).absolute()
        self.local = threading.local()

    def checkpoint(self):
        event = getattr(self.local, 'cancelled', None)
        if event is not None and event.is_set():
            raise Rejected('CANCELLED')

    @contextmanager
    def directory(self, relative=None, create=False, private=False):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for name in parts(relative) if relative else ():
                if create:
                    try:
                        os.mkdir(name, 0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            info = os.fstat(fd)
            if private and (info.st_uid != os.geteuid() or info.st_mode & 0o077):
                raise Rejected('STORAGE_UNAVAILABLE')
            yield fd
        finally:
            os.close(fd)

    @contextmanager
    def open(self, relative, max_bytes=None, private=False, single_link=True):
        path = parts(relative)
        with self.directory('/'.join(path[:-1]) if len(path) > 1 else None) as parent:
            fd = os.open(path[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or (single_link and info.st_nlink != 1)
                    or (max_bytes is not None and info.st_size > max_bytes)
                    or (private and (info.st_uid != os.geteuid() or info.st_mode & 0o077))):
                raise Rejected('UNSAFE_FILE')
            yield stream

    def json(self, relative, max_bytes=1024 * 1024, private=False):
        with self.open(relative, max_bytes=max_bytes, private=private) as source:
            data = source.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise Rejected('LIMIT_EXCEEDED')
        return json.loads(data)

    def write(self, relative, data, replace=False):
        path = parts(relative)
        with self.directory('/'.join(path[:-1]), private=True) as parent:
            temporary = '.' + uuid.uuid4().hex + '.tmp'
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            try:
                with os.fdopen(fd, 'wb') as target:
                    target.write(data)
                    target.flush()
                    os.fsync(target.fileno())
                if replace:
                    # Replacing the directory entry never follows/truncates its old inode.
                    os.replace(temporary, path[-1], src_dir_fd=parent, dst_dir_fd=parent)
                else:
                    os.link(temporary, path[-1], src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                    os.unlink(temporary, dir_fd=parent)
                os.fsync(parent)
            finally:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass

    def new_directory(self, relative):
        path = parts(relative)
        with self.directory('/'.join(path[:-1]), create=True) as parent:
            os.mkdir(path[-1], 0o700, dir_fd=parent)
            os.fsync(parent)

    def listdir(self, relative, limit=5000):
        with self.directory(relative) as fd:
            with os.scandir(fd) as entries:
                result = []
                for entry in entries:
                    self.checkpoint()
                    if len(result) >= limit:
                        raise Rejected('LIMIT_EXCEEDED')
                    result.append((entry.name, entry.stat(follow_symlinks=False)))
                return sorted(result, key=lambda item: item[0])

    def digest(self, relative, max_bytes=16 * 1024 ** 3):
        with self.open(relative, max_bytes=max_bytes) as source:
            before = os.fstat(source.fileno())
            digest = hashlib.sha256()
            total = 0
            while data := source.read(1024 * 1024):
                self.checkpoint()
                total += len(data)
                if total > max_bytes:
                    raise Rejected('LIMIT_EXCEEDED')
                digest.update(data)
            after = os.fstat(source.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise Rejected('PLAN_STALE')
        return dict(sha256=digest.hexdigest(), size_bytes=total)

    def copy_verified(self, source_path, destination, expected):
        """Create a new private copy and verify bytes against the approved content."""
        target_parts = parts(destination)
        with self.directory('/'.join(target_parts[:-1]), create=True, private=True) as parent:
            fd = os.open(target_parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            with os.fdopen(fd, 'wb') as target, self.open(source_path, max_bytes=expected['size_bytes']) as source:
                result, total = hashlib.sha256(), 0
                while data := source.read(1024 * 1024):
                    total += len(data)
                    if total > expected['size_bytes']:
                        raise Rejected('PLAN_STALE')
                    target.write(data)
                    result.update(data)
                if total != expected['size_bytes'] or result.hexdigest() != expected['sha256']:
                    raise Rejected('PLAN_STALE')
                target.flush()
                os.fsync(target.fileno())
            os.fsync(parent)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()
