#!/usr/bin/env python3
import base64
import mimetypes
import os
import re
import shutil
import stat
import subprocess
import time
import threading
import zipfile
from collections import deque
from pathlib import Path, PurePosixPath
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import dpipe router (handle both package and flat module execution)
try:
    from .dpipe_api import router as dpipe_router  # type: ignore
except ImportError:
    from dpipe_api import router as dpipe_router  # type: ignore

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
}
DISPLAY_NAMES = {
    "jupyter": "Jupyter Lab",
    "code-server": "VS Code Server",
    "comfy": "Comfy UI",
    "kohya": "Kohya",
    "diffpipe": "TensorBoard",
    "invoke": "Invoke AI",
    "controlpilot": "ControlPilot",
}
SERVICES = list(SERVICE_LOGS.keys())
TRAINPILOT_BIN = Path("/opt/pilot/apps/TrainPilot/trainpilot.sh")
_tp_proc: Optional[subprocess.Popen] = None
_tp_logs: deque[str] = deque(maxlen=4000)

# Shutdown scheduler globals
shutdown_scheduled = False
shutdown_time = None
shutdown_thread = None
shutdown_lock = threading.Lock()


def ensure_manifest():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists() and DEFAULT_MANIFEST.exists():
        shutil.copy(DEFAULT_MANIFEST, MANIFEST)


class ModelEntry(BaseModel):
    name: str
    kind: str
    source: str
    subdir: str
    include: Optional[str] = ""
    expected_size_bytes: Optional[int] = None
    category: str
    type: str
    installed: bool
    size_bytes: int
    info_url: Optional[str] = None
    target_path: str


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


class ShutdownRequest(BaseModel):
    value: int
    unit: str  # "minutes", "hours", "days"


class ShutdownStatus(BaseModel):
    scheduled: bool
    time_remaining: Optional[int] = None  # seconds remaining
    shutdown_time: Optional[str] = None  # ISO timestamp


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


def classify_model(name: str, source: str, subdir: str) -> str:
    key = f"{name} {source} {subdir}".lower()
    if "flux" in key:
        return "FLUX"
    if "wan" in key:
        return "WAN"
    if any(k in key for k in ["sdxl", "sd_xl", "stable-diffusion-xl", "-xl", "xl-"]):
        return "SDXL"
    return "OTHERS"


def parse_manifest() -> List[ModelEntry]:
    ensure_manifest()
    entries: List[ModelEntry] = []
    if not MANIFEST.exists():
        return entries
    subdir_to_type = {
        "checkpoints": "checkpoint",
        "vae": "vae",
        "vae_approx": "vae",
        "loras": "lora",
        "refiners": "refiner",
        "text_encoders": "text_encoder",
        "clip": "clip",
        "clip_vision": "clip_vision",
        "controlnet": "controlnet",
        "diffusers": "diffusers",
        "diffusion_models": "checkpoint",
        "embeddings": "embedding",
        "hypernetworks": "hypernetwork",
        "latent_upscale_models": "latent_upscale",
        "audio_encoders": "audio_encoder",
        "photomaker": "photomaker",
        "style_models": "style",
        "unet": "unet",
        "upscale_models": "upscale",
    }

    def parse_size(raw: str) -> Optional[int]:
        if not raw:
            return None
        s = raw.strip().lower()
        try:
            if s.endswith("tb"):
                return int(float(s[:-2]) * 1024 * 1024 * 1024 * 1024)
            if s.endswith("gb"):
                return int(float(s[:-2]) * 1024 * 1024 * 1024)
            if s.endswith("mb"):
                return int(float(s[:-2]) * 1024 * 1024)
            if s.endswith("kb"):
                return int(float(s[:-2]) * 1024)
            # plain bytes
            if s.replace(".", "", 1).isdigit():
                return int(float(s))
        except Exception:
            return None
        return None

    with MANIFEST.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            name, kind, source, subdir, *rest = parts
            include = rest[0] if rest else ""
            expected_size_bytes = parse_size(rest[1]) if len(rest) > 1 else None
            target_dir = MODELS_DIR / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            expected: List[Path] = []
            matched: List[Path] = []
            repo = source.split(":")[0] if ":" in source else source
            if kind == "hf_file":
                path_in_repo = source.split(":", 1)[1] if ":" in source else ""
                fname = Path(path_in_repo).name
                expected = [target_dir / fname]
            elif kind == "url":
                fname = Path(source.split("?")[0]).name
                expected = [target_dir / fname]
            elif kind == "hf_repo":
                pats = [p.strip() for p in include.split(",")] if include else []
                if pats:
                    for pat in pats:
                        if pat:
                            matched.extend(target_dir.glob(pat))
                else:
                    # no include pattern; consider any file as match
                    matched.extend(target_dir.glob("*"))
            # If we have explicit expected files, check those
            if expected:
                matched.extend([p for p in expected if p.exists()])
            # Prefer safetensors when summarizing size
            safes = [p for p in matched if p.suffix == ".safetensors"]
            use_files = safes or matched
            installed = len(use_files) > 0
            size_bytes = sum(p.stat().st_size for p in use_files)
            if not installed and expected_size_bytes:
                size_bytes = expected_size_bytes
            category = classify_model(name, source, subdir)
            mtype = subdir_to_type.get(subdir, "checkpoint")
            info_url = None
            if kind.startswith("hf_"):
                repo = source.split(":")[0]
                info_url = f"https://huggingface.co/{repo}"
            elif source.startswith("http"):
                info_url = source
            entries.append(
                ModelEntry(
                    name=name,
                    kind=kind,
                    source=source,
                    subdir=subdir,
                    include=include,
                    expected_size_bytes=expected_size_bytes,
                    category=category,
                    type=mtype,
                    installed=installed,
                    size_bytes=size_bytes,
                    info_url=info_url,
                    target_path=str(target_dir),
                )
            )
    return entries


app = FastAPI(title="LoRA Pilot Portal", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(dpipe_router)

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

@app.get("/api/models", response_model=List[ModelEntry])
def list_models():
    return parse_manifest()


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
    ensure_manifest()
    # Use existing CLI for consistency
    try:
        result = subprocess.run(
            ["/opt/pilot/get-models.sh", "pull", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
        return {"status": "ok", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stdout or str(e))


@app.post("/api/models/{name}/delete")
def delete_model(name: str):
    ensure_manifest()
    line = None
    with MANIFEST.open() as f:
        for l in f:
            if l.strip().startswith("#") or not l.strip():
                continue
            parts = l.strip().split("|")
            if parts and parts[0] == name:
                line = parts
                break
    if not line:
        raise HTTPException(status_code=404, detail="Unknown model")
    parts = line + ["", "", "", ""]
    _, kind, source, subdir, include, *_ = parts
    target_dir = MODELS_DIR / subdir
    to_delete: list[Path] = []
    include = include.strip()

    def add_path(p: Path):
        if p.exists():
            to_delete.append(p)
            # Debug logging
            print(f"DEBUG: Marked for deletion: {p}")

    if kind == "hf_file":
        # hf_file sources look like repo:path/in/repo/filename
        fname = source.split(":", 1)[-1] if ":" in source else source
        fname = os.path.basename(fname)
        add_path(target_dir / fname)
    elif kind == "url":
        add_path(target_dir / os.path.basename(source.split("?", 1)[0]))
    else:
        # hf_repo or others: use include globs if provided; otherwise try name* heuristic
        patterns = [p.strip() for p in include.split(",") if p.strip()] if include else []
        if not patterns:
            # For hf_repo, be more conservative - only match exact name or name with common suffixes
            patterns = [
                f"{name}.*",           # Exact name with any extension
                f"{name}*",             # Exact name prefix (more conservative)
            ]
        print(f"DEBUG: Model {name}, kind={kind}, patterns={patterns}, target_dir={target_dir}")
        print(f"DEBUG: Include pattern: '{include}'")
        
        for pat in patterns:
            print(f"DEBUG: Searching for pattern: {pat}")
            for p in target_dir.glob(pat):
                # Additional safety check: only delete files that are actually related to this model
                # For hf_repo types, be extra careful and only delete files that match the exact model name
                if kind == "hf_repo":
                    filename = p.name.lower()
                    model_name_lower = name.lower()
                    # Only delete if filename starts with the exact model name
                    if filename.startswith(model_name_lower):
                        add_path(p)
                    else:
                        print(f"DEBUG: Skipping {p.name} - doesn't match model name {name}")
                else:
                    add_path(p)

    print(f"DEBUG: Total files marked for deletion: {len(to_delete)}")
    for p in to_delete:
        print(f"DEBUG: Will delete: {p}")

    deleted = 0
    for p in to_delete:
        try:
            if p.is_dir():
                print(f"DEBUG: Deleting directory: {p}")
                shutil.rmtree(p, ignore_errors=True)
            else:
                print(f"DEBUG: Deleting file: {p}")
                p.unlink(missing_ok=True)
            deleted += 1
        except Exception as e:
            print(f"DEBUG: Failed to delete {p}: {e}")
            pass

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
    return {"status": "ok"}


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
def service_log(name: str, lines: int = 50):
    if name not in SERVICE_LOGS:
        raise HTTPException(status_code=404, detail="Unknown service")
    out_log, err_log = SERVICE_LOGS[name]
    path = Path(err_log if Path(err_log).exists() else out_log)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Log not found")
    try:
        content = subprocess.check_output(["tail", "-n", str(lines), str(path)], text=True)
    except subprocess.CalledProcessError:
        content = path.read_text()[-5000:]
    return {"log": content, "path": str(path)}


@app.post("/api/shutdown/schedule")
def schedule_shutdown_endpoint(request: ShutdownRequest):
    """Schedule a shutdown"""
    schedule_shutdown(request)
    return {"status": "scheduled", "message": f"Shutdown scheduled in {request.value} {request.unit}"}


@app.post("/api/shutdown/cancel")
def cancel_shutdown_endpoint():
    """Cancel the scheduled shutdown"""
    cancel_shutdown()
    return {"status": "cancelled", "message": "Shutdown cancelled"}


@app.get("/api/shutdown/status", response_model=ShutdownStatus)
def shutdown_status_endpoint():
    """Get the current shutdown status"""
    return get_shutdown_status()


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


def shutdown_worker():
    """Worker function that waits for shutdown time and executes shutdown"""
    global shutdown_scheduled, shutdown_time
    
    while True:
        with shutdown_lock:
            if not shutdown_scheduled or shutdown_time is None:
                break
                
            time_remaining = shutdown_time - time.time()
            
            if time_remaining <= 0:
                # Time to shutdown
                print("Executing scheduled shutdown...")
                os.system("shutdown -h now")
                break
                
            # Sleep for a short time, then check again
            shutdown_lock.release()
            time.sleep(min(10, time_remaining))
            shutdown_lock.acquire()


def schedule_shutdown(request: ShutdownRequest):
    """Schedule a shutdown for the specified time"""
    global shutdown_scheduled, shutdown_time, shutdown_thread
    
    # Convert to seconds
    multipliers = {"minutes": 60, "hours": 3600, "days": 86400}
    if request.unit not in multipliers:
        raise HTTPException(status_code=400, detail="Invalid unit. Must be: minutes, hours, days")
    
    delay_seconds = request.value * multipliers[request.unit]
    
    with shutdown_lock:
        shutdown_scheduled = True
        shutdown_time = time.time() + delay_seconds
        
        # Start the shutdown worker thread
        shutdown_thread = threading.Thread(target=shutdown_worker, daemon=True)
        shutdown_thread.start()


def cancel_shutdown():
    """Cancel the scheduled shutdown"""
    global shutdown_scheduled, shutdown_time, shutdown_thread
    
    with shutdown_lock:
        shutdown_scheduled = False
        shutdown_time = None
        shutdown_thread = None


def get_shutdown_status() -> ShutdownStatus:
    """Get the current shutdown status"""
    global shutdown_scheduled, shutdown_time
    
    with shutdown_lock:
        if not shutdown_scheduled or shutdown_time is None:
            return ShutdownStatus(scheduled=False)
        
        time_remaining = max(0, int(shutdown_time - time.time()))
        shutdown_time_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(shutdown_time))
        
        return ShutdownStatus(
            scheduled=True,
            time_remaining=time_remaining,
            shutdown_time=shutdown_time_str
        )


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
    profile = req.profile.strip() or "regular"
    if profile not in ("quick_test", "regular", "high_quality"):
        raise HTTPException(status_code=400, detail="Invalid profile")
    toml_path = Path(req.toml_path.strip() or "/opt/pilot/apps/TrainPilot/newlora.toml")
    if not toml_path.exists():
        raise HTTPException(status_code=400, detail=f"TOML not found: {toml_path}")
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
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    _tp_proc = proc
    _tp_logs.clear()
    threading.Thread(target=_tp_reader, args=(proc,), daemon=True).start()
    return {"status": "started", "pid": proc.pid}


@app.post("/api/trainpilot/stop")
def trainpilot_stop():
    global _tp_proc
    if not _tp_proc or _tp_proc.poll() is not None:
        _tp_proc = None
        return {"status": "noop"}
    try:
        _tp_proc.terminate()
        _tp_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _tp_proc.kill()
    finally:
        _tp_proc = None
    return {"status": "stopped"}


@app.get("/api/trainpilot/logs")
def trainpilot_logs(limit: int = 500):
    """Get combined logs from TrainPilot process and Kohya training logs."""
    lines = []
    
    # Add TrainPilot process logs
    lines.extend(list(_tp_logs))
    
    # Also try to read the latest Kohya training log file
    try:
        # Find the most recent training output directory
        outs_base = Path("/workspace/outs")
        if outs_base.exists():
            # Get all output directories and sort by modification time
            output_dirs = [d for d in outs_base.iterdir() if d.is_dir()]
            output_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for output_dir in output_dirs[:3]:  # Check last 3 directories
                log_file = output_dir / "_logs" / "train.log"
                if log_file.exists():
                    try:
                        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                            kohya_lines = f.readlines()
                            # Add a separator to distinguish Kohya logs
                            if kohya_lines:
                                lines.append(f"--- Kohya training logs from {output_dir.name} ---")
                                lines.extend([line.rstrip() for line in kohya_lines[-100:]])  # Last 100 lines
                                break  # Only read from the most recent training
                    except Exception:
                        continue
    except Exception:
        pass  # If we can't read Kohya logs, just return TrainPilot logs
    
    return {"lines": lines[-limit:]}


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
