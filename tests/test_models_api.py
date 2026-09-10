import io
import importlib.util
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.Portal import app as portal
from apps.Portal.services import model_downloads, models_api


class ModelsAPITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = self.root / "manifest"
        self.manifest.write_text("sample|hf_file|org/repo:sample.safetensors|checkpoints||14\n")
        self.token = Mock(return_value="")
        self.queue = model_downloads.ModelPullQueue(self.token, timeout=17)
        app = FastAPI()
        app.include_router(models_api.create_router(
            self.manifest, self.manifest, self.root / "models", self.root / "config",
            self.token, queue=self.queue))
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_catalog_and_invalid_download_requests(self):
        response = self.client.get("/api/models")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["name"], "sample")
        self.assertFalse(response.json()[0]["installed"])
        for name, status, detail in [("unknown", 404, "Unknown model"),
                                     ("bad;command", 400, "invalid model name"),
                                     ("%20", 400, "model name is required")]:
            for suffix in ["pull", "pull/start"]:
                response = self.client.post(f"/api/models/{name}/{suffix}")
                self.assertEqual((response.status_code, response.json()), (status, {"detail": detail}))

    def test_models_page_endpoints_with_packaged_workflow_paths(self):
        root = Path(__file__).resolve().parents[1]
        for directory in ("bundled/comfy-workflows", "config/comfy-workflows"):
            with self.subTest(directory=directory):
                package_root = self.root / directory.split("/")[0]
                module_path = package_root / "apps/Portal/services/model_install.py"
                module_path.parent.mkdir(parents=True)
                shutil.copyfile(root / "apps/Portal/services/model_install.py", module_path)
                shutil.copytree(root / "config/comfy-workflows", package_root / directory)
                spec = importlib.util.spec_from_file_location(
                    "apps.Portal.services.packaged_model_install", module_path)
                packaged = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(packaged)
                self.manifest.write_text((root / "config/models.manifest").read_text())
                with patch.object(models_api, "model_install", packaged), \
                     patch.object(packaged, "check_source", return_value={"error": "Offline test"}), \
                     TestClient(self.client.app, raise_server_exceptions=False) as client:
                    for endpoint in ("/api/models", "/api/models/pulls", "/api/models/workflows"):
                        response = client.get(endpoint)
                        self.assertEqual(response.status_code, 200, endpoint)
                        if endpoint == "/api/models":
                            self.assertGreater(len(response.json()), 100)
                        elif endpoint.endswith("workflows"):
                            self.assertEqual(len(response.json()["workflows"]), 4)
                    plan = client.post(
                        "/api/models/workflows/video_ltx2_5_t2v/plan", json={})
                    self.assertEqual(plan.status_code, 200)
                    self.assertEqual(len(plan.json()["files"]), 5)

    def test_synchronous_pull_output_and_error_contract(self):
        with patch.object(self.queue, "run_command", return_value="download complete\n") as run:
            response = self.client.post("/api/models/sample/pull")
            self.assertEqual(response.json(), {"status": "ok", "output": "download complete\n"})
            run.assert_called_once_with(["/opt/pilot/get-models.sh", "pull", "sample"])
        with patch.object(self.queue, "run_command", side_effect=RuntimeError("provider failure")):
            response = self.client.post("/api/models/sample/pull")
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json(), {"detail": "Model pull failed"})

    def test_background_start_status_list_and_deduplication(self):
        self.assertEqual(self.client.get("/api/models/sample/pull/status").json(), {"name": "sample", "state": "idle"})
        with patch.object(model_downloads, "Thread") as thread:
            first = self.client.post("/api/models/sample/pull/start")
            second = self.client.post("/api/models/sample/pull/start")
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.json(), second.json())
            self.assertEqual(set(first.json()), {"name", "state", "pid", "progress_pct", "last_line", "error", "started_at", "updated_at", "output_tail"})
            self.assertEqual(first.json()["state"], "running")
            thread.assert_called_once()
            self.assertEqual(self.client.get("/api/models/sample/pull/status").json(), first.json())
            self.assertEqual(self.client.get("/api/models/pulls").json(), {"jobs": [first.json()]})
            self.queue.jobs["sample"].state = "queued"
            self.assertEqual(self.client.post("/api/models/sample/pull/start").json()["state"], "queued")
            thread.assert_called_once()

    def test_delete_files_unknown_models_and_active_downloads(self):
        self.client.get("/api/models")
        path = self.root / "models/checkpoints/sample.safetensors"
        path.write_bytes(b"complete model")
        for state in ["running", "queued"]:
            self.queue.jobs["sample"] = model_downloads.ModelPullJob(name="sample", state=state)
            response = self.client.post("/api/models/sample/delete")
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json(), {"detail": "Wait for this model download to finish before removing it."})
            self.assertTrue(path.exists())
        self.queue.jobs["sample"].state = "done"
        self.assertEqual(self.client.post("/api/models/sample/delete").json(), {"status": "ok", "deleted": 1})
        self.assertFalse(path.exists())
        response = self.client.post("/api/models/unknown/delete")
        self.assertEqual((response.status_code, response.json()), (404, {"detail": "Unknown model"}))

    def test_workflow_catalog_plan_errors_and_body_validation(self):
        self.assertEqual(len(self.client.get("/api/models/workflows").json()["workflows"]), 4)
        base = "/api/models/workflows/video_ltx2_5_t2v"
        for payload in [None, {"optional": "wrong type"}]:
            self.assertEqual(self.client.post(base + "/plan", json=payload).status_code, 422)
        response = self.client.post("/api/models/workflows/unknown/plan", json={})
        self.assertEqual((response.status_code, response.json()), (400, {"detail": "Unknown bundled workflow"}))
        self.assertEqual(self.client.post(base + "/plan", json={"optional": ["unknown"]}).status_code, 400)
        plan = self.client.post(base + "/plan", json={}).json()
        self.assertFalse(plan["can_install"])
        self.assertEqual(len(plan["files"]), 5)
        response = self.client.post(base + "/install", json={})
        self.assertEqual((response.status_code, response.json()), (409, {"detail": "Installation plan changed. Review installation again."}))
        response = self.client.post(base + "/install", json={"plan_id": plan["plan_id"]})
        self.assertEqual((response.status_code, response.json()), (409, {"detail": "Installation checks failed. Review installation again."}))

    def test_queue_ttl_sorting_and_instance_isolation(self):
        now = time.time()
        for name, state, age in [("old", "done", 601), ("error", "error", 601),
                                 ("queued", "queued", 900), ("active", "running", 800), ("recent", "done", 5)]:
            self.queue.jobs[name] = model_downloads.ModelPullJob(name=name, state=state, updated_at=now - age)
        self.assertEqual([j["name"] for j in self.queue.list_jobs()["jobs"]], ["recent", "active", "queued"])
        self.assertEqual(model_downloads.ModelPullQueue(self.token).list_jobs(), {"jobs": []})

    def test_downloader_receives_current_token_and_configured_sync_timeout(self):
        job = model_downloads.ModelPullJob(name="sample")
        process = SimpleNamespace(pid=123, stdout=io.BytesIO(b"100%\n"), wait=lambda: 0)
        self.token.return_value = "updated-test-token"
        with patch.object(model_downloads.subprocess, "Popen", return_value=process) as popen:
            self.queue.run_job(job, ["fake"])
            self.assertEqual(popen.call_args.kwargs["env"]["HF_TOKEN"], "updated-test-token")
        with patch.object(model_downloads.subprocess, "run", side_effect=subprocess.TimeoutExpired("fake", 17)) as run:
            with self.assertRaisesRegex(RuntimeError, "Timeout running model pull"):
                self.queue.run_command(["fake"])
            self.assertEqual(run.call_args.kwargs["timeout"], 17)

    def test_portal_router_remains_authenticated_and_uncached(self):
        client = TestClient(portal.app)
        self.addCleanup(client.close)
        with patch.object(portal, "_controlpilot_request_authenticated", return_value=False):
            for method, url in [("GET", "/api/models"), ("GET", "/api/models/pulls"),
                                ("POST", "/api/models/sample/pull/start"),
                                ("POST", "/api/models/workflows/video_ltx2_5_t2v/install")]:
                response = client.request(method, url, json={})
                self.assertEqual((response.status_code, response.json()), (401, {"detail": "ControlPilot password required"}))
        with patch.object(portal, "_controlpilot_request_authenticated", return_value=True), patch.object(models_api.models_service, "parse_manifest", return_value=[]):
            response = client.get("/api/models")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
            self.assertIn("no-store", response.headers["Cache-Control"])
            with patch.object(portal, "_read_secret_env_var", return_value="fresh-token"), patch.object(models_api.model_install, "installation_plan", return_value={}) as plan:
                client.post("/api/models/workflows/video_ltx2_5_t2v/plan", json={})
                self.assertEqual(plan.call_args.args[-1], "fresh-token")
