#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


DEFAULT_HOME = Path(os.environ.get("COPILOT_HOME", "/workspace/home/root"))
DEFAULT_XDG_CONFIG_HOME = Path(os.environ.get("COPILOT_XDG_CONFIG_HOME", "/workspace/home/root/.config"))
DEFAULT_CWD = Path(os.environ.get("COPILOT_CWD", "/workspace"))
DEFAULT_PORT = int(os.environ.get("COPILOT_SIDECAR_PORT", "7879"))
DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("COPILOT_TIMEOUT_SECONDS", "1800"))


def _copilot_bin() -> Optional[str]:
    return shutil.which("copilot")


def _config_json_path() -> Path:
    """
    Copilot CLI config defaults to ~/.copilot/config.json, and docs mention XDG_CONFIG_HOME can relocate it.
    We follow that by storing under $XDG_CONFIG_HOME/.copilot/config.json when XDG_CONFIG_HOME is set.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / ".copilot" / "config.json"
    home = Path(os.environ.get("HOME", str(DEFAULT_HOME)))
    return home / ".copilot" / "config.json"


def _ensure_trusted_folder(folder: Path) -> None:
    cfg_path = _config_json_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg: Dict[str, Any] = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            # Don't risk clobbering an existing (possibly non-JSON) config/auth store.
            return
    trusted = cfg.get("trusted_folders")
    if not isinstance(trusted, list):
        trusted = []
    folder_str = str(folder.resolve())
    if folder_str not in trusted:
        trusted.append(folder_str)
    cfg["trusted_folders"] = trusted
    cfg_path.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class ChatRequest(BaseModel):
    prompt: str
    cwd: Optional[str] = None
    allow_all_tools: bool = True
    allow_all_paths: bool = True
    allow_all_urls: bool = False
    timeout_seconds: Optional[int] = None


class ChatResponse(BaseModel):
    ok: bool
    returncode: int
    duration_seconds: float
    stdout: str
    stderr: str
    command: list[str]


app = FastAPI(title="LoRA Pilot Copilot Sidecar", docs_url=None, redoc_url=None)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/status")
def status():
    copilot = _copilot_bin()
    out: Dict[str, Any] = {
        "copilot_in_path": bool(copilot),
        "copilot_path": copilot,
        "home": os.environ.get("HOME", str(DEFAULT_HOME)),
        "xdg_config_home": os.environ.get("XDG_CONFIG_HOME", str(DEFAULT_XDG_CONFIG_HOME)),
        "cwd": str(DEFAULT_CWD),
        "config_json": str(_config_json_path()),
        "config_exists": _config_json_path().exists(),
        "port": DEFAULT_PORT,
        "env_has_token": any(
            bool(os.environ.get(k))
            for k in ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
        ),
    }
    # Best-effort auth detection (do not return secrets)
    if out["config_exists"]:
        try:
            cfg = json.loads(_config_json_path().read_text(encoding="utf-8"))
            token_like = [
                cfg.get("oauth_token"),
                cfg.get("github_token"),
                cfg.get("token"),
            ]
            out["config_has_token_like_field"] = any(
                isinstance(v, str) and v.strip() for v in token_like
            )
        except Exception:
            out["config_has_token_like_field"] = False
    if copilot:
        try:
            p = subprocess.run([copilot, "--version"], capture_output=True, text=True, check=False)
            out["copilot_version"] = (p.stdout or p.stderr or "").strip()
        except Exception as e:
            out["copilot_version_error"] = str(e)
    return out


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    copilot = _copilot_bin()
    if not copilot:
        raise HTTPException(status_code=503, detail="copilot CLI not found in PATH")
    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    cwd = Path(req.cwd) if req.cwd else DEFAULT_CWD
    cwd = cwd.resolve()
    if not str(cwd).startswith("/workspace"):
        raise HTTPException(status_code=400, detail="cwd must be under /workspace")

    _ensure_trusted_folder(cwd)

    cmd = [copilot, "-p", prompt]
    if req.allow_all_tools:
        cmd.append("--allow-all-tools")
    if req.allow_all_paths:
        cmd.append("--allow-all-paths")
    if req.allow_all_urls:
        cmd.append("--allow-all-urls")

    env = os.environ.copy()
    env.setdefault("HOME", str(DEFAULT_HOME))
    env.setdefault("XDG_CONFIG_HOME", str(DEFAULT_XDG_CONFIG_HOME))

    timeout = int(req.timeout_seconds or DEFAULT_TIMEOUT_SECONDS)
    t0 = time.time()
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        dt = time.time() - t0
        return ChatResponse(
            ok=False,
            returncode=124,
            duration_seconds=dt,
            stdout=e.stdout or "",
            stderr=(e.stderr or "") + f"\nTimed out after {timeout}s\n",
            command=cmd,
        )

    dt = time.time() - t0
    return ChatResponse(
        ok=p.returncode == 0,
        returncode=int(p.returncode),
        duration_seconds=dt,
        stdout=p.stdout or "",
        stderr=p.stderr or "",
        command=cmd,
    )
