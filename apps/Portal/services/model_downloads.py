"""Process-local model download jobs and subprocess output handling."""
import os
import re
import subprocess
from threading import Lock, Thread
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Optional

_MODEL_PULL_TTL_SECONDS = 10 * 60
_MODEL_PULL_PROGRESS_RE = re.compile(r"(?P<pct>\d{1,3})%")


@dataclass
class ModelPullJob:
    name: str
    state: str = "running"  # queued | running | done | error
    pid: Optional[int] = None
    progress_pct: Optional[int] = None
    last_line: str = ""
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    output_tail: deque[str] = field(default_factory=lambda: deque(maxlen=200))


def job_to_dict(job: ModelPullJob) -> dict:
    return {
        "name": job.name,
        "state": job.state,
        "pid": job.pid,
        "progress_pct": job.progress_pct,
        "last_line": job.last_line,
        "error": job.error,
        "started_at": job.started_at,
        "updated_at": job.updated_at,
        "output_tail": list(job.output_tail),
    }


def update_job(job: ModelPullJob, line: str) -> None:
    line = (line or "").strip()
    if not line:
        return
    job.last_line = line
    job.updated_at = time.time()
    job.output_tail.append(line)
    m = _MODEL_PULL_PROGRESS_RE.search(line)
    if m:
        try:
            pct = int(m.group("pct"))
            if 0 <= pct <= 100:
                job.progress_pct = pct
        except Exception:
            pass


class DownloadActiveError(Exception):
    pass


class ModelPullQueue:
    def __init__(self, token_reader: Callable[[], str], timeout: int = 1200):
        self.token_reader = token_reader
        self.timeout = timeout
        self.lock = Lock()
        self.jobs: dict[str, ModelPullJob] = {}

    def cleanup(self, now: Optional[float] = None) -> None:
        ts = now if now is not None else time.time()
        with self.lock:
            to_delete: list[str] = []
            for name, job in self.jobs.items():
                if job.state in ("done", "error") and (ts - job.updated_at) > _MODEL_PULL_TTL_SECONDS:
                    to_delete.append(name)
            for name in to_delete:
                self.jobs.pop(name, None)

    def run_command(self, cmd: list[str]) -> str:
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout running model pull: {' '.join(cmd)}") from e
        except FileNotFoundError as e:
            raise RuntimeError(f"Command not found: {cmd[0]}") from e
        output = result.stdout or ""
        if result.returncode != 0:
            raise RuntimeError(output.strip() or f"Command failed ({result.returncode}): {' '.join(cmd)}")
        return output

    def run_job(self, job: ModelPullJob, cmd: list[str]) -> None:
        try:
            env = os.environ.copy()
            env["HF_TOKEN"] = self.token_reader()
            env.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "0")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                bufsize=0,
            )
            job.pid = proc.pid
            job.updated_at = time.time()

            assert proc.stdout is not None
            buf = ""
            for chunk in iter(lambda: proc.stdout.read(4096), b""):
                text = chunk.decode("utf-8", errors="replace")
                buf += text
                while True:
                    idx_n = buf.find("\n")
                    idx_r = buf.find("\r")
                    idxs = [i for i in (idx_n, idx_r) if i != -1]
                    if not idxs:
                        break
                    idx = min(idxs)
                    seg = buf[:idx]
                    buf = buf[idx + 1 :]
                    update_job(job, seg)
                buf = buf[-8192:]
            if buf.strip():
                update_job(job, buf)
            proc.stdout.close()
            rc = proc.wait()
            if rc == 0:
                job.state = "done"
                job.progress_pct = 100
            else:
                job.state = "error"
                output = "\n".join(job.output_tail).strip()
                job.error = output[-2000:] if output else f"exit code {rc}"
            job.updated_at = time.time()
        except Exception as e:
            job.state = "error"
            job.error = str(e)
            job.updated_at = time.time()
        finally:
            with self.lock:
                self.jobs[job.name] = job

    def run_workflow(self, jobs: list[ModelPullJob], is_installed: Callable[[str], bool]) -> None:
        for job in jobs:
            try:
                installed = is_installed(job.name)
                with self.lock:
                    job.state = "done" if installed else "running"
                    job.updated_at = time.time()
                    if installed:
                        job.progress_pct = 100
                        job.last_line = "Reused installed component"
                if not installed:
                    self.run_job(job, ["/opt/pilot/get-models.sh", "pull", job.name])
            except Exception:
                with self.lock:
                    job.state = "error"
                    job.error = "Could not prepare workflow component. Review installation again."
                    job.updated_at = time.time()

    def start(self, name: str, job_key: str) -> dict:
        with self.lock:
            existing = self.jobs.get(job_key)
            if existing and existing.state in ("running", "queued"):
                return job_to_dict(existing)
            job = ModelPullJob(name=name)
            self.jobs[job_key] = job
        cmd = ["/opt/pilot/get-models.sh", "pull", name]
        Thread(target=self.run_job, args=(job, cmd), daemon=True).start()
        return job_to_dict(job)

    def start_workflow(self, names: list[str], is_installed: Callable[[str], bool]) -> list[dict]:
        new_jobs, selected_jobs = [], []
        with self.lock:
            for name in names:
                job = self.jobs.get(name)
                if not job or job.state not in ("running", "queued"):
                    job = ModelPullJob(name=name, state="queued")
                    self.jobs[name] = job
                    new_jobs.append(job)
                selected_jobs.append(job)
        if new_jobs:
            Thread(target=self.run_workflow, args=(new_jobs, is_installed), daemon=True).start()
        return [job_to_dict(job) for job in selected_jobs]

    def status(self, name: str) -> dict:
        self.cleanup()
        with self.lock:
            job = self.jobs.get(name)
            return job_to_dict(job) if job else {"name": name, "state": "idle"}

    def list_jobs(self) -> dict:
        self.cleanup()
        with self.lock:
            jobs = list(self.jobs.values())
        jobs.sort(key=lambda j: j.updated_at, reverse=True)
        return {"jobs": [job_to_dict(job) for job in jobs]}

    def delete_when_idle(self, name: str, delete: Callable[[], int]) -> int:
        with self.lock:
            job = self.jobs.get(name)
            if job and job.state in ("running", "queued"):
                raise DownloadActiveError("Wait for this model download to finish before removing it.")
            return delete()
