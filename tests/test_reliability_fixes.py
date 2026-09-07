import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from apps.Portal.services import models
try:
    import httpx
    from fastapi import UploadFile
    from apps.Portal import app as portal
    from apps.Portal.services import shutdown
except ModuleNotFoundError as exc:
    if exc.name not in {"fastapi", "httpx"}:
        raise
    portal = None

ROOT = Path(__file__).resolve().parents[1]


class BundleSyncTests(unittest.TestCase):
    def test_refresh_preserves_user_files_and_prunes_only_owned_unchanged_files(self):
        spec = importlib.util.spec_from_file_location("bundle_sync", ROOT / "scripts/bundle-sync.py")
        bundle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bundle)
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "source", Path(tmp) / "target"
            source.mkdir(); target.mkdir()
            (source / "main.py").write_text("version one")
            (source / "obsolete.py").write_text("old code")
            (source / "edited.py").write_text("original")
            (target / "comfy_upscale_workflow.json").write_text("custom workflow")
            (target / ".env").write_text("custom settings")
            # Migrate a copy that only has the old tree-level marker.
            (target / ".bundle-sync-sha").write_text("old hash")
            bundle.sync_bundle(source, target)
            (target / "edited.py").write_text("user edit")
            (source / "edited.py").write_text("new bundled version")
            (source / "main.py").write_text("version two")
            (source / "obsolete.py").unlink()
            bundle.sync_bundle(source, target)
            self.assertEqual((target / "main.py").read_text(), "version two")
            self.assertFalse((target / "obsolete.py").exists())
            self.assertEqual((target / "edited.py").read_text(), "user edit")
            self.assertEqual((target / "comfy_upscale_workflow.json").read_text(), "custom workflow")
            self.assertEqual((target / ".env").read_text(), "custom settings")
            (source / "edited.py").unlink()
            bundle.sync_bundle(source, target)
            self.assertEqual((target / "edited.py").read_text(), "user edit")


@unittest.skipIf(portal is None, "Portal test dependencies unavailable")
class DatasetUploadTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        for name, value in [("WORKSPACE_ROOT", self.root), ("_DATASET_ROOT", self.root / "datasets"),
                            ("_DATASET_ZIP_ROOT", self.root / "datasets/ZIPs")]:
            self.stack.enter_context(patch.object(portal, name, value))
        self.dataset = self.root / "datasets/1_sample"
        self.dataset.mkdir(parents=True)
        (self.dataset / "original.jpg").write_bytes(b"original")
        self.archive = self.root / "datasets/ZIPs/sample.zip"
        self.archive.parent.mkdir()
        self.archive.write_bytes(b"original archive")

    def upload(self, contents=None):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            for name, content in (contents or {"new.jpg": b"replacement"}).items():
                archive.writestr(name, content)
        data.seek(0)
        return UploadFile(filename="sample.zip", file=data)

    def assert_original(self):
        self.assertEqual((self.dataset / "original.jpg").read_bytes(), b"original")
        self.assertEqual(self.archive.read_bytes(), b"original archive")
        self.assertEqual(list(self.archive.parent.glob(".upload-*")), [])

    def test_invalid_and_unsafe_archives_preserve_existing_dataset_and_zip(self):
        for upload in [UploadFile(filename="sample.zip", file=io.BytesIO(b"invalid")),
                       self.upload({"valid.jpg": b"new", "../escape": b"bad"})]:
            with self.subTest(upload=upload), self.assertRaises(portal.HTTPException) as error:
                portal.upload_dataset(upload)
            self.assertEqual(error.exception.status_code, 400)
            self.assert_original()

    def test_failed_upload_size_check_preserves_existing_archive(self):
        with patch.object(portal, "DATASET_UPLOAD_MAX_BYTES", 1):
            with self.assertRaises(portal.HTTPException) as error:
                portal.upload_dataset(self.upload())
        self.assertEqual(error.exception.status_code, 413)
        self.assert_original()

    def test_valid_upload_replaces_dataset_and_archive(self):
        result = portal.upload_dataset(self.upload())
        self.assertEqual(result["status"], "uploaded")
        self.assertFalse((self.dataset / "original.jpg").exists())
        self.assertEqual((self.dataset / "new.jpg").read_bytes(), b"replacement")
        with zipfile.ZipFile(self.archive) as archive:
            self.assertEqual(archive.read("new.jpg"), b"replacement")

    def test_failed_rollback_keeps_original_files_for_recovery(self):
        replace = os.replace
        def fail_promotion_and_rollback(source, destination):
            if Path(destination) == self.archive or Path(source).name == "previous":
                raise OSError("simulated disk error")
            return replace(source, destination)
        with patch.object(portal.os, "replace", side_effect=fail_promotion_and_rollback), self.assertLogs(portal.logger, level="ERROR"):
            with self.assertRaises(portal.HTTPException):
                portal.upload_dataset(self.upload())
        retained = list(self.archive.parent.glob(".upload-*/previous/original.jpg"))
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].read_bytes(), b"original")
        self.assertEqual(self.archive.read_bytes(), b"original archive")

    def test_archive_promotion_failure_rolls_back_dataset(self):
        replace = os.replace
        def fail_archive(source, destination):
            if Path(destination) == self.archive:
                raise OSError("simulated disk error")
            return replace(source, destination)
        with patch.object(portal.os, "replace", side_effect=fail_archive):
            with self.assertRaises(portal.HTTPException):
                portal.upload_dataset(self.upload())
        self.assert_original()


@unittest.skipIf(portal is None, "Portal test dependencies unavailable")
class TrainPilotOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        script = self.root / "trainpilot.sh"; script.write_text("#!/bin/sh\n"); script.chmod(0o700)
        config = self.root / "training.toml"; config.write_text("")
        for name, value in [("WORKSPACE_ROOT", self.root), ("_OUTPUT_ROOT", self.root / "outputs"),
                            ("TRAINPILOT_BIN", script), ("_tp_proc", None), ("_tp_lock", threading.RLock()),
                            ("_tp_logs", deque()), ("_tp_run_id", "previous"), ("_tp_exit_code", 0),
                            ("_tp_output_dir", None), ("_tp_output_baseline", {}), ("_tp_moved_run_id", None)]:
            self.stack.enter_context(patch.object(portal, name, value))
        self.request = portal.TrainPilotRequest(dataset_name="sample", output_name="sample", toml_path=str(config))

    def test_start_reservation_rejects_overlap_and_keeps_one_owner(self):
        entered, release = threading.Event(), threading.Event()
        process = SimpleNamespace(pid=123, poll=lambda: None)
        def spawn(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("test did not release start")
            return process
        with patch.object(portal.subprocess, "Popen", side_effect=spawn) as popen, patch.object(portal, "_tp_reader"):
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(portal.trainpilot_start, self.request)
                try:
                    self.assertTrue(entered.wait(5))
                    with self.assertRaises(portal.HTTPException) as error:
                        portal.trainpilot_start(self.request)
                    self.assertEqual(error.exception.status_code, 409)
                    self.assertEqual(portal._tp_run_id, "previous")
                finally:
                    release.set()
                result = first.result(timeout=5)
            self.assertIs(portal._tp_proc, process)
            self.assertEqual(result["run_id"], portal._tp_run_id)
            self.assertNotEqual(result["run_id"], "previous")
            popen.assert_called_once()

    def test_failed_start_preserves_completed_run_and_allows_retry(self):
        with patch.object(portal.subprocess, "Popen", side_effect=OSError("failure")):
            with self.assertRaises(portal.HTTPException):
                portal.trainpilot_start(self.request)
        self.assertEqual(portal._tp_run_id, "previous")
        self.assertEqual(portal._tp_exit_code, 0)
        with patch.object(portal.subprocess, "Popen", return_value=SimpleNamespace(pid=1)), patch.object(portal, "_tp_reader"):
            self.assertEqual(portal.trainpilot_start(self.request)["status"], "started")

    def test_old_reader_cannot_clear_a_new_process_or_change_its_result(self):
        active = object(); portal._tp_proc = active; portal._tp_exit_code = None
        old = SimpleNamespace(stdout=io.BytesIO(b"stale log\n"), wait=lambda: 0)
        portal._tp_reader(old)
        self.assertIs(portal._tp_proc, active)
        self.assertIsNone(portal._tp_exit_code)
        self.assertEqual(list(portal._tp_logs), [])


class ModelCompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.model_root = self.root / "models"
        self.target = self.model_root / "diffusers/sample"; self.target.mkdir(parents=True)
        self.manifest = self.root / "manifest"
        self.manifest.write_text("sample|hf_repo|owner/repo|diffusers/sample|*.json,*.safetensors|\n")
        self.required = ["model_index.json", "weights.safetensors"]
        (self.target / "model_index.json").write_text("{}")

    def complete(self, required=None):
        models.record_repo_download("sample", "owner/repo", "*.json,*.safetensors", self.target, self.model_root, required or self.required)

    def installed(self):
        return models.parse_manifest(self.manifest, self.manifest, self.model_root, self.root / "config")[0].installed

    def test_metadata_and_unverified_weights_are_not_installed(self):
        self.assertFalse(self.installed())
        with self.assertRaises(ValueError): self.complete()
        (self.target / "weights.safetensors").write_bytes(b"weights")
        self.assertFalse(self.installed())
        self.complete()
        self.assertTrue(self.installed())
        (self.target / "weights.safetensors").write_bytes(b"truncated")
        self.assertFalse(self.installed())

    def test_missing_indexed_shard_and_missing_required_config_are_rejected(self):
        (self.target / "weights.safetensors").write_bytes(b"weights")
        index = self.target / "weights.safetensors.index.json"
        index.write_text(json.dumps({"weight_map": {"layer": "absent.safetensors"}}))
        with self.assertRaises(ValueError): self.complete(self.required + [index.name])
        with self.assertRaises(ValueError): self.complete(self.required + ["missing-config.json"])

    def test_cli_records_success_and_invalidates_receipt_before_failed_retry(self):
        fake_hf = self.root / "hf"
        fake_hf.write_text(
            f"#!{sys.executable}\n"
            "import os,sys\nfrom pathlib import Path\n"
            "if os.environ.get('TEST_DOWNLOAD_FAIL'): sys.exit(1)\n"
            "target=Path(sys.argv[sys.argv.index('--local-dir')+1])\n"
            "(target/'model_index.json').write_text('{}')\n"
            "(target/'weights.safetensors').write_bytes(b'weights')\n"
        )
        fake_hf.chmod(0o700)
        (self.root / "huggingface_hub.py").write_text(
            "class HfApi:\n def list_repo_files(self, **kwargs):\n"
            "  return ['model_index.json','weights.safetensors']\n"
        )
        env = os.environ.copy()
        env.update(WORKSPACE_ROOT=str(self.root), MODELS_DIR=str(self.model_root),
                   MODELS_MANIFEST=str(self.manifest), VENV_PY=sys.executable, HF_BIN=str(fake_hf),
                   MODEL_STATE_HELPER=str(ROOT / "apps/Portal/services/models.py"),
                   PYTHONPATH=str(self.root), HF_TOKEN="")
        command = ["bash", str(ROOT / "scripts/get-models.sh"), "pull", "sample"]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.installed())
        env["TEST_DOWNLOAD_FAIL"] = "1"
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.installed())

    def test_custom_destination_receipt_does_not_replace_default_destination_record(self):
        (self.target / "weights.safetensors").write_bytes(b"weights")
        self.complete()
        custom = self.model_root / "custom"; custom.mkdir()
        (custom / "weights.safetensors").write_bytes(b"custom weights")
        models.record_repo_download("sample", "owner/repo", "*.safetensors", custom, self.model_root, ["weights.safetensors"])
        self.assertTrue(self.installed())

    def test_receipt_deletion_preserves_unrelated_files(self):
        (self.target / "weights.safetensors").write_bytes(b"weights")
        (self.target / "unrelated.safetensors").write_bytes(b"keep")
        self.complete()
        models.delete_model("sample", self.manifest, self.model_root)
        self.assertFalse(self.installed())
        self.assertEqual((self.target / "unrelated.safetensors").read_bytes(), b"keep")


@unittest.skipIf(portal is None, "Portal test dependencies unavailable")
class ShutdownFailureTests(unittest.TestCase):
    def test_command_failures_remain_visible_until_dismissed(self):
        for failure in [None, FileNotFoundError(), subprocess.TimeoutExpired([], 60)]:
            with self.subTest(failure=failure), ExitStack() as stack:
                for name, value in [("shutdown_scheduled", True), ("shutdown_time", 0),
                                    ("shutdown_state", "scheduled"), ("shutdown_error", None), ("shutdown_thread", None)]:
                    stack.enter_context(patch.object(shutdown, name, value))
                stack.enter_context(patch.object(shutdown, "_runpod_shutdown_command", return_value=(["fake"], "stop", "fixture")))
                run = stack.enter_context(patch.object(shutdown.subprocess, "run", side_effect=failure, return_value=SimpleNamespace(returncode=1)))
                shutdown.shutdown_worker()
                status = shutdown.get_shutdown_status()
                self.assertEqual(status.state, "failed")
                self.assertTrue(status.error)
                self.assertFalse(status.scheduled)
                run.assert_called_once()  # Never fall back to a different shutdown action.
                shutdown.cancel_shutdown()
                self.assertIsNone(shutdown.get_shutdown_status().error)

    def test_execution_releases_status_lock_and_disallows_rescheduling(self):
        with ExitStack() as stack:
            for name, value in [("shutdown_scheduled", True), ("shutdown_time", 0),
                                ("shutdown_state", "scheduled"), ("shutdown_error", None), ("shutdown_thread", None)]:
                stack.enter_context(patch.object(shutdown, name, value))
            stack.enter_context(patch.object(shutdown, "_runpod_shutdown_command", return_value=(["fake"], "stop", "fixture")))
            def execute(*args, **kwargs):
                self.assertEqual(shutdown.get_shutdown_status().state, "executing")
                with self.assertRaises(portal.HTTPException):
                    shutdown.schedule_shutdown(shutdown.ShutdownRequest(value=1, unit="minutes"))
                return SimpleNamespace(returncode=0)
            with patch.object(shutdown.subprocess, "run", side_effect=execute):
                shutdown.shutdown_worker()
            self.assertEqual(shutdown.get_shutdown_status().state, "requested")


@unittest.skipIf(portal is None, "Portal test dependencies unavailable")
class CopilotProxyTests(unittest.TestCase):
    def test_chat_waits_for_execution_and_status_keeps_short_timeout(self):
        seen = []
        async def respond(request):
            seen.append(request.extensions["timeout"]["read"])
            return httpx.Response(200, json={"ok": True})
        real_client = httpx.AsyncClient
        with patch.dict(os.environ, {"COPILOT_TIMEOUT_SECONDS": "1800"}), patch.object(portal.httpx, "AsyncClient", side_effect=lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw)):
            asyncio.run(portal.copilot_chat({"prompt": "test"}))
            asyncio.run(portal.copilot_chat({"prompt": "test", "timeout_seconds": 90}))
            asyncio.run(portal.copilot_status())
        self.assertEqual(seen, [1815, max(portal.COPILOT_SIDECAR_TIMEOUT_SECONDS, 105), portal.COPILOT_SIDECAR_TIMEOUT_SECONDS])

    def test_timeout_returns_504_and_invalid_duration_is_rejected(self):
        async def fail(request):
            raise httpx.ReadTimeout("timeout", request=request)
        real_client = httpx.AsyncClient
        with patch.object(portal.httpx, "AsyncClient", side_effect=lambda **kw: real_client(transport=httpx.MockTransport(fail), **kw)):
            with self.assertRaises(portal.HTTPException) as error:
                asyncio.run(portal.copilot_chat({"prompt": "test"}))
            self.assertEqual(error.exception.status_code, 504)
        for timeout in [0, -1, True, "1800"]:
            with self.subTest(timeout=timeout), self.assertRaises(portal.HTTPException) as error:
                asyncio.run(portal.copilot_chat({"prompt": "test", "timeout_seconds": timeout}))
            self.assertEqual(error.exception.status_code, 422)
