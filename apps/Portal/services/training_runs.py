"""Persistent, single-worker training queue with explicit restart recovery."""
import copy
import fcntl
import json
import logging
import os
import re
import signal
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from .gpu_guard import LAUNCH_LOCK

ACTIVE = {'queued', 'running', 'stopping'}
log = logging.getLogger(__name__)


def now():
    return datetime.now(timezone.utc).isoformat()


def under(root, path):
    root_resolved = os.path.realpath(str(root))
    resolved = os.path.realpath(str(path))
    root_with_sep = os.path.join(root_resolved, '')
    if resolved != root_resolved and not resolved.startswith(root_with_sep):
        raise HTTPException(400, 'Path must stay within its workspace directory')
    return Path(resolved)


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def process_identity(pid):
    try:
        return Path(f'/proc/{int(pid)}/stat').read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, ValueError, IndexError):
        return None


class TrainingRuns:
    def __init__(self, root, prepare, launch, conflicts):
        self.root = Path(root)
        self.prepare = prepare
        self.launch = launch
        self.conflicts = conflicts
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.stopping = threading.Event()
        self.worker = None
        self.owner = None
        self.proc = None
        self.current = None
        self.paused = False
        self.reason = []

    def start(self, background=True):
        with self.lock:
            if self.owner:
                return
            self.root.mkdir(parents=True, exist_ok=True)
            if self.root.is_symlink():
                raise HTTPException(400, 'Training history directory must not be a symlink')
            fd = os.open(self.root / 'worker.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            self.owner = os.fdopen(fd, 'w')
            try:
                fcntl.flock(self.owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                self.owner.close()
                self.owner = None
                raise HTTPException(503, 'Another ControlPilot worker owns the training queue')
            try:
                state = self.root / 'queue.json'
                if state.is_symlink():
                    raise HTTPException(400, 'Invalid queue state path')
                self.paused = state.exists() and json.loads(state.read_text()).get('paused', False)
                for run in self.list():
                    if run['status'] in ACTIVE:
                        self.paused = True
                        if run['status'] != 'queued':
                            run.update(status='interrupted', finished_at=now(),
                                       error='ControlPilot restarted. Inspect the process and logs before repeating this run.')
                            self.save(run)
                self._save_queue()
            except Exception:
                self.owner.close()
                self.owner = None
                raise
            self.stopping.clear()
            if background:
                self.worker = threading.Thread(target=self._work, daemon=True, name='training-queue')
                self.worker.start()

    def directory(self, run_id):
        if not re.fullmatch(r'[a-f0-9]{32}', run_id):
            raise HTTPException(404, 'Training run not found')
        directory = self.root / uuid.UUID(run_id).hex
        if directory.is_symlink():
            raise HTTPException(400, 'Invalid training history path')
        return under(self.root, directory)

    def get(self, run_id):
        path = self.directory(run_id) / 'run.json'
        if path.is_symlink():
            raise HTTPException(400, 'Invalid training history file')
        try:
            run = json.loads(path.read_text())
        except FileNotFoundError:
            raise HTTPException(404, 'Training run not found')
        if run.get('id') != run_id:
            raise HTTPException(400, 'Invalid training record')
        return run

    def list(self):
        with self.lock:
            runs = []
            if self.root.exists():
                for path in self.root.iterdir():
                    if re.fullmatch(r'[a-f0-9]{32}', path.name) and (path / 'run.json').exists():
                        runs.append(self.get(path.name))
            return sorted(runs, key=lambda r: (r['created_at'], r['id']), reverse=True)

    def save(self, run):
        write_json(self.directory(run['id']) / 'run.json', run)

    def _save_queue(self):
        write_json(self.root / 'queue.json', {'paused': self.paused})

    def submit(self, spec):
        with self.lock:
            if sum(r['status'] in ACTIVE for r in self.list()) >= 50:
                raise HTTPException(409, 'Queue is full (50 runs). Cancel a queued run first.')
            run_id = uuid.uuid4().hex
            directory = self.directory(run_id)
            directory.mkdir(mode=0o700)
            prepared = self.prepare(copy.deepcopy(spec), run_id, directory)
            run = dict(prepared, id=run_id, created_at=now(), status='queued', exit_code=None,
                       started_at=None, finished_at=None, error=None)
            self.save(run)
            self.wake.set()
            return run

    def set_paused(self, paused):
        with self.lock:
            self.paused = paused
            self._save_queue()
            self.wake.set()

    def orphan_conflicts(self):
        reasons = []
        for run in self.list():
            if run['status'] == 'interrupted' and run.get('pid'):
                identity = process_identity(run['pid'])
                if identity and identity == run.get('process_identity'):
                    reasons.append(f'Interrupted run {run["spec"]["output_name"]} still has a live process ({run["pid"]}).')
        return reasons

    def tick(self):
        with LAUNCH_LOCK, self.lock:
            if self.proc:
                code = self.proc.poll()
                if code is None:
                    return
                run = self.get(self.current)
                run.update(status='stopped' if run['status'] == 'stopping' else 'succeeded' if code == 0 else 'failed',
                           exit_code=code, finished_at=now())
                self.save(run)
                self.proc = None
                self.current = None
            queued = [r for r in reversed(self.list()) if r['status'] == 'queued']
            if self.paused or not queued:
                return
            self.reason = self.orphan_conflicts() + self.conflicts()
            if self.reason:
                return
            run = queued[0]
            run.update(status='running', started_at=now())
            self.save(run)  # A crash during launch becomes interrupted, never silently repeated.
            try:
                path = self.directory(run['id']) / 'run.log'
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'ab') as stream:
                    proc = self.launch(run, stream)
                self.proc = proc
                self.current = run['id']
                run.update(pid=proc.pid, process_identity=process_identity(proc.pid))
                self.save(run)
            except Exception as error:
                if self.proc is not None:
                    self._terminate(self.proc)
                    self.proc = None
                    self.current = None
                run.update(status='failed', finished_at=now(), error=str(getattr(error, 'detail', error)))
                self.save(run)

    @staticmethod
    def _terminate(proc):
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
        except ProcessLookupError:
            pass

    def cancel(self, run_id):
        with self.lock:
            run = self.get(run_id)
            if run['status'] == 'queued':
                run.update(status='cancelled', finished_at=now())
                self.save(run)
            elif self.current == run_id and self.proc:
                run['status'] = 'stopping'
                self.save(run)
                self._terminate(self.proc)
            else:
                raise HTTPException(409, 'Only queued or currently managed runs can be stopped')
            self.wake.set()
            return run

    def logs(self, run_id):
        path = under(self.directory(run_id), self.directory(run_id) / 'run.log')
        if not path.exists():
            return []
        with path.open('rb') as stream:
            stream.seek(max(0, path.stat().st_size - 128 * 1024))
            return stream.read().decode('utf-8', errors='replace').replace('\r', '\n').splitlines()[-500:]

    def _work(self):
        while not self.stopping.is_set():
            try:
                self.tick()
            except Exception:
                log.exception('Training queue failed; pausing dispatch')
                with self.lock:
                    self.paused = True
                    self.reason = ['Queue error. Inspect ControlPilot logs before resuming.']
            self.wake.wait(3)
            self.wake.clear()

    def close(self):
        self.stopping.set()
        self.wake.set()
        if self.worker:
            self.worker.join(timeout=15)
            if self.worker.is_alive():
                return  # Never release ownership while the worker can still dispatch.
        if self.owner:
            self.owner.close()
            self.owner = None
