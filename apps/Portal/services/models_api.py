"""Models HTTP API. Paths and secret access are supplied by the Portal host."""
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import model_install, models as models_service
from .model_downloads import DownloadActiveError, ModelPullQueue


class WorkflowInstallRequest(BaseModel):
    optional: List[str] = []
    plan_id: Optional[str] = None


def _normalize_model_name(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="model name is required")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", raw):
        raise HTTPException(status_code=400, detail="invalid model name")
    return raw


def _resolve_model_name(raw: str, entries: list[models_service.ModelEntry]) -> str:
    normalized = _normalize_model_name(raw)
    for entry in entries:
        if entry.name == normalized:
            return entry.name
    raise HTTPException(status_code=404, detail="Unknown model")


def create_router(
    manifest: Path,
    default_manifest: Path,
    models_dir: Path,
    config_dir: Path,
    token_reader: Callable[[], str],
    pull_timeout: int = 1200,
    queue: Optional[ModelPullQueue] = None,
) -> APIRouter:
    router = APIRouter()
    if queue is None:
        queue = ModelPullQueue(token_reader, timeout=pull_timeout)

    @router.get("/api/models", response_model=List[models_service.ModelEntry])
    def list_models():
        return models_service.parse_manifest(
            manifest,
            default_manifest,
            models_dir,
            config_dir,
        )

    @router.get("/api/models/workflows")
    def model_workflows():
        return {"workflows": model_install.catalog()}

    @router.post("/api/models/workflows/{workflow_id}/plan")
    def plan_model_workflow(workflow_id: str, payload: WorkflowInstallRequest):
        try:
            return model_install.installation_plan(
                workflow_id, payload.optional, list_models(), models_dir, token_reader())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/api/models/workflows/{workflow_id}/install")
    def install_model_workflow(workflow_id: str, payload: WorkflowInstallRequest):
        plan = plan_model_workflow(workflow_id, payload)
        if not payload.plan_id or payload.plan_id != plan["plan_id"]:
            raise HTTPException(status_code=409, detail="Installation plan changed. Review installation again.")
        if not plan["can_install"]:
            raise HTTPException(status_code=409, detail="Installation checks failed. Review installation again.")
        names = [item["model_name"] for item in plan["files"] if item["state"] != "installed"]
        jobs = queue.start_workflow(names, lambda name: any(m.name == name and m.installed for m in list_models()))
        return {"jobs": jobs, "installed_count": plan["installed_count"]}

    @router.post("/api/models/{name}/pull")
    def pull_model(name: str):
        models_service.ensure_manifest(manifest, default_manifest, models_dir, config_dir)
        entries = models_service.parse_manifest(manifest, default_manifest, models_dir, config_dir)
        model_name = _resolve_model_name(name, entries)
        cmd = ["/opt/pilot/get-models.sh", "pull", model_name]
        print(f"[models] pull start name={model_name} cmd={' '.join(cmd)}", file=sys.stderr)
        try:
            output = queue.run_command(cmd)
            tail = output[-4000:] if len(output) > 4000 else output
            print(f"[models] pull ok name={name} output_tail={tail!r}", file=sys.stderr)
            return {"status": "ok", "output": output}
        except Exception as e:
            output = str(e)
            tail = output[-4000:] if len(output) > 4000 else output
            print(f"[models] pull failed name={name} output_tail={tail!r}", file=sys.stderr)
            raise HTTPException(status_code=500, detail="Model pull failed")

    @router.post("/api/models/{name}/pull/start")
    def pull_model_start(name: str):
        """Start a model pull in the background (used by UI for progress updates)."""
        queue.cleanup()
        models_service.ensure_manifest(manifest, default_manifest, models_dir, config_dir)
        entries = models_service.parse_manifest(manifest, default_manifest, models_dir, config_dir)
        model_name = _resolve_model_name(name, entries)

        return queue.start(model_name, job_key=name)

    @router.get("/api/models/{name}/pull/status")
    def pull_model_status(name: str):
        return queue.status(name)

    @router.get("/api/models/pulls")
    def list_model_pulls():
        """List recent model pull jobs (running + recently completed/failed)."""
        return queue.list_jobs()

    @router.post("/api/models/{name}/delete")
    def delete_model(name: str):
        models_service.ensure_manifest(manifest, default_manifest, models_dir, config_dir)
        try:
            deleted = queue.delete_when_idle(name, lambda: models_service.delete_model(name, manifest, models_dir))
        except DownloadActiveError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except KeyError:
            raise HTTPException(status_code=404, detail="Unknown model")
        return {"status": "ok", "deleted": deleted}

    return router
