import json
import os
import re
import signal
import subprocess
import threading
import uuid
from collections import deque
from pathlib import Path, PurePosixPath
from typing import List, Optional, Union

import toml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Paths aligned with the runtime layout
WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
MODEL_DIR = WORKSPACE / "models"
BASE_DATASET_DIR = WORKSPACE / "datasets"
OUTPUT_DIR = WORKSPACE / "outputs"
CONFIG_DIR = WORKSPACE / "configs"
DIFFPIPE_APP_DIR = Path(os.environ.get("DIFFPIPE_APP_DIR", WORKSPACE / "apps" / "diffusion-pipe"))
DIFFPIPE_REPO_DIR = Path(os.environ.get("DIFFPIPE_REPO_DIR", "/opt/pilot/repos/diffusion-pipe"))
DPIPE_CONFIG_ROOT = CONFIG_DIR / "dpipe"
DPIPE_OUTPUT_ROOT = OUTPUT_DIR / "dpipe"
DPIPE_RUN_REGISTRY = DPIPE_CONFIG_ROOT / "runs.json"

# Deepspeed entrypoint (isolated in the diffusion-pipe venv)
DEEPSPEED_BIN = os.environ.get("DEEPSPEED_BIN", "/opt/venvs/diffpipe/bin/deepspeed")
NUM_GPUS = os.environ.get("NUM_GPUS", "1")
_LOCAL_PATH_ROOTS = (
    WORKSPACE.resolve(),
    Path("/opt").resolve(),
    Path(os.environ.get("HOME", "/root")).expanduser().resolve(),
)

router = APIRouter(prefix="/dpipe", tags=["diffusion-pipe"])

# Process/bookkeeping
_proc_lock = threading.Lock()
_procs: dict[int, subprocess.Popen] = {}
_logs: dict[int, deque[str]] = {}
_LOG_MAX = 2000


def _ensure_dirs():
    for p in [MODEL_DIR, BASE_DATASET_DIR, OUTPUT_DIR, CONFIG_DIR, DPIPE_CONFIG_ROOT, DPIPE_OUTPUT_ROOT]:
        p.mkdir(parents=True, exist_ok=True)


def _deque_for(pid: int) -> deque[str]:
    if pid not in _logs:
        _logs[pid] = deque(maxlen=_LOG_MAX)
    return _logs[pid]


def _read_stream(proc: subprocess.Popen, pid: int):
    for raw in iter(proc.stdout.readline, b""):
        try:
            line = raw.decode("utf-8", errors="replace")
        except Exception:
            line = str(raw)
        with _proc_lock:
            _deque_for(pid).append(line.rstrip("\n"))
    proc.stdout.close()
    proc.wait()
    with _proc_lock:
        _procs.pop(pid, None)


def _resolve_diffpipe_dir() -> Path:
    app_train = DIFFPIPE_APP_DIR / "train.py"
    if DIFFPIPE_APP_DIR.exists() and app_train.exists():
        return DIFFPIPE_APP_DIR
    repo_train = DIFFPIPE_REPO_DIR / "train.py"
    if DIFFPIPE_REPO_DIR.exists() and repo_train.exists():
        return DIFFPIPE_REPO_DIR
    return DIFFPIPE_APP_DIR


def _path_is_within_root(candidate: Path, root: Path) -> bool:
    root_abs = os.path.realpath(str(root))
    candidate_abs = os.path.realpath(str(candidate))
    root_with_sep = os.path.join(root_abs, "")
    return candidate_abs == root_abs or candidate_abs.startswith(root_with_sep)


def _resolve_under_root(raw_value: str, *, root: Path, field: str) -> Path:
    raw = (raw_value or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail=f"{field} is required")
    root_abs = os.path.realpath(str(root))
    expanded = os.path.expandvars(os.path.expanduser(raw))
    if os.path.isabs(expanded):
        resolved = os.path.realpath(expanded)
    else:
        resolved = os.path.realpath(os.path.join(root_abs, expanded))
    if not _path_is_within_root(Path(resolved), Path(root_abs)):
        raise HTTPException(status_code=400, detail=f"{field} must stay within {root_abs}")
    return Path(resolved)


def _resolve_local_path(raw_value: str, *, field: str) -> Path:
    raw = (raw_value or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail=f"{field} is required")
    expanded = os.path.expandvars(os.path.expanduser(raw))
    if os.path.isabs(expanded):
        resolved = os.path.realpath(expanded)
    else:
        resolved = os.path.realpath(os.path.join(str(WORKSPACE), expanded))
    if not any(_path_is_within_root(Path(resolved), root) for root in _LOCAL_PATH_ROOTS):
        raise HTTPException(status_code=400, detail=f"{field} must stay within approved directories")
    return Path(resolved)


def _clean_name(value: str, *, default: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value or "").strip("_-")
    return cleaned or default


def _normalize_dataset_name(raw_value: str) -> str:
    raw = (raw_value or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="dataset_name is required")
    leaf = PurePosixPath(raw.replace("\\", "/")).name
    normalized = leaf[2:] if leaf.startswith("1_") else leaf
    return f"1_{_clean_name(normalized, default='dataset')}"


def _resolve_dataset_dir(dataset_name: str) -> Path:
    wanted = _normalize_dataset_name(dataset_name)
    try:
        with os.scandir(BASE_DATASET_DIR) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False) and entry.name == wanted:
                        return Path(entry.path).resolve()
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    raise HTTPException(status_code=404, detail="dataset not found")


def _load_run_registry() -> dict[str, dict[str, str]]:
    if not DPIPE_RUN_REGISTRY.exists():
        return {}
    try:
        raw = json.loads(DPIPE_RUN_REGISTRY.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {
                str(key): value
                for key, value in raw.items()
                if isinstance(key, str) and isinstance(value, dict)
            }
    except Exception:
        pass
    return {}


def _save_run_registry(registry: dict[str, dict[str, str]]) -> None:
    DPIPE_RUN_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    DPIPE_RUN_REGISTRY.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _managed_run_dirs(run_name: str, dataset_name: str) -> tuple[str, Path, Path]:
    safe_run_name = _clean_name(run_name or dataset_name, default="dpipe_run")
    registry = _load_run_registry()
    record = registry.get(safe_run_name)
    run_id = ""
    if record:
        run_id = _clean_name(str(record.get("run_id", "")), default="")
    if not run_id:
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        registry[safe_run_name] = {
            "dataset_name": dataset_name,
            "run_id": run_id,
            "run_name": safe_run_name,
        }
        _save_run_registry(registry)
    return safe_run_name, DPIPE_CONFIG_ROOT / run_id, DPIPE_OUTPUT_ROOT / run_id


def _resolve_deepspeed_bin() -> Path:
    binary = _resolve_local_path(DEEPSPEED_BIN, field="DEEPSPEED_BIN")
    if not binary.exists() or not binary.is_file():
        raise HTTPException(status_code=500, detail="deepspeed binary is unavailable")
    if not os.access(binary, os.X_OK):
        raise HTTPException(status_code=500, detail="deepspeed binary is not executable")
    return binary


def create_dataset_config(
    dataset_path: Path,
    config_dir: Path,
    num_repeats: int,
    resolutions: list,
    enable_ar_bucket: bool,
    min_ar: float,
    max_ar: float,
    num_ar_buckets: int,
    frame_buckets: list,
    ar_buckets: Optional[list],
) -> Path:
    cfg = {
        "resolutions": resolutions,
        "enable_ar_bucket": enable_ar_bucket,
        "min_ar": min_ar,
        "max_ar": max_ar,
        "num_ar_buckets": num_ar_buckets,
        "frame_buckets": frame_buckets,
        "ar_buckets": ar_buckets,
        "directory": [{"path": str(dataset_path), "num_repeats": num_repeats}],
    }
    config_dir.mkdir(parents=True, exist_ok=True)
    out = config_dir / "dataset_config.toml"
    with out.open("w") as f:
        toml.dump(cfg, f)
    return out


def create_training_config(
    output_dir: Path,
    config_dir: Path,
    dataset_config_path: Path,
    epochs: int,
    batch_size: int,
    gradient_accumulation_steps: int,
    gradient_clipping: float,
    warmup_steps: int,
    eval_every: int,
    eval_before_first_step: bool,
    eval_micro_batch_size_per_gpu: int,
    eval_gradient_accumulation_steps: int,
    save_every: int,
    checkpoint_every_n_minutes: int,
    activation_checkpointing: bool,
    partition_method: str,
    save_dtype: str,
    caching_batch_size: int,
    steps_per_print: int,
    video_clip_mode: str,
    transformer_path: str,
    vae_path: str,
    llm_path: str,
    clip_path: str,
    dtype: str,
    rank: int,
    only_double_blocks: bool,
    optimizer_type: str,
    lr: float,
    betas: list,
    weight_decay: float,
    eps: float,
    enable_wandb: bool,
    wandb_run_name: Optional[str],
    wandb_tracker_name: Optional[str],
    wandb_api_key: Optional[str],
) -> Path:
    num_gpus = int(NUM_GPUS)
    cfg = {
        "output_dir": str(output_dir),
        "dataset": str(dataset_config_path),
        "epochs": epochs,
        "micro_batch_size_per_gpu": batch_size,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "gradient_clipping": gradient_clipping,
        "warmup_steps": warmup_steps,
        "eval_every_n_epochs": eval_every,
        "eval_before_first_step": eval_before_first_step,
        "eval_micro_batch_size_per_gpu": eval_micro_batch_size_per_gpu,
        "eval_gradient_accumulation_steps": eval_gradient_accumulation_steps,
        "save_every_n_epochs": save_every,
        "checkpoint_every_n_minutes": checkpoint_every_n_minutes,
        "activation_checkpointing": activation_checkpointing,
        "partition_method": partition_method,
        "save_dtype": save_dtype,
        "caching_batch_size": caching_batch_size,
        "steps_per_print": steps_per_print,
        "video_clip_mode": video_clip_mode,
        "pipeline_stages": num_gpus,
        "model": {
            "type": "hunyuan-video",
            "transformer_path": transformer_path,
            "vae_path": vae_path,
            "llm_path": llm_path,
            "clip_path": clip_path,
            "dtype": dtype,
            "transformer_dtype": "float8",
            "timestep_sample_method": "logit_normal",
        },
        "adapter": {
            "type": "lora",
            "rank": rank,
            "dtype": dtype,
            "only_double_blocks": only_double_blocks,
        },
        "optimizer": {
            "type": optimizer_type,
            "lr": lr,
            "betas": betas,
            "weight_decay": weight_decay,
            "eps": eps,
        },
        "monitoring": {
            "log_dir": str(output_dir),
            "enable_wandb": enable_wandb,
            "wandb_run_name": wandb_run_name,
            "wandb_tracker_name": wandb_tracker_name,
            "wandb_api_key": wandb_api_key,
        },
    }
    config_dir.mkdir(parents=True, exist_ok=True)
    out = config_dir / "training_config.toml"
    with out.open("w") as f:
        toml.dump(cfg, f)
    return out


class TrainRequest(BaseModel):
    dataset_name: str
    run_name: str = ""
    epochs: int = 1000
    batch_size: int = 1
    lr: float = Field(2e-5, alias="learning_rate")
    save_every: int = 2
    eval_every: int = 1
    rank: int = 32
    dtype: str = "bfloat16"
    transformer_path: str
    vae_path: str
    llm_path: str
    clip_path: str
    optimizer_type: str = "adamw_optimi"
    betas: Union[str, list] = "[0.9, 0.99]"
    weight_decay: float = 0.01
    eps: float = 1e-8
    gradient_accumulation_steps: int = 4
    num_repeats: int = 10
    resolutions_input: str = "[512]"
    enable_ar_bucket: bool = True
    min_ar: float = 0.5
    max_ar: float = 2.0
    num_ar_buckets: int = 7
    ar_buckets: Optional[str] = ""
    frame_buckets: str = "[1, 33]"
    gradient_clipping: float = 1.0
    warmup_steps: int = 100
    eval_before_first_step: bool = True
    eval_micro_batch_size_per_gpu: int = 1
    eval_gradient_accumulation_steps: int = 1
    checkpoint_every_n_minutes: int = 120
    activation_checkpointing: bool = True
    partition_method: str = "parameters"
    save_dtype: str = "bfloat16"
    caching_batch_size: int = 1
    steps_per_print: int = 1
    video_clip_mode: str = "single_middle"
    resume_from_checkpoint: bool = False
    only_double_blocks: bool = False
    enable_wandb: bool = False
    wandb_run_name: Optional[str] = None
    wandb_tracker_name: Optional[str] = None
    wandb_api_key: Optional[str] = None


class TrainValidateRequest(BaseModel):
    transformer_path: str
    vae_path: str
    llm_path: str
    clip_path: str

def _parse_json_list(value: Union[str, list], *, field: str) -> list:
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON for {field}: {exc}")
    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail=f"{field} must be a JSON list")
    return parsed


def _parse_optional_json_list(value: Optional[str], *, field: str) -> Optional[list]:
    if value is None or str(value).strip() == "":
        return None
    return _parse_json_list(value, field=field)


@router.post("/train/validate")
def validate_training_paths(req: TrainValidateRequest):
    missing = []
    checks = {
        "transformer_path": req.transformer_path,
        "vae_path": req.vae_path,
        "llm_path": req.llm_path,
        "clip_path": req.clip_path,
    }
    for key, value in checks.items():
        path = _resolve_local_path(value, field=key)
        if not path.exists():
            missing.append({"field": key, "path": value})
    return {"ok": len(missing) == 0, "missing": missing}


def _ensure_single_run():
    with _proc_lock:
        if _procs:
            raise HTTPException(status_code=400, detail="A training process is already running.")


@router.post("/train/start")
def start_training(req: TrainRequest):
    _ensure_dirs()
    _ensure_single_run()

    ds_path = _resolve_dataset_dir(req.dataset_name)
    run_name, cfg_dir, out_dir = _managed_run_dirs(req.run_name, ds_path.name)
    deepspeed_bin = _resolve_deepspeed_bin()
    run_dir = _resolve_diffpipe_dir()
    if not run_dir.exists():
        raise HTTPException(status_code=500, detail=f"Diffusion-pipe dir missing: {run_dir}")
    if not (run_dir / "train.py").exists():
        raise HTTPException(status_code=500, detail=f"train.py not found in: {run_dir}")
    try:
        resolutions = _parse_json_list(req.resolutions_input, field="resolutions_input")
        frames = _parse_json_list(req.frame_buckets, field="frame_buckets")
        arb = _parse_optional_json_list(req.ar_buckets, field="ar_buckets")
        betas = _parse_json_list(req.betas, field="betas")
    except HTTPException:
        raise

    dataset_cfg = create_dataset_config(
        ds_path,
        cfg_dir,
        num_repeats=req.num_repeats,
        resolutions=resolutions,
        enable_ar_bucket=req.enable_ar_bucket,
        min_ar=req.min_ar,
        max_ar=req.max_ar,
        num_ar_buckets=req.num_ar_buckets,
        frame_buckets=frames,
        ar_buckets=arb,
    )
    training_cfg = create_training_config(
        output_dir=out_dir,
        config_dir=cfg_dir,
        dataset_config_path=dataset_cfg,
        epochs=req.epochs,
        batch_size=req.batch_size,
        gradient_accumulation_steps=req.gradient_accumulation_steps,
        gradient_clipping=req.gradient_clipping,
        warmup_steps=req.warmup_steps,
        eval_every=req.eval_every,
        eval_before_first_step=req.eval_before_first_step,
        eval_micro_batch_size_per_gpu=req.eval_micro_batch_size_per_gpu,
        eval_gradient_accumulation_steps=req.eval_gradient_accumulation_steps,
        save_every=req.save_every,
        checkpoint_every_n_minutes=req.checkpoint_every_n_minutes,
        activation_checkpointing=req.activation_checkpointing,
        partition_method=req.partition_method,
        save_dtype=req.save_dtype,
        caching_batch_size=req.caching_batch_size,
        steps_per_print=req.steps_per_print,
        video_clip_mode=req.video_clip_mode,
        transformer_path=req.transformer_path,
        vae_path=req.vae_path,
        llm_path=req.llm_path,
        clip_path=req.clip_path,
        dtype=req.dtype,
        rank=req.rank,
        only_double_blocks=req.only_double_blocks,
        optimizer_type=req.optimizer_type,
        lr=req.lr,
        betas=betas,
        weight_decay=req.weight_decay,
        eps=req.eps,
        enable_wandb=req.enable_wandb,
        wandb_run_name=req.wandb_run_name,
        wandb_tracker_name=req.wandb_tracker_name,
        wandb_api_key=req.wandb_api_key,
    )

    cmd = [
        str(deepspeed_bin),
        f"--num_gpus={NUM_GPUS}",
        "train.py",
        "--deepspeed",
        "--config",
        str(training_cfg),
    ]
    if req.resume_from_checkpoint:
        cmd.append("--resume_from_checkpoint")

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=run_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="deepspeed binary is unavailable")
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to start diffusion-pipe training")

    pid = proc.pid
    with _proc_lock:
        _procs[pid] = proc
        _deque_for(pid).clear()
    threading.Thread(target=_read_stream, args=(proc, pid), daemon=True).start()
    return {
        "status": "started",
        "pid": pid,
        "config": str(training_cfg),
        "dataset_name": ds_path.name,
        "output_dir": str(out_dir),
        "run_name": run_name,
    }


@router.post("/train/stop")
def stop_training(pid: Optional[int] = None):
    with _proc_lock:
        if pid is None:
            if not _procs:
                return {"status": "noop", "detail": "No training process tracked."}
            pid = next(iter(_procs))
        proc = _procs.get(pid)
    if proc is None:
        return {"status": "noop", "detail": "Process not found."}
    if proc.poll() is not None:
        with _proc_lock:
            _procs.pop(pid, None)
        return {"status": "stopped", "detail": "Process already exited."}
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()
    finally:
        with _proc_lock:
            _procs.pop(pid, None)
    return {"status": "stopped", "pid": pid}


@router.get("/train/logs")
def training_logs(pid: Optional[int] = None, limit: int = 500):
    with _proc_lock:
        if pid is None:
            if not _procs and not _logs:
                return {"pid": None, "lines": []}
            pid = next(iter(_logs)) if _logs else next(iter(_procs))
        lines = list(_deque_for(pid))[-limit:]
    return {"pid": pid, "lines": lines}
