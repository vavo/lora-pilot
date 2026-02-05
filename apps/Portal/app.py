#!/usr/bin/env python3
import base64
import configparser
import json
import mimetypes
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import threading
import tomllib
import zipfile
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx

# Import dpipe router (handle both package and flat module execution)
try:
    from .dpipe_api import router as dpipe_router  # type: ignore
except ImportError:
    from dpipe_api import router as dpipe_router  # type: ignore

# Import service modules (handle both package and flat module execution)
try:
    from .services import models as models_service  # type: ignore
    from .services import shutdown as shutdown_service  # type: ignore
    from .services.comfy import create_router as create_comfy_router  # type: ignore
except ImportError:
    from services import models as models_service  # type: ignore
    from services import shutdown as shutdown_service  # type: ignore
    from services.comfy import create_router as create_comfy_router  # type: ignore

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
MODELS_DIR = Path(os.environ.get("MODELS_DIR", WORKSPACE_ROOT / "models"))
CONFIG_DIR = WORKSPACE_ROOT / "config"
MANIFEST = Path(os.environ.get("MODELS_MANIFEST", CONFIG_DIR / "models.manifest"))
DEFAULT_MANIFEST = Path(os.environ.get("DEFAULT_MODELS_MANIFEST", "/opt/pilot/config/models.manifest.default"))
SUPERVISORCTL = shutil.which("supervisorctl") or "/usr/bin/supervisorctl"
SERVICE_LOGS = {
    "jupyter": ("/workspace/logs/jupyter.out.log", "/workspace/logs/jupyter.err.log"),
    "code-server": ("/workspace/logs/code-server.out.log", "/workspace/logs/code-server.err.log"),
    "comfy": ("/workspace/logs/comfy.out.log", "/workspace/logs/comfy.err.log"),
    "kohya": ("/workspace/logs/kohya.out.log", "/workspace/logs/kohya.err.log"),
    "diffpipe": ("/workspace/logs/diffpipe.out.log", "/workspace/logs/diffpipe.err.log"),
    "invoke": ("/workspace/logs/invoke.out.log", "/workspace/logs/invoke.err.log"),
    "ai-toolkit": ("/workspace/logs/ai-toolkit.out.log", "/workspace/logs/ai-toolkit.err.log"),
    "controlpilot": ("/workspace/logs/controlpilot.out.log", "/workspace/logs/controlpilot.err.log"),
    "copilot": ("/workspace/logs/copilot.out.log", "/workspace/logs/copilot.err.log"),
}
DISPLAY_NAMES = {
    "jupyter": "Jupyter Lab",
    "code-server": "VS Code Server",
    "comfy": "Comfy UI",
    "kohya": "Kohya",
    "diffpipe": "TensorBoard",
    "invoke": "Invoke AI",
    "ai-toolkit": "AI Toolkit",
    "controlpilot": "ControlPilot",
    "copilot": "Copilot Sidecar",
}
SERVICES = list(SERVICE_LOGS.keys())
TRAINPILOT_BIN = Path("/opt/pilot/apps/TrainPilot/trainpilot.sh")
_tp_proc: Optional[subprocess.Popen] = None
_tp_logs: deque[str] = deque(maxlen=4000)
_tp_output_dir: Optional[Path] = None

_model_pull_lock = threading.Lock()
_model_pull_jobs: dict[str, "ModelPullJob"] = {}
_MODEL_PULL_TTL_SECONDS = 10 * 60
_MODEL_PULL_PROGRESS_RE = re.compile(r"(?P<pct>\\d{1,3})%")


@dataclass
class ModelPullJob:
    name: str
    state: str = "running"  # running | done | error
    pid: Optional[int] = None
    progress_pct: Optional[int] = None
    last_line: str = ""
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    output_tail: deque[str] = field(default_factory=lambda: deque(maxlen=200))


def _cleanup_model_pull_jobs(now: Optional[float] = None) -> None:
    ts = now if now is not None else time.time()
    with _model_pull_lock:
        to_delete: list[str] = []
        for name, job in _model_pull_jobs.items():
            if job.state in ("done", "error") and (ts - job.updated_at) > _MODEL_PULL_TTL_SECONDS:
                to_delete.append(name)
        for name in to_delete:
            _model_pull_jobs.pop(name, None)


def _model_pull_job_to_dict(job: ModelPullJob) -> dict:
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


def _update_model_pull_job(job: ModelPullJob, line: str) -> None:
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


def _run_model_pull_job(job: ModelPullJob, cmd: list[str]) -> None:
    try:
        env = os.environ.copy()
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
                idx_n = buf.find("\\n")
                idx_r = buf.find("\\r")
                idxs = [i for i in (idx_n, idx_r) if i != -1]
                if not idxs:
                    break
                idx = min(idxs)
                seg = buf[:idx]
                buf = buf[idx + 1 :]
                _update_model_pull_job(job, seg)
        if buf.strip():
            _update_model_pull_job(job, buf)
        proc.stdout.close()
        rc = proc.wait()
        if rc == 0:
            job.state = "done"
            job.progress_pct = 100
        else:
            job.state = "error"
            job.error = f"exit code {rc}"
        job.updated_at = time.time()
    except Exception as e:
        job.state = "error"
        job.error = str(e)
        job.updated_at = time.time()
    finally:
        with _model_pull_lock:
            _model_pull_jobs[job.name] = job


class ServiceEntry(BaseModel):
    name: str  # supervisor program name
    display: str
    state: str
    state_raw: str
    running: bool
    autostart: Optional[bool] = None


class ServiceAutostartRequest(BaseModel):
    enabled: bool


class DiskUsage(BaseModel):
    mount: str
    total: int
    used: int
    free: int
    pct: int
    alert: bool


class GPUInfo(BaseModel):
    index: int
    name: str
    util: Optional[int] = None
    mem_used: Optional[int] = None
    mem_total: Optional[int] = None


class Telemetry(BaseModel):
    host: str
    uptime_seconds: float
    load_avg: List[float]
    cpu_count: int
    mem_total: int
    mem_used: int
    mem_free: int
    disks: List[DiskUsage]
    gpus: List[GPUInfo]
    workspace_data_used_bytes: Optional[int] = None
    docs: Optional[str] = None  # unused in telemetry, kept for future


class DatasetEntry(BaseModel):
    name: str        # raw directory name
    display: str     # friendly name
    images: int      # number of image files found
    size_bytes: int


class TrainPilotModelCheckRequest(BaseModel):
    toml_path: str = ""


def _toml_find_first_str(data, key: str) -> Optional[str]:
    if isinstance(data, dict):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
        for vv in data.values():
            found = _toml_find_first_str(vv, key)
            if found:
                return found
    elif isinstance(data, list):
        for vv in data:
            found = _toml_find_first_str(vv, key)
            if found:
                return found
    return None


def _is_local_path_value(value: str) -> bool:
    if not value:
        return False
    # Kohya configs can accept HF repo ids, which are not local filesystem paths.
    return value.startswith("/")
    has_tags: bool
    path: str


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        # Disable caching to avoid stale assets (esp. TagPilot embed)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        # Cloudflare hints
        response.headers["Cloudflare-Cache-Status"] = "BYPASS"
        response.headers["CF-Cache-Status"] = "BYPASS"
        response.headers["CDN-Cache-Control"] = "no-store"
        return response




app = FastAPI(title="LoRA Pilot Portal", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(dpipe_router)
app.include_router(create_comfy_router(WORKSPACE_ROOT))

# Copilot sidecar config
COPILOT_SIDECAR_URL = os.environ.get("COPILOT_SIDECAR_URL", "http://127.0.0.1:7879")

# No-cache headers for API responses (helps avoid stale data)
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Cloudflare-Cache-Status"] = "BYPASS"
        response.headers["CF-Cache-Status"] = "BYPASS"
        response.headers["CDN-Cache-Control"] = "no-store"
    return response

README_PRIMARY = Path("/opt/pilot/README.md")
README_FALLBACK = Path("/workspace/README.md")
CHANGELOG_PRIMARY = Path("/opt/pilot/CHANGELOG")
CHANGELOG_FALLBACK = Path("/workspace/CHANGELOG")

@app.get("/api/models", response_model=List[models_service.ModelEntry])
def list_models():
    return models_service.parse_manifest(
        MANIFEST,
        DEFAULT_MANIFEST,
        MODELS_DIR,
        CONFIG_DIR,
    )


@app.get("/api/datasets", response_model=List[DatasetEntry])
def list_datasets():
    base = WORKSPACE_ROOT / "datasets"
    entries: List[DatasetEntry] = []
    if not base.exists():
        return entries
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        if not d.name.startswith("1_"):
            continue
        images = 0
        size_bytes = 0
        has_tags = False
        try:
            for p in d.rglob("*"):
                if p.is_file() and p.suffix.lower() in exts:
                    images += 1
                if p.is_file():
                    try:
                        size_bytes += p.stat().st_size
                    except Exception:
                        pass
                if p.is_file() and p.suffix.lower() in {".txt"}:
                    has_tags = True
        except Exception:
            pass
        raw = d.name
        # Strip leading "1_" prefix and prettify
        trimmed = raw[2:] if raw.startswith("1_") else raw
        display = trimmed.replace("_", " ").strip().title() or raw
        entries.append(DatasetEntry(name=raw, display=display, images=images, size_bytes=size_bytes, has_tags=has_tags, path=str(d)))
    return entries


async def _copilot_sidecar_request(method: str, path: str, json_body: Optional[dict] = None):
    url = COPILOT_SIDECAR_URL.rstrip("/") + path
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.request(method, url, json=json_body)
        ct = res.headers.get("content-type", "")
        if "application/json" in ct:
            try:
                return JSONResponse(status_code=res.status_code, content=res.json())
            except Exception:
                return JSONResponse(status_code=500, content={"detail": "invalid JSON from copilot sidecar"})
        return JSONResponse(status_code=res.status_code, content={"detail": res.text})
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="copilot sidecar not reachable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="copilot sidecar timed out")


@app.get("/api/copilot/status")
async def copilot_status():
    return await _copilot_sidecar_request("GET", "/status")


@app.post("/api/copilot/chat")
async def copilot_chat(payload: dict):
    return await _copilot_sidecar_request("POST", "/chat", json_body=payload)


def _clean_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_-")
    return cleaned or "dataset"


def _dataset_dir(name: str) -> Path:
    base = WORKSPACE_ROOT / "datasets"
    base.mkdir(parents=True, exist_ok=True)
    n = name.strip()
    if not n:
        n = "dataset"
    if n.startswith("1_"):
        return base / n
    return base / f"1_{_clean_name(n)}"


def _zipinfo_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return stat.S_ISLNK(mode)


def _safe_zip_member_path(name: str) -> PurePosixPath:
    safe_name = name.replace("\\", "/")
    path = PurePosixPath(safe_name)
    if path.is_absolute():
        raise ValueError(f"unsafe absolute path in zip: {name}")
    if ".." in path.parts:
        raise ValueError(f"unsafe parent path in zip: {name}")
    if path.parts and ":" in path.parts[0]:
        raise ValueError(f"unsafe drive path in zip: {name}")
    return path


def _safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    dest_dir = dest_dir.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if not info.filename:
                continue
            if _zipinfo_is_symlink(info):
                raise ValueError(f"symlink not allowed in zip: {info.filename}")
            rel_path = _safe_zip_member_path(info.filename)
            if not rel_path.parts:
                continue
            target = (dest_dir / Path(*rel_path.parts)).resolve()
            if os.path.commonpath([str(dest_dir), str(target)]) != str(dest_dir):
                raise ValueError(f"zip path escapes destination: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


@app.post("/api/datasets/create")
def create_dataset(payload: dict):
    raw = payload.get("name", "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="name is required")
    target = _dataset_dir(raw)
    if target.exists():
        raise HTTPException(status_code=400, detail="dataset already exists")
    target.mkdir(parents=True, exist_ok=True)
    return {"status": "created", "path": str(target)}


@app.post("/api/datasets/upload")
def upload_dataset(file: UploadFile = File(...)):
    zip_dir = WORKSPACE_ROOT / "datasets" / "ZIPs"
    target_dir = WORKSPACE_ROOT / "datasets"
    zip_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)
    fname_stem = _clean_name(Path(file.filename or "dataset.zip").stem)
    fname = fname_stem + ".zip"
    dest = zip_dir / fname
    try:
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        # Extract into /workspace/datasets/<cleaned_name>
        extract_dir = target_dir / f"1_{fname_stem}"
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)
        extract_dir.mkdir(parents=True, exist_ok=True)
        _safe_extract_zip(dest, extract_dir)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "uploaded", "zip": str(dest), "extracted_to": str(extract_dir)}


@app.delete("/api/datasets/{name}")
def delete_dataset(name: str):
    target = _dataset_dir(name)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    try:
        shutil.rmtree(target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Best-effort cleanup of any corresponding ZIP
    zip_dir = WORKSPACE_ROOT / "datasets" / "ZIPs"
    stem = _clean_name(name)
    for candidate in [zip_dir / f"{stem}.zip", zip_dir / f"1_{stem}.zip"]:
        if candidate.exists():
            try:
                candidate.unlink()
            except Exception:
                pass
    return {"status": "deleted", "path": str(target)}


@app.patch("/api/datasets/{name}")
def rename_dataset(name: str, payload: dict):
    """Rename a dataset directory"""
    new_name = payload.get("name", "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="new name is required")
    
    source = _dataset_dir(name)
    target = _dataset_dir(new_name)
    
    if not source.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if target.exists() and target != source:
        raise HTTPException(status_code=400, detail="Dataset with new name already exists")
    
    try:
        # Rename the directory
        source.rename(target)
        
        # Update any corresponding ZIP files
        zip_dir = WORKSPACE_ROOT / "datasets" / "ZIPs"
        old_stem = _clean_name(name)
        new_stem = _clean_name(new_name)
        
        for old_zip in [zip_dir / f"{old_stem}.zip", zip_dir / f"1_{old_stem}.zip"]:
            if old_zip.exists():
                new_zip = zip_dir / f"{new_stem}.zip"
                try:
                    old_zip.rename(new_zip)
                except Exception:
                    pass  # Best effort
        
        return {"status": "renamed", "old_path": str(source), "new_path": str(target)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tagpilot/load")
def tagpilot_load(name: str):
    target = _dataset_dir(name)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Dataset not found")
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".txt"}
    files = []
    for p in sorted(target.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in allowed:
            continue
        rel = p.relative_to(target).as_posix()
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        try:
            data = p.read_bytes()
            b64 = base64.b64encode(data).decode("utf-8")
        except Exception:
            continue
        files.append({"name": rel, "mime": mime, "b64": b64})
    return {"name": target.name, "files": files}


@app.post("/api/tagpilot/save")
def tagpilot_save(name: str, file: UploadFile = File(...)):
    target = _dataset_dir(name)
    zip_dir = WORKSPACE_ROOT / "datasets" / "ZIPs"
    zip_dir.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    fname = _clean_name(name) + ".zip"
    dest = zip_dir / fname
    try:
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        _safe_extract_zip(dest, target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "saved", "path": str(target), "zip": str(dest)}


@app.post("/api/models/{name}/pull")
def pull_model(name: str):
    models_service.ensure_manifest(MANIFEST, DEFAULT_MANIFEST, MODELS_DIR, CONFIG_DIR)
    cmd = ["/opt/pilot/get-models.sh", "pull", name]
    print(f"[models] pull start name={name} cmd={' '.join(cmd)}", file=sys.stderr)
    # Use existing CLI for consistency
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
        output = result.stdout or ""
        tail = output[-4000:] if len(output) > 4000 else output
        print(f"[models] pull ok name={name} output_tail={tail!r}", file=sys.stderr)
        return {"status": "ok", "output": output}
    except subprocess.CalledProcessError as e:
        output = e.stdout or str(e)
        tail = output[-4000:] if len(output) > 4000 else output
        print(f"[models] pull failed name={name} output_tail={tail!r}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=output)


@app.post("/api/models/{name}/pull/start")
def pull_model_start(name: str):
    """Start a model pull in the background (used by UI for progress updates)."""
    _cleanup_model_pull_jobs()
    models_service.ensure_manifest(MANIFEST, DEFAULT_MANIFEST, MODELS_DIR, CONFIG_DIR)
    entries = models_service.parse_manifest(MANIFEST, DEFAULT_MANIFEST, MODELS_DIR, CONFIG_DIR)
    if not any(e.name == name for e in entries):
        raise HTTPException(status_code=404, detail="Unknown model")

    with _model_pull_lock:
        existing = _model_pull_jobs.get(name)
        if existing and existing.state == "running":
            return _model_pull_job_to_dict(existing)
        job = ModelPullJob(name=name)
        _model_pull_jobs[name] = job

    cmd = ["/opt/pilot/get-models.sh", "pull", name]
    threading.Thread(target=_run_model_pull_job, args=(job, cmd), daemon=True).start()
    return _model_pull_job_to_dict(job)


@app.get("/api/models/{name}/pull/status")
def pull_model_status(name: str):
    _cleanup_model_pull_jobs()
    with _model_pull_lock:
        job = _model_pull_jobs.get(name)
        if not job:
            return {"name": name, "state": "idle"}
        return _model_pull_job_to_dict(job)


@app.get("/api/models/pulls")
def list_model_pulls():
    """List recent model pull jobs (running + recently completed/failed)."""
    _cleanup_model_pull_jobs()
    with _model_pull_lock:
        jobs = list(_model_pull_jobs.values())
    jobs.sort(key=lambda j: j.updated_at, reverse=True)
    return {"jobs": [_model_pull_job_to_dict(j) for j in jobs]}


@app.post("/api/models/{name}/delete")
def delete_model(name: str):
    models_service.ensure_manifest(MANIFEST, DEFAULT_MANIFEST, MODELS_DIR, CONFIG_DIR)
    try:
        deleted = models_service.delete_model(name, MANIFEST, MODELS_DIR)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown model")
    return {"status": "ok", "deleted": deleted}


@app.post("/api/hf-token")
async def set_hf_token(request: Request, token: Optional[str] = None):
    # Accept token either as query param or JSON body {token:"..."}
    if token is None:
        try:
            payload = await request.json()
            token = payload.get("token") if isinstance(payload, dict) else None
        except Exception:
            token = None
    if not token:
        raise HTTPException(status_code=422, detail="token is required")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    secrets_file = CONFIG_DIR / "secrets.env"
    lines = []
    if secrets_file.exists():
        lines = secrets_file.read_text().splitlines()
        lines = [ln for ln in lines if not ln.startswith("export HF_TOKEN=")]
    lines.append(f'export HF_TOKEN="{token}"')
    secrets_file.write_text("\n".join(lines) + "\n")
    os.environ["HF_TOKEN"] = token
    return {"status": "ok"}


@app.get("/api/hf-token")
def get_hf_token_status():
    token = os.environ.get("HF_TOKEN")
    if not token:
        secrets_file = CONFIG_DIR / "secrets.env"
        if secrets_file.exists():
            for line in secrets_file.read_text().splitlines():
                if line.startswith("export HF_TOKEN="):
                    token = line.split("=", 1)[-1].strip().strip('"')
                    break
    return {"set": bool(token)}


@app.get("/api/copilot/token")
def get_copilot_token_status():
    token = (
        os.environ.get("COPILOT_GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
    )
    if not token:
        secrets_file = CONFIG_DIR / "secrets.env"
        if secrets_file.exists():
            for line in secrets_file.read_text().splitlines():
                if line.startswith("export COPILOT_GITHUB_TOKEN="):
                    token = line.split("=", 1)[-1].strip().strip('"')
                    break
    return {"set": bool(token)}


@app.post("/api/copilot/token")
def set_copilot_token(payload: dict):
    token = None
    if isinstance(payload, dict):
        token = payload.get("token")
    if token is None:
        raise HTTPException(status_code=422, detail="token is required")
    token = str(token).strip()

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    secrets_file = CONFIG_DIR / "secrets.env"
    lines = []
    if secrets_file.exists():
        lines = secrets_file.read_text().splitlines()
        lines = [
            ln for ln in lines
            if not ln.startswith("export COPILOT_GITHUB_TOKEN=")
        ]
    if token:
        lines.append(f'export COPILOT_GITHUB_TOKEN="{token}"')
        os.environ["COPILOT_GITHUB_TOKEN"] = token
    else:
        os.environ.pop("COPILOT_GITHUB_TOKEN", None)

    secrets_file.write_text("\n".join(lines) + ("\n" if lines else ""))
    return {"status": "ok", "set": bool(token)}


def supervisor_status(name: str) -> ServiceEntry:
    if not SUPERVISORCTL:
        raise HTTPException(status_code=500, detail="supervisorctl not found")
    try:
        out = subprocess.check_output([SUPERVISORCTL, "status", name], text=True)
    except subprocess.CalledProcessError as e:
        out = e.output or ""
    # Expected format: "name                       RUNNING   pid ...\n"
    parts = out.strip().split()
    state_raw = parts[1] if len(parts) > 1 else "UNKNOWN"
    state_upper = state_raw.upper()
    running = state_upper in ("RUNNING",)
    display = DISPLAY_NAMES.get(name, name)
    return ServiceEntry(
        name=name,
        display=display,
        state=state_upper,
        state_raw=state_raw,
        running=running,
        autostart=_read_service_autostart(name),
    )


def _supervisor_config_path() -> Optional[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("SUPERVISOR_CONFIG_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend(
        [
            Path("/etc/supervisor/supervisord.conf"),
            Path("/opt/pilot/supervisor/supervisord.conf"),
            Path(__file__).resolve().parents[2] / "supervisor" / "supervisord.conf",
        ]
    )
    for path in candidates:
        try:
            if path.exists():
                return path
        except Exception:
            continue
    return None


def _read_service_autostart(name: str) -> Optional[bool]:
    conf_path = _supervisor_config_path()
    if not conf_path:
        return None
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # preserve option case
    try:
        parser.read(conf_path)
    except Exception:
        return None
    section = f"program:{name}"
    if not parser.has_section(section):
        return None
    if not parser.has_option(section, "autostart"):
        return None
    try:
        return parser.getboolean(section, "autostart")
    except Exception:
        raw = parser.get(section, "autostart", fallback="").strip().lower()
        if raw in ("true", "1", "yes", "on"):
            return True
        if raw in ("false", "0", "no", "off"):
            return False
        return None


def _set_service_autostart(name: str, enabled: bool) -> Optional[bool]:
    conf_path = _supervisor_config_path()
    if not conf_path:
        raise HTTPException(status_code=500, detail="Supervisor config not found")
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    try:
        parser.read(conf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read supervisor config: {str(e)}")

    section = f"program:{name}"
    if not parser.has_section(section):
        raise HTTPException(status_code=404, detail=f"Service section not found in supervisor config: {name}")
    parser.set(section, "autostart", "true" if enabled else "false")

    try:
        with conf_path.open("w", encoding="utf-8") as f:
            parser.write(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write supervisor config: {str(e)}")

    # Best effort: ask supervisor to re-read changed config.
    try:
        subprocess.check_output([SUPERVISORCTL, "reread"], text=True, stderr=subprocess.STDOUT)
    except Exception:
        # Autostart flag is primarily for next boot; ignore reread failures.
        pass
    return _read_service_autostart(name)


@app.get("/api/services", response_model=List[ServiceEntry])
def list_services():
    entries = []
    for svc in SERVICES:
        entries.append(supervisor_status(svc))
    return entries


@app.post("/api/services/{name}/{action}")
def control_service(name: str, action: str):
    if name not in SERVICES:
        raise HTTPException(status_code=404, detail="Unknown service")
    if action not in ("start", "stop", "restart"):
        raise HTTPException(status_code=400, detail="Bad action")
    if not SUPERVISORCTL:
        raise HTTPException(status_code=500, detail="supervisorctl not found")
    try:
        subprocess.check_output([SUPERVISORCTL, action, name], text=True, stderr=subprocess.STDOUT)
        return {"status": "ok"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.output or str(e))


@app.post("/api/services/{name}/settings/autostart")
def service_autostart(name: str, payload: ServiceAutostartRequest):
    if name not in SERVICES:
        raise HTTPException(status_code=404, detail="Unknown service")
    autostart = _set_service_autostart(name, bool(payload.enabled))
    return {"status": "ok", "name": name, "autostart": autostart}


@app.get("/api/services/{name}/log")
def service_log(name: str, lines: int = 100):
    if name not in SERVICE_LOGS:
        raise HTTPException(status_code=404, detail="Unknown service")
    out_log, err_log = SERVICE_LOGS[name]
    out_path = Path(out_log)
    err_path = Path(err_log)
    candidates = [p for p in (out_path, err_path) if p.exists()]
    if not candidates:
        raise HTTPException(status_code=404, detail="Log not found")
    if len(candidates) == 2:
        try:
            if err_path.stat().st_size == 0 and out_path.stat().st_size > 0:
                path = out_path
            else:
                path = max(candidates, key=lambda p: p.stat().st_mtime)
        except Exception:
            path = err_path if err_path.exists() else out_path
    else:
        path = candidates[0]
    try:
        content = subprocess.check_output(["tail", "-n", str(lines), str(path)], text=True)
    except subprocess.CalledProcessError:
        try:
            file_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            content = "\n".join(file_lines[-lines:]) + "\n"
        except Exception:
            content = path.read_text()[-5000:]
    return {"log": content, "path": str(path)}


@app.post("/api/shutdown/schedule")
def schedule_shutdown_endpoint(request: shutdown_service.ShutdownRequest):
    """Schedule a shutdown"""
    shutdown_service.schedule_shutdown(request)
    return {"status": "scheduled", "message": f"Shutdown scheduled in {request.value} {request.unit}"}


@app.post("/api/shutdown/cancel")
def cancel_shutdown_endpoint():
    """Cancel the scheduled shutdown"""
    shutdown_service.cancel_shutdown()
    return {"status": "cancelled", "message": "Shutdown cancelled"}


@app.get("/api/shutdown/status", response_model=shutdown_service.ShutdownStatus)
def shutdown_status_endpoint():
    """Get the current shutdown status"""
    return shutdown_service.get_shutdown_status()


def get_meminfo():
    meminfo = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                key, val = line.split(":", 1)
                meminfo[key.strip()] = int(val.strip().split()[0]) * 1024
    except FileNotFoundError:
        pass
    total = meminfo.get("MemTotal", 0)
    free = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    used = max(total - free, 0)
    return total, used, free


# --- tiny cache at module scope (top-level) ---
_WS_DU_CACHE = {"ts": 0.0, "val": None}
_WS_DU_CACHE_SECONDS = int(os.environ.get("WORKSPACE_DU_CACHE_SECONDS", "30"))
_WS_DU_TIMEOUT_SECONDS = float(os.environ.get("WORKSPACE_DU_TIMEOUT_SECONDS", "2.5"))


def _du_bytes(path: str) -> int:
    """
    Fast-ish: try GNU du first, then BusyBox-ish du, then a slow Python fallback.
    Returns total apparent bytes under `path`.
    """
    # Try GNU coreutils: du -sb
    for cmd in (["du", "-sb", path], ["du", "-sB1", path]):
        try:
            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=_WS_DU_TIMEOUT_SECONDS,
            )
            # output: "<bytes>\t<path>"
            tok = (p.stdout.strip().split() or ["0"])[0]
            return int(tok)
        except Exception:
            pass

    # Avoid Python os.walk fallback here: it can lock up telemetry on very large workspaces.
    raise RuntimeError("du failed or timed out")


def workspace_data_used_bytes(path: str) -> int:
    """
    Cached du result to keep /api/telemetry from turning into a space heater.
    """
    now = time.time()
    if _WS_DU_CACHE["val"] is not None and (now - _WS_DU_CACHE["ts"]) < _WS_DU_CACHE_SECONDS:
        return int(_WS_DU_CACHE["val"])
    try:
        val = _du_bytes(path)
        _WS_DU_CACHE["ts"] = now
        _WS_DU_CACHE["val"] = val
        return int(val)
    except Exception:
        # Best effort: return last known value if available, otherwise 0.
        if _WS_DU_CACHE["val"] is not None:
            return int(_WS_DU_CACHE["val"])
        return 0

def disk_usage(path: str) -> DiskUsage:
    # Prefer df with the actual mountpoint to honor container quotas/overlays
    def resolve_mountpoint(p: str) -> str:
        target = os.path.realpath(p)
        best = "/"
        try:
            with open("/proc/self/mountinfo") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    mnt = parts[4]
                    if target == mnt or (target.startswith(mnt.rstrip("/") + "/") and len(mnt) > len(best)):
                        best = mnt
        except Exception:
            pass
        return best

    mountpoint = resolve_mountpoint(path)
    try:
        out = subprocess.check_output(["df", "-kP", mountpoint], text=True).strip().splitlines()
        if len(out) >= 2:
            parts = out[1].split()
            size = int(parts[1]) * 1024
            used = int(parts[2]) * 1024
            free = int(parts[3]) * 1024
            pct = int((used / size) * 100) if size else 0
            return DiskUsage(mount=mountpoint, total=size, used=used, free=free, pct=pct, alert=pct >= 80)
    except Exception:
        pass
    st = shutil.disk_usage(path)
    pct = int((st.used / st.total) * 100) if st.total else 0
    return DiskUsage(mount=path, total=st.total, used=st.used, free=st.free, pct=pct, alert=pct >= 80)


def get_gpus() -> List[GPUInfo]:
    gpus: List[GPUInfo] = []
    candidates = [
        shutil.which("nvidia-smi"),
        "/usr/bin/nvidia-smi",
        "/usr/local/bin/nvidia-smi",
    ]
    candidates = [c for c in candidates if c]
    for exe in candidates:
        try:
            out = subprocess.check_output(
                [
                    exe,
                    "--query-gpu=index,name,utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
            )
            for line in out.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpus.append(
                        GPUInfo(
                            index=int(parts[0]),
                            name=parts[1],
                            util=int(parts[2]),
                            mem_used=int(parts[3]) * 1024 * 1024,
                            mem_total=int(parts[4]) * 1024 * 1024,
                        )
                    )
            if gpus:
                break
        except Exception:
            continue
    return gpus


_telemetry_history_lock = threading.Lock()
_telemetry_history_points: deque[dict] = deque()
_telemetry_history_started = False
_telemetry_history_file = CONFIG_DIR / "telemetry_history.jsonl"
_telemetry_history_sample_seconds = max(5, int(os.environ.get("TELEMETRY_HISTORY_SAMPLE_SECONDS", "30")))
_telemetry_history_max_seconds = max(60, int(os.environ.get("TELEMETRY_HISTORY_MAX_SECONDS", str(24 * 3600))))
_telemetry_history_last_compact_ts = 0.0
_telemetry_history_compact_interval_seconds = max(
    60, int(os.environ.get("TELEMETRY_HISTORY_COMPACT_SECONDS", "600"))
)


def _cpu_pct_from_load(load_avg: List[float], cpu_count: int) -> int:
    if not cpu_count:
        return 0
    try:
        return int(min(100, max(0, round(((load_avg[0] if load_avg else 0.0) / cpu_count) * 100))))
    except Exception:
        return 0


def _telemetry_history_prune(now: float) -> bool:
    changed = False
    cutoff = now - float(_telemetry_history_max_seconds)
    while _telemetry_history_points and float(_telemetry_history_points[0].get("ts", 0.0)) < cutoff:
        _telemetry_history_points.popleft()
        changed = True
    return changed


def _telemetry_history_load_from_disk() -> None:
    if not _telemetry_history_file.exists():
        return
    try:
        now = time.time()
        points: list[dict] = []
        for raw in _telemetry_history_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict) or "ts" not in obj:
                continue
            try:
                ts = float(obj["ts"])
            except Exception:
                continue
            if ts < (now - float(_telemetry_history_max_seconds)):
                continue
            points.append(obj)
        points.sort(key=lambda p: float(p.get("ts", 0.0)))
        with _telemetry_history_lock:
            _telemetry_history_points.clear()
            _telemetry_history_points.extend(points)
            _telemetry_history_prune(now)
    except Exception:
        # Best-effort: ignore corrupt history files.
        return


def _telemetry_history_write_all() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _telemetry_history_file.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for p in _telemetry_history_points:
            try:
                f.write(json.dumps(p, separators=(",", ":"), ensure_ascii=False) + "\n")
            except Exception:
                continue
    tmp.replace(_telemetry_history_file)


def _telemetry_history_append(point: dict) -> None:
    global _telemetry_history_last_compact_ts
    now = time.time()
    with _telemetry_history_lock:
        _telemetry_history_points.append(point)
        pruned = _telemetry_history_prune(now)
        do_compact = pruned or (now - _telemetry_history_last_compact_ts) >= _telemetry_history_compact_interval_seconds

        # Append first for durability; compact (rewrite) periodically.
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with _telemetry_history_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(point, separators=(",", ":"), ensure_ascii=False) + "\n")
        except Exception:
            pass

        if do_compact:
            try:
                _telemetry_history_write_all()
                _telemetry_history_last_compact_ts = now
            except Exception:
                pass


def _collect_cpu_gpu_history_point() -> dict:
    ts = time.time()
    load_avg = list(os.getloadavg()) if hasattr(os, "getloadavg") else [0.0, 0.0, 0.0]
    cpu_count = os.cpu_count() or 1
    cpu_pct = _cpu_pct_from_load(load_avg, cpu_count)

    gpus = []
    for g in get_gpus():
        mem_pct = int(min(100, max(0, round((g.mem_used / g.mem_total) * 100)))) if g.mem_total else 0
        gpus.append(
            {
                "index": g.index,
                "name": g.name,
                "util": g.util if g.util is not None else 0,
                "mem_used": g.mem_used if g.mem_used is not None else 0,
                "mem_total": g.mem_total if g.mem_total is not None else 0,
                "mem_pct": mem_pct,
            }
        )
    return {
        "ts": ts,
        "cpu": {"load_avg": load_avg, "cpu_count": cpu_count, "pct": cpu_pct},
        "gpus": gpus,
    }


def _telemetry_history_sampler() -> None:
    # Load once, then sample forever (best-effort).
    _telemetry_history_load_from_disk()
    next_ts = time.time()
    while True:
        now = time.time()
        if now < next_ts:
            time.sleep(min(1.0, next_ts - now))
            continue
        next_ts = now + float(_telemetry_history_sample_seconds)
        try:
            point = _collect_cpu_gpu_history_point()
            _telemetry_history_append(point)
        except Exception:
            # Never kill the sampler.
            continue


@app.on_event("startup")
def _start_telemetry_history() -> None:
    global _telemetry_history_started
    if _telemetry_history_started:
        return
    _telemetry_history_started = True
    t = threading.Thread(target=_telemetry_history_sampler, daemon=True)
    t.start()


@app.get("/api/telemetry", response_model=Telemetry)
def telemetry():
    host = os.environ.get("RUNPOD_POD_ID") or os.environ.get("RUNPOD_HOST_ID") or os.uname().nodename

    # Container uptime: derive from host uptime minus PID 1 start time
    uptime_seconds = 0.0
    try:
        with open("/proc/uptime") as f:
            host_uptime = float(f.read().split()[0])
        with open("/proc/1/stat") as f:
            stat = f.read().split()
            start_ticks = float(stat[21])
        hz = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        start_secs = start_ticks / hz
        uptime_seconds = max(host_uptime - start_secs, 0.0)
    except Exception:
        uptime_seconds = 0.0

    load_avg = list(os.getloadavg()) if hasattr(os, "getloadavg") else [0.0, 0.0, 0.0]
    cpu_count = os.cpu_count() or 1

    # Try cgroup (container) memory first
    mem_total = mem_used = mem_free = 0
    cgroup_cur = Path("/sys/fs/cgroup/memory.current")
    cgroup_max = Path("/sys/fs/cgroup/memory.max")
    if cgroup_cur.exists():
        try:
            mem_used = int(cgroup_cur.read_text().strip())
            max_txt = cgroup_max.read_text().strip() if cgroup_max.exists() else "max"
            if max_txt != "max":
                mem_total = int(max_txt)
            else:
                mem_total, _, _ = get_meminfo()
            mem_free = max(mem_total - mem_used, 0)
        except Exception:
            mem_total, mem_used, mem_free = get_meminfo()
    else:
        mem_total, mem_used, mem_free = get_meminfo()

    root_du = disk_usage("/")
    disks = [root_du]

    # Always include a /workspace entry using raw stats
    # Always include a /workspace entry using mount-aware stats
    try:
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        disks.append(disk_usage(str(WORKSPACE_ROOT)))
    except Exception:
        disks.append(
            DiskUsage(
                mount=str(WORKSPACE_ROOT),
                total=0,
                used=0,
                free=0,
                pct=0,
                alert=False,
            )
        )


    # NEW: how much data is actually stored under /workspace (du), cached
    ws_path = str(WORKSPACE_ROOT)
    try:
        ws_data_used = workspace_data_used_bytes(ws_path)
    except Exception:
        ws_data_used = 0

    gpus = get_gpus()
    return Telemetry(
        host=host,
        uptime_seconds=uptime_seconds,
        load_avg=load_avg,
        cpu_count=cpu_count,
        mem_total=mem_total,
        mem_used=mem_used,
        mem_free=mem_free,
        disks=disks,
        gpus=gpus,
        workspace_data_used_bytes=ws_data_used,  # <-- NEW
    )


@app.get("/api/telemetry/history")
def telemetry_history(max_seconds: int = 0):
    """
    Time-series telemetry for charts (backend-retained).

    - Retention is capped by TELEMETRY_HISTORY_MAX_SECONDS (default 24h).
    - Default response returns *all retained points* (so the UI can choose the window based on availability).
    - Use `max_seconds` to request only the last N seconds.
    """
    now = time.time()
    with _telemetry_history_lock:
        _telemetry_history_prune(now)
        pts = list(_telemetry_history_points)

    if not pts:
        return {
            "sample_seconds": _telemetry_history_sample_seconds,
            "retention_seconds": _telemetry_history_max_seconds,
            "available_seconds": 0,
            "from_ts": None,
            "to_ts": None,
            "points": [],
        }

    to_ts = float(pts[-1].get("ts", now))
    if max_seconds and max_seconds > 0:
        cutoff = to_ts - float(max_seconds)
        pts = [p for p in pts if float(p.get("ts", 0.0)) >= cutoff]

    from_ts = float(pts[0].get("ts", to_ts))
    return {
        "sample_seconds": _telemetry_history_sample_seconds,
        "retention_seconds": _telemetry_history_max_seconds,
        "available_seconds": max(0.0, to_ts - from_ts),
        "from_ts": from_ts,
        "to_ts": to_ts,
        "points": pts,
    }


# ---------------- TrainPilot (web) ----------------
class TrainPilotRequest(BaseModel):
    dataset_name: str
    output_name: str
    profile: str = "regular"
    toml_path: str = "/opt/pilot/apps/TrainPilot/newlora.toml"


def _tp_reader(proc: subprocess.Popen):
    global _tp_proc
    for raw in iter(proc.stdout.readline, b""):
        try:
            line = raw.decode("utf-8", errors="replace")
        except Exception:
            line = str(raw)
        _tp_logs.append(line.rstrip("\n"))
    proc.stdout.close()
    proc.wait()
    _tp_proc = None


@app.post("/api/trainpilot/start")
def trainpilot_start(req: TrainPilotRequest):
    global _tp_proc
    global _tp_output_dir
    if _tp_proc and _tp_proc.poll() is None:
        raise HTTPException(status_code=400, detail="TrainPilot already running")
    if not TRAINPILOT_BIN.exists():
        raise HTTPException(status_code=500, detail=f"TrainPilot script not found at {TRAINPILOT_BIN}")
    if not os.access(TRAINPILOT_BIN, os.X_OK):
        raise HTTPException(status_code=500, detail=f"TrainPilot script not executable: {TRAINPILOT_BIN}")
    ds_raw = req.dataset_name.strip()
    if not ds_raw:
        raise HTTPException(status_code=400, detail="dataset_name is required")
    ds_name = os.path.basename(ds_raw)
    out_name = req.output_name.strip() or ds_name
    _tp_output_dir = WORKSPACE_ROOT / "outputs" / out_name
    profile = req.profile.strip() or "regular"
    if profile not in ("quick_test", "regular", "high_quality"):
        raise HTTPException(status_code=400, detail="Invalid profile")
    toml_path = Path(req.toml_path.strip() or "/opt/pilot/apps/TrainPilot/newlora.toml")
    if not toml_path.exists():
        raise HTTPException(status_code=400, detail=f"TOML not found: {toml_path}")
    
    # Add debugging info to logs
    _tp_logs.append(f"=== Starting TrainPilot at {datetime.now().isoformat()} ===")
    _tp_logs.append(f"Dataset: {ds_name} (from {ds_raw})")
    _tp_logs.append(f"Output: {out_name}")
    _tp_logs.append(f"Profile: {profile}")
    _tp_logs.append(f"TOML: {toml_path}")
    _tp_logs.append(f"Script: {TRAINPILOT_BIN}")
    
    env = os.environ.copy()
    env.update(
        {
          "NO_CONFIRM": "1",
          "DATASET_NAME": ds_name,
          "OUTPUT_NAME": out_name,
          "PROFILE": profile,
          "TOML": str(toml_path),
          "WORKSPACE_ROOT": str(WORKSPACE_ROOT),
        }
    )
    try:
        proc = subprocess.Popen(
            [str(TRAINPILOT_BIN)],
            cwd=TRAINPILOT_BIN.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            preexec_fn=os.setsid,
        )
        _tp_logs.append(f"TrainPilot process started with PID: {proc.pid}")
    except Exception as e:
        _tp_logs.append(f"Failed to start TrainPilot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    _tp_proc = proc
    _tp_logs.clear()  # Clear startup logs, start fresh for process output
    _tp_logs.append(f"=== TrainPilot process started (PID: {proc.pid}) ===")
    threading.Thread(target=_tp_reader, args=(proc,), daemon=True).start()
    return {"status": "started", "pid": proc.pid}


@app.post("/api/trainpilot/stop")
def trainpilot_stop():
    global _tp_proc
    if not _tp_proc or _tp_proc.poll() is not None:
        _tp_proc = None
        return {"status": "noop"}
    try:
        os.killpg(os.getpgid(_tp_proc.pid), signal.SIGTERM)
        _tp_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(_tp_proc.pid), signal.SIGKILL)
        _tp_proc.wait()
    except ProcessLookupError:
        pass
    finally:
        _tp_proc = None
    return {"status": "stopped"}


@app.post("/api/trainpilot/model-check")
def trainpilot_model_check(req: TrainPilotModelCheckRequest):
    """
    Parse the selected TrainPilot TOML and check that checkpoint + VAE files exist.
    If they are missing and can be mapped to a manifest entry, return the model name
    so the UI can offer to download with progress.
    """
    toml_path = Path((req.toml_path or "").strip() or "/opt/pilot/apps/TrainPilot/newlora.toml")
    if not toml_path.exists():
        raise HTTPException(status_code=404, detail=f"TOML not found: {toml_path}")

    try:
        raw = toml_path.read_bytes()
        data = tomllib.loads(raw.decode("utf-8", errors="replace"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse TOML: {str(e)}")

    ckpt = _toml_find_first_str(data, "pretrained_model_name_or_path")
    vae = _toml_find_first_str(data, "vae")

    def check_one(kind: str, key: str, value: Optional[str]) -> dict:
        if not value:
            return {
                "kind": kind,
                "key": key,
                "value": "",
                "is_local_path": False,
                "exists": False,
                "model_name": None,
                "reason": f"Missing `{key}` in TOML",
            }
        if not _is_local_path_value(value):
            return {
                "kind": kind,
                "key": key,
                "value": value,
                "is_local_path": False,
                "exists": False,
                "model_name": None,
                "reason": "Not a local file path",
            }
        p = Path(value)
        exists = p.exists()
        model_name = None
        if not exists:
            try:
                model_name = models_service.model_name_for_expected_path(
                    p,
                    MANIFEST,
                    DEFAULT_MANIFEST,
                    MODELS_DIR,
                    CONFIG_DIR,
                )
            except Exception:
                model_name = None
        return {
            "kind": kind,
            "key": key,
            "value": value,
            "is_local_path": True,
            "exists": bool(exists),
            "model_name": model_name,
            "reason": None if exists else "File not found",
        }

    items = [
        check_one("checkpoint", "pretrained_model_name_or_path", ckpt),
        check_one("vae", "vae", vae),
    ]
    missing = [it for it in items if not it.get("exists")]
    return {"toml_path": str(toml_path), "items": items, "missing": missing}


@app.get("/api/trainpilot/logs")
def trainpilot_logs(limit: int = 500):
    """Get combined logs from TrainPilot process and Kohya training logs."""
    lines = []
    running = False
    
    # Add initial status
    lines.append(f"--- TrainPilot logs endpoint called at {datetime.now().isoformat()} ---")
    
    # Check TrainPilot process status
    global _tp_proc
    if _tp_proc:
        if _tp_proc.poll() is None:
            running = True
            lines.append(f"--- TrainPilot process running (PID: {_tp_proc.pid}) ---")
        else:
            lines.append(f"--- TrainPilot process finished (exit code: {_tp_proc.poll()}) ---")
    else:
        lines.append("--- No TrainPilot process running ---")
    
    # Add TrainPilot process logs
    tp_logs = list(_tp_logs)
    if tp_logs:
        lines.append(f"--- TrainPilot process logs ({len(tp_logs)} lines) ---")
        lines.extend(tp_logs)
    else:
        lines.append("--- No TrainPilot process logs available ---")
    
    # Also try to read the latest Kohya training log file
    try:
        outs_base = Path("/workspace/outputs")
        if not outs_base.exists():
            lines.append("--- No training outputs directory found at /workspace/outputs ---")
        elif _tp_output_dir:
            output_dir = _tp_output_dir
            log_file = output_dir / "_logs" / "train.log"
            lines.append(f"--- Current output dir: {output_dir} ---")
            if log_file.exists():
                stat_info = log_file.stat()
                lines.append(f"--- Log file exists, size: {stat_info.st_size} bytes, modified: {datetime.fromtimestamp(stat_info.st_mtime)} ---")
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    kohya_lines = f.readlines()
                    if kohya_lines:
                        lines.append(f"--- Kohya training logs from {output_dir.name} ({len(kohya_lines)} lines) ---")
                        lines.extend([line.rstrip() for line in kohya_lines[-100:]])
            else:
                lines.append(f"--- Log file not found for current run: {log_file} ---")
        else:
            # Find the most recent training output directory
            lines.append(f"--- Checking outputs directory: {outs_base} ---")
            output_dirs = [d for d in outs_base.iterdir() if d.is_dir()]
            lines.append(f"--- Found {len(output_dirs)} output directories ---")
            output_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for i, output_dir in enumerate(output_dirs[:3]):
                lines.append(f"--- Checking output dir {i+1}: {output_dir.name} ---")
                log_file = output_dir / "_logs" / "train.log"
                lines.append(f"--- Looking for log file: {log_file} ---")
                if log_file.exists():
                    try:
                        stat_info = log_file.stat()
                        lines.append(f"--- Log file exists, size: {stat_info.st_size} bytes, modified: {datetime.fromtimestamp(stat_info.st_mtime)} ---")
                        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                            kohya_lines = f.readlines()
                            if kohya_lines:
                                lines.append(f"--- Kohya training logs from {output_dir.name} ({len(kohya_lines)} lines) ---")
                                lines.extend([line.rstrip() for line in kohya_lines[-100:]])
                                break
                    except Exception as e:
                        lines.append(f"--- Error reading Kohya logs from {output_dir.name}: {str(e)} ---")
                        continue
                else:
                    lines.append(f"--- Log file not found: {log_file} ---")
                    logs_dir = output_dir / "_logs"
                    if logs_dir.exists():
                        lines.append(f"--- _logs directory exists, contents: {list(logs_dir.iterdir())} ---")
                    else:
                        lines.append(f"--- _logs directory does not exist ---")
    except Exception as e:
        lines.append(f"--- Error accessing training outputs: {str(e)} ---")
    
    # Always return a valid response, even if empty
    return {"lines": lines[-limit:], "running": running}


@app.get("/api/trainpilot/toml")
def get_trainpilot_toml():
    """Get the current TrainPilot TOML configuration content."""
    toml_path = Path("/opt/pilot/apps/TrainPilot/newlora.toml")
    
    if not toml_path.exists():
        raise HTTPException(status_code=404, detail="TOML configuration file not found")
    
    try:
        content = toml_path.read_text(encoding="utf-8")
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading TOML file: {str(e)}")


@app.get("/api/docs")
def get_docs():
    if README_PRIMARY.exists():
        return {"content": README_PRIMARY.read_text(encoding="utf-8")}
    if README_FALLBACK.exists():
        return {"content": README_FALLBACK.read_text(encoding="utf-8")}
    raise HTTPException(status_code=404, detail="README not found")


@app.get("/api/changelog")
def get_changelog():
    if CHANGELOG_PRIMARY.exists():
        return {"content": CHANGELOG_PRIMARY.read_text(encoding="utf-8")}
    if CHANGELOG_FALLBACK.exists():
        return {"content": CHANGELOG_FALLBACK.read_text(encoding="utf-8")}
    raise HTTPException(status_code=404, detail="CHANGELOG not found")


# Static assets
static_dir = Path(__file__).parent / "static"
tagpilot_dir = Path("/workspace/apps/TagPilot")
if not tagpilot_dir.exists():
    fallback_tagpilot = Path("/opt/pilot/apps/TagPilot")
    if fallback_tagpilot.exists():
        tagpilot_dir = fallback_tagpilot

# Mount TagPilot assets under /tagpilot (served by the same app/port)
app.mount("/tagpilot", NoCacheStaticFiles(directory=tagpilot_dir, html=True), name="tagpilot")
app.mount("/", NoCacheStaticFiles(directory=static_dir, html=True), name="static")
