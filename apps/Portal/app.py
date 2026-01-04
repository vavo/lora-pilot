#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import time
from collections import deque
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
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
    "tagpilot": ("/workspace/logs/tagpilot.out.log", "/workspace/logs/tagpilot.err.log"),
    "controlpilot": ("/workspace/logs/controlpilot.out.log", "/workspace/logs/controlpilot.err.log"),
}
DISPLAY_NAMES = {
    "jupyter": "Jupyter Lab",
    "code-server": "VS Code Server",
    "comfy": "Comfy UI",
    "kohya": "Kohya",
    "diffpipe": "TensorBoard",
    "invoke": "Invoke AI",
    "tagpilot": "TagPilot",
    "controlpilot": "ControlPilot",
}
SERVICES = list(SERVICE_LOGS.keys())
TRAINPILOT_BIN = Path("/opt/pilot/apps/TrainPilot/trainpilot.sh")
_tp_proc: Optional[subprocess.Popen] = None
_tp_logs: deque[str] = deque(maxlen=4000)


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
    docs: Optional[str] = None  # unused in telemetry, kept for future


class DatasetEntry(BaseModel):
    name: str        # raw directory name
    display: str     # friendly name
    images: int      # number of image files found
    size_bytes: int
    has_tags: bool
    path: str


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
app.include_router(dpipe_router)

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


@app.post("/api/datasets/create")
def create_dataset(payload: dict):
    base = WORKSPACE_ROOT / "datasets"
    base.mkdir(parents=True, exist_ok=True)
    raw = payload.get("name", "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="name is required")
    cleaned = _clean_name(raw)
    dirname = f"1_{cleaned}"
    target = base / dirname
    if target.exists():
        raise HTTPException(status_code=400, detail="dataset already exists")
    target.mkdir(parents=True, exist_ok=True)
    return {"status": "created", "path": str(target)}


@app.post("/api/datasets/upload")
def upload_dataset(file: UploadFile = File(...)):
    zip_dir = WORKSPACE_ROOT / "datasets" / "ZIPs"
    zip_dir.mkdir(parents=True, exist_ok=True)
    fname = _clean_name(Path(file.filename or "dataset.zip").stem) + ".zip"
    dest = zip_dir / fname
    try:
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "uploaded", "path": str(dest)}


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
    _, _, _, subdir, *_ = line + ["", ""]
    target_dir = MODELS_DIR / subdir
    if target_dir.exists():
        for p in target_dir.glob("*"):
            try:
                p.unlink()
            except IsADirectoryError:
                shutil.rmtree(p, ignore_errors=True)
    return {"status": "ok"}


@app.post("/api/hf-token")
def set_hf_token(token: str):
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
    if shutil.which("nvidia-smi") is None:
        return gpus
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
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
    except Exception:
        pass
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
    # Heuristic: pick a reasonable workspace mount (prefer explicit env, otherwise realpath, then common volume paths)
    candidates = []
    env_ws = os.environ.get("WORKSPACE_DISK_PATH")
    if env_ws:
        candidates.append(env_ws)
    # Force /workspace first (most typical mount), then resolved WORKSPACE_ROOT, then others
    candidates.append("/workspace")
    candidates.append(str(Path(WORKSPACE_ROOT).resolve()))
    candidates.extend(["/runpod-volume", "/data"])
    seen = set()
    # Always include a /workspace entry using raw stats (even if same mount as /)
    try:
        ws_stats = shutil.disk_usage(str(WORKSPACE_ROOT))
        ws_pct = int((ws_stats.used / ws_stats.total) * 100) if ws_stats.total else 0
        disks.append(
            DiskUsage(
                mount="/workspace",
                total=ws_stats.total,
                used=ws_stats.used,
                free=ws_stats.free,
                pct=ws_pct,
                alert=ws_pct >= 80,
            )
        )
    except Exception:
        pass
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
    return {"lines": list(_tp_logs)[-limit:]}


@app.get("/api/docs")
def get_docs():
    if README_PRIMARY.exists():
        return {"content": README_PRIMARY.read_text(encoding="utf-8")}
    if README_FALLBACK.exists():
        return {"content": README_FALLBACK.read_text(encoding="utf-8")}
    raise HTTPException(status_code=404, detail="README not found")


# Static assets
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
