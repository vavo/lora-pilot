import os
import subprocess
import threading
import time
import json
from typing import Optional
from pathlib import Path

from . import runpod

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
    action: Optional[str] = None
    notice: Optional[str] = None


shutdown_scheduled = False
shutdown_state = "idle"
shutdown_error = None
shutdown_time = None
shutdown_thread = None
shutdown_plan = None
shutdown_lock = threading.Lock()
_shutdown_wake_event = threading.Event()


def _runpod_shutdown_plan():
    identifier = runpod.pod_id()
    if not identifier:
        return None
    pod = runpod.client.pod(identifier, fresh=True)
    settings_path = os.environ.get("CONTROLPILOT_SETTINGS_PATH", str(Path(os.environ.get("WORKSPACE_ROOT", "/workspace")) / "config/controlpilot-settings.json"))
    try:
        mode = json.loads(Path(settings_path).read_text()).get("shutdown_mode", "")
    except (OSError, ValueError, AttributeError):
        mode = ""
    mode = str(mode or os.environ.get("RUNPOD_POD_SHUTDOWN", "")).strip().lower()
    if mode in {"remove", "terminate", "delete"}:
        action = "terminate"
    elif mode in {"stop", "halt"}:
        action = "stop"
    else:
        mount = runpod.workspace_mount(os.environ.get("WORKSPACE_ROOT", "/workspace"), pod)
        action = "terminate" if mount and mount[0] == "network" else "stop"
    _require_action(pod, action)
    notice = ("Terminate deletes the pod and its local storage. Attached network volumes are retained."
              if action == "terminate" else "Stop releases compute and keeps the pod available to restart. Storage charges may continue.")
    return {"pod_id": identifier, "action": action, "notice": notice}


def _require_action(pod, action):
    actions = pod.get("actions")
    if pod.get("locked") or not isinstance(actions, list) or action not in actions:
        raise runpod.RunpodError("conflict", "The pod is locked or cannot perform the selected shutdown action.", 409)


def _execute_shutdown(plan):
    if plan is not None:
        # Recheck eligibility, but never recalculate or switch the scheduled action.
        pod = runpod.client.pod(plan["pod_id"], fresh=True)
        _require_action(pod, plan["action"])
        runpod.client.action(plan["pod_id"], plan["action"])
        return
    result = subprocess.run(["shutdown", "-h", "now"], check=False, timeout=60, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Local shutdown command failed. Check system permissions.")


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
                plan = shutdown_plan
                break
        _shutdown_wake_event.wait(timeout=min(5.0, max(0.1, remaining)))
        _shutdown_wake_event.clear()

    error = None
    try:
        _execute_shutdown(plan)
    except runpod.RunpodError as exc:
        error = str(exc)
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
    global shutdown_scheduled, shutdown_time, shutdown_thread, shutdown_state, shutdown_error, shutdown_plan

    multipliers = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}
    if request.unit not in multipliers:
        raise HTTPException(
            status_code=400,
            detail="Invalid unit. Must be: seconds, minutes, hours, days",
        )

    delay_seconds = request.value * multipliers[request.unit]
    if delay_seconds <= 0:
        raise HTTPException(status_code=422, detail="Choose a positive shutdown delay")
    with shutdown_lock:
        if shutdown_state == "executing":
            raise HTTPException(status_code=409, detail="Shutdown is already executing")
    try:
        plan = _runpod_shutdown_plan()
    except runpod.RunpodError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from None

    with shutdown_lock:
        if shutdown_state == "executing":
            raise HTTPException(status_code=409, detail="Shutdown is already executing")
        shutdown_plan = plan
        shutdown_state = "scheduled"
        shutdown_error = None
        shutdown_scheduled = True
        shutdown_time = time.time() + delay_seconds
        _shutdown_wake_event.set()

        if shutdown_thread is None or not shutdown_thread.is_alive():
            shutdown_thread = threading.Thread(target=shutdown_worker, daemon=True)
            shutdown_thread.start()


def cancel_shutdown() -> None:
    global shutdown_scheduled, shutdown_time, shutdown_thread, shutdown_state, shutdown_error, shutdown_plan

    with shutdown_lock:
        if shutdown_state == "executing":
            raise HTTPException(status_code=409, detail="Shutdown is already executing")
        shutdown_plan = None
        shutdown_state = "idle"
        shutdown_error = None
        shutdown_scheduled = False
        shutdown_time = None
        _shutdown_wake_event.set()


def get_shutdown_status() -> ShutdownStatus:
    """Get the current shutdown status."""
    global shutdown_scheduled, shutdown_time

    with shutdown_lock:
        plan_fields = {key: shutdown_plan.get(key) for key in ("action", "notice")} if shutdown_plan else {}
        if not shutdown_scheduled or shutdown_time is None:
            return ShutdownStatus(scheduled=False, state=shutdown_state, error=shutdown_error, **plan_fields)

        time_remaining = max(0, int(shutdown_time - time.time()))
        shutdown_time_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(shutdown_time))

        return ShutdownStatus(
            scheduled=True,
            state=shutdown_state,
            error=shutdown_error,
            time_remaining=time_remaining,
            shutdown_time=shutdown_time_str,
            **plan_fields,
        )
