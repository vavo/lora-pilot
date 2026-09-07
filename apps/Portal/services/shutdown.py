import os
import subprocess
import threading
import time
import json
from typing import Optional, Tuple, List

from fastapi import HTTPException
from pydantic import BaseModel


class ShutdownRequest(BaseModel):
    value: int
    unit: str  # "seconds", "minutes", "hours", "days"


class ShutdownStatus(BaseModel):
    scheduled: bool
    state: str = "idle"
    error: Optional[str] = None
    time_remaining: Optional[int] = None  # seconds remaining
    shutdown_time: Optional[str] = None  # ISO timestamp


shutdown_scheduled = False
shutdown_state = "idle"
shutdown_error = None
shutdown_time = None
shutdown_thread = None
shutdown_lock = threading.Lock()
_shutdown_wake_event = threading.Event()


def _runpod_shutdown_command() -> Tuple[Optional[List[str]], Optional[str], str]:
    pod_id = os.environ.get("RUNPOD_POD_ID", "").strip()
    if not pod_id:
        return None, None, ""

    mode = ""
    settings_path = os.environ.get("CONTROLPILOT_SETTINGS_PATH", "/workspace/config/controlpilot-settings.json")
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        mode = str(data.get("shutdown_mode", "") or "").strip().lower()
    except Exception:
        mode = ""
    if not mode:
        mode = os.environ.get("RUNPOD_POD_SHUTDOWN", "").strip().lower()
    if mode in ("remove", "terminate", "delete"):
        return ["runpodctl", "remove", "pod", pod_id], "remove", pod_id
    if mode in ("stop", "halt"):
        return ["runpodctl", "stop", "pod", pod_id], "stop", pod_id

    volume_type = os.environ.get("RUNPOD_VOLUME_TYPE", "").strip().lower()
    if volume_type in ("network", "network-volume", "nfs", "volume"):
        return ["runpodctl", "remove", "pod", pod_id], "remove", pod_id
    if volume_type in ("local", "local-storage", "ephemeral", "local-ssd"):
        return ["runpodctl", "stop", "pod", pod_id], "stop", pod_id

    if os.environ.get("RUNPOD_NETWORK_VOLUME_ID"):
        return ["runpodctl", "remove", "pod", pod_id], "remove", pod_id

    return ["runpodctl", "stop", "pod", pod_id], "stop", pod_id


def shutdown_worker():
    global shutdown_scheduled, shutdown_time, shutdown_thread, shutdown_state, shutdown_error

    while True:
        with shutdown_lock:
            if not shutdown_scheduled or shutdown_time is None:
                shutdown_thread = None
                return
            remaining = shutdown_time - time.time()
            if remaining <= 0:
                shutdown_scheduled = False
                shutdown_state = "executing"
                break
        _shutdown_wake_event.wait(timeout=min(5.0, max(0.1, remaining)))
        _shutdown_wake_event.clear()

    error = None
    try:
        cmd, _mode, _pod_id = _runpod_shutdown_command()
        cmd = cmd or ["shutdown", "-h", "now"]
        result = subprocess.run(cmd, check=False, timeout=60, capture_output=True, text=True)
        if result.returncode != 0:
            error = f"Shutdown command failed (exit {result.returncode}). Check the pod credentials and retry."
    except FileNotFoundError:
        error = "Shutdown command is unavailable. The pod has not been stopped."
    except subprocess.TimeoutExpired:
        error = "Shutdown command timed out. Check the pod status before retrying."
    except Exception:
        error = "Shutdown failed. Check the pod status before retrying."
    finally:
        with shutdown_lock:
            shutdown_error = error
            shutdown_state = "failed" if error else "requested"
            shutdown_thread = None


def schedule_shutdown(request: ShutdownRequest) -> None:
    global shutdown_scheduled, shutdown_time, shutdown_thread, shutdown_state, shutdown_error

    multipliers = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}
    if request.unit not in multipliers:
        raise HTTPException(
            status_code=400,
            detail="Invalid unit. Must be: seconds, minutes, hours, days",
        )

    delay_seconds = request.value * multipliers[request.unit]

    with shutdown_lock:
        if shutdown_state == "executing":
            raise HTTPException(status_code=409, detail="Shutdown is already executing")
        shutdown_state = "scheduled"
        shutdown_error = None
        shutdown_scheduled = True
        shutdown_time = time.time() + delay_seconds
        _shutdown_wake_event.set()

        if shutdown_thread is None or not shutdown_thread.is_alive():
            shutdown_thread = threading.Thread(target=shutdown_worker, daemon=True)
            shutdown_thread.start()


def cancel_shutdown() -> None:
    global shutdown_scheduled, shutdown_time, shutdown_thread, shutdown_state, shutdown_error

    with shutdown_lock:
        if shutdown_state == "executing":
            raise HTTPException(status_code=409, detail="Shutdown is already executing")
        shutdown_state = "idle"
        shutdown_error = None
        shutdown_scheduled = False
        shutdown_time = None
        _shutdown_wake_event.set()


def get_shutdown_status() -> ShutdownStatus:
    """Get the current shutdown status."""
    global shutdown_scheduled, shutdown_time

    with shutdown_lock:
        if not shutdown_scheduled or shutdown_time is None:
            return ShutdownStatus(scheduled=False, state=shutdown_state, error=shutdown_error)

        time_remaining = max(0, int(shutdown_time - time.time()))
        shutdown_time_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(shutdown_time))

        return ShutdownStatus(
            scheduled=True,
            state=shutdown_state,
            error=shutdown_error,
            time_remaining=time_remaining,
            shutdown_time=shutdown_time_str,
        )
