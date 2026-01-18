import json
import os
import signal
import subprocess
import threading
from collections import deque
from pathlib import Path
from typing import List, Optional, Union

import toml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

# Paths aligned with the runtime layout
WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
MODEL_DIR = WORKSPACE / "models"
BASE_DATASET_DIR = WORKSPACE / "datasets"
OUTPUT_DIR = WORKSPACE / "outputs"
CONFIG_DIR = WORKSPACE / "configs"
DIFFPIPE_APP_DIR = WORKSPACE / "apps" / "diffusion-pipe"

# Deepspeed entrypoint (assumed installed in core venv)
DEEPSPEED_BIN = os.environ.get("DEEPSPEED_BIN", "/opt/venvs/core/bin/deepspeed")
NUM_GPUS = os.environ.get("NUM_GPUS", "1")

router = APIRouter(prefix="/dpipe", tags=["diffusion-pipe"])

# Process/bookkeeping
_proc_lock = threading.Lock()
_procs: dict[int, subprocess.Popen] = {}
_logs: dict[int, deque[str]] = {}
_LOG_MAX = 2000


def _ensure_dirs():
    for p in [MODEL_DIR, BASE_DATASET_DIR, OUTPUT_DIR, CONFIG_DIR]:
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
    dataset_path: str
    config_dir: str
    output_dir: str
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

    @validator("betas")
    def _parse_betas(cls, v):
        if isinstance(v, list):
            return v
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, list):
                raise ValueError
            return parsed
        except Exception:
            raise ValueError("betas must be a JSON list, e.g. [0.9, 0.99]")

    @validator("resolutions_input")
    def _parse_resolutions(cls, v):
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, list):
                raise ValueError
            return v
        except Exception:
            raise ValueError("resolutions_input must be JSON, e.g. [512] or [[512,512]]")

    @validator("frame_buckets")
    def _parse_frames(cls, v):
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, list):
                raise ValueError
            return v
        except Exception:
            raise ValueError("frame_buckets must be JSON list, e.g. [1,33]")

    @validator("ar_buckets")
    def _parse_ar(cls, v):
        if not v:
            return ""
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, list):
                raise ValueError
            return v
        except Exception:
            raise ValueError("ar_buckets must be JSON list or empty string")


def _ensure_single_run():
    with _proc_lock:
        if _procs:
            raise HTTPException(status_code=400, detail="A training process is already running.")


@router.post("/train/start")
def start_training(req: TrainRequest):
    _ensure_dirs()
    _ensure_single_run()

    ds_path = Path(req.dataset_path)
    # Constrain config_dir to a subdirectory under WORKSPACE to avoid arbitrary path usage.
    base_cfg_root = (WORKSPACE / "configs").resolve()
    user_cfg_component = Path(req.config_dir)
    # Prevent absolute paths and normalize to avoid path traversal (e.g., "..").
    if user_cfg_component.is_absolute():
        raise HTTPException(status_code=400, detail="config_dir must be a relative path or name")
    cfg_dir = (base_cfg_root / user_cfg_component).resolve()
    try:
        cfg_dir.relative_to(base_cfg_root)
    except ValueError:
        raise HTTPException(status_code=400, detail="config_dir is invalid")
    cfg_dir.mkdir(parents=True, exist_ok=True)

    out_dir = Path(req.output_dir)
    if not ds_path.exists():
        raise HTTPException(status_code=400, detail="dataset_path does not exist")
    if not DIFFPIPE_APP_DIR.exists():
        raise HTTPException(status_code=500, detail=f"Diffusion-pipe app dir missing: {DIFFPIPE_APP_DIR}")
    try:
        resolutions = json.loads(req.resolutions_input)
        frames = json.loads(req.frame_buckets)
        arb = json.loads(req.ar_buckets) if req.ar_buckets else None
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in resolutions/frame/ar buckets: {e}")

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
        betas=req._parse_betas(req.betas),
        weight_decay=req.weight_decay,
        eps=req.eps,
        enable_wandb=req.enable_wandb,
        wandb_run_name=req.wandb_run_name,
        wandb_tracker_name=req.wandb_tracker_name,
        wandb_api_key=req.wandb_api_key,
    )

    cmd = [
        DEEPSPEED_BIN,
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
            cwd=DIFFPIPE_APP_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"deepspeed not found at {DEEPSPEED_BIN}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    pid = proc.pid
    with _proc_lock:
        _procs[pid] = proc
        _deque_for(pid).clear()
    threading.Thread(target=_read_stream, args=(proc, pid), daemon=True).start()
    return {"status": "started", "pid": pid, "config": str(training_cfg)}


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
                raise HTTPException(status_code=404, detail="No process/logs available")
            pid = next(iter(_logs)) if _logs else next(iter(_procs))
        lines = list(_deque_for(pid))[-limit:]
    return {"pid": pid, "lines": lines}
