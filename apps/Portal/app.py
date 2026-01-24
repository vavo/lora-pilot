#!/usr/bin/env python3
import base64
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
import zipfile
from collections import deque
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
    "controlpilot": "ControlPilot",
    "copilot": "Copilot Sidecar",
}
SERVICES = list(SERVICE_LOGS.keys())
TRAINPILOT_BIN = Path("/opt/pilot/apps/TrainPilot/trainpilot.sh")
_tp_proc: Optional[subprocess.Popen] = None
_tp_logs: deque[str] = deque(maxlen=4000)
_tp_output_dir: Optional[Path] = None


class ServiceEntry(BaseModel):
    name: str  # supervisor program name
    display: str
    state: str
    state_raw: str
    running: bool


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
    return ServiceEntry(name=name, display=display, state=state_upper, state_raw=state_raw, running=running)


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


def _du_bytes(path: str) -> int:
    """
    Fast-ish: try GNU du first, then BusyBox-ish du, then a slow Python fallback.
    Returns total apparent bytes under `path`.
    """
    # Try GNU coreutils: du -sb
    for cmd in (["du", "-sb", path], ["du", "-sB1", path]):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # output: "<bytes>\t<path>"
            tok = (p.stdout.strip().split() or ["0"])[0]
            return int(tok)
        except Exception:
            pass

    # Slow fallback: walk filesystem
    total = 0
    for root, dirs, files in os.walk(path, topdown=True):
        # avoid dying on permission errors
        try:
            for name in files:
                fp = os.path.join(root, name)
                try:
                    st = os.stat(fp, follow_symlinks=False)
                    total += int(st.st_size)
                except Exception:
                    continue
        except Exception:
            continue
    return total


def workspace_data_used_bytes(path: str) -> int:
    """
    Cached du result to keep /api/telemetry from turning into a space heater.
    """
    now = time.time()
    if _WS_DU_CACHE["val"] is not None and (now - _WS_DU_CACHE["ts"]) < _WS_DU_CACHE_SECONDS:
        return int(_WS_DU_CACHE["val"])
    val = _du_bytes(path)
    _WS_DU_CACHE["ts"] = now
    _WS_DU_CACHE["val"] = val
    return int(val)

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
