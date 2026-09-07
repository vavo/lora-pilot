import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from apps.Portal.services import model_downloads

try:
    from apps.Portal import app as portal
    from apps.Portal import dpipe_api as dpipe
    from apps.CopilotSidecar import app as copilot
except ModuleNotFoundError as exc:
    if exc.name not in {"fastapi", "httpx"}:
        raise
    portal = None


@unittest.skipIf(portal is None, "Portal test dependencies unavailable")
class MediaMoveTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.dict(os.environ, {
            "MEDIAPILOT_OUTPUT_DIR": str(self.root / "outputs"),
            "MEDIAPILOT_THUMBS_DIR": str(self.root / "thumbs"),
            "MEDIAPILOT_INVOKEAI_DIR": str(self.root / "invoke"),
            "MEDIAPILOT_DB_FILE": str(self.root / "media.db"),
        }))
        try:
            import PIL
        except ImportError:
            # Image decoding is not used by the move endpoint.
            self.stack.enter_context(patch.dict(sys.modules, {"PIL": MagicMock()}))
        path = Path(__file__).resolve().parents[1] / "apps/MediaPilot/main.py"
        spec = importlib.util.spec_from_file_location("review_mediapilot", path)
        self.media = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.media)
        self.source = self.root / "outputs" / "same.png"
        self.source.write_bytes(b"source image")
        self.destination = self.root / "outputs" / "saved" / "same.png"
        self.destination.parent.mkdir()

    def test_collision_preserves_both_images_and_metadata(self):
        self.destination.write_bytes(b"existing image")
        with self.assertRaises(self.media.HTTPException) as error:
            self.media.tag_file("same.png", "_root", "saved")
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.source.read_bytes(), b"source image")
        self.assertEqual(self.destination.read_bytes(), b"existing image")
        with self.media.get_db() as db:
            self.assertEqual(db.execute("SELECT * FROM tags").fetchall(), [])

    def test_move_and_same_folder_noop(self):
        self.media.tag_file("same.png", "_root", "saved")
        self.assertFalse(self.source.exists())
        self.assertEqual(self.destination.read_bytes(), b"source image")
        self.media.tag_file("same.png", "saved", "saved")
        self.assertEqual(self.destination.read_bytes(), b"source image")
        with self.media.get_db() as db:
            self.assertEqual(db.execute("SELECT folder FROM tags").fetchall(), [("saved",)])

    def test_missing_source_is_not_reported_as_moved(self):
        with self.assertRaises(self.media.HTTPException) as error:
            self.media.tag_file("missing.png", "_root", "saved")
        self.assertEqual(error.exception.status_code, 404)


@unittest.skipIf(portal is None, "Portal test dependencies unavailable")
class DiffusionPipeRunTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for name, suffix in [("WORKSPACE", ""), ("MODEL_DIR", "models"),
                             ("BASE_DATASET_DIR", "datasets"), ("OUTPUT_DIR", "outputs"),
                             ("CONFIG_DIR", "configs"), ("DIFFPIPE_APP_DIR", "app")]:
            self.stack.enter_context(patch.object(dpipe, name, self.root / suffix))
        self.stack.enter_context(patch.object(dpipe, "_LOCAL_PATH_ROOTS", (self.root,)))
        self.stack.enter_context(patch.object(dpipe, "_procs", {}))
        self.stack.enter_context(patch.object(dpipe, "_logs", {}))
        self.stack.enter_context(patch.object(dpipe, "_start_lock", threading.Lock()))
        dpipe._ensure_dirs()
        dpipe.DIFFPIPE_APP_DIR.mkdir()
        (dpipe.DIFFPIPE_APP_DIR / "train.py").touch()
        self.request = dpipe.TrainRequest(
            dataset_path=str(dpipe.BASE_DATASET_DIR), config_dir=str(dpipe.CONFIG_DIR),
            output_dir=str(dpipe.OUTPUT_DIR), transformer_path="models/transformer",
            vae_path="models/vae", llm_path="models/llm", clip_path="models/clip",
        )
        self.spawn = self.stack.enter_context(patch.object(
            dpipe.subprocess, "Popen", return_value=SimpleNamespace(pid=123)))
        self.stack.enter_context(patch.object(dpipe, "_read_stream"))

    def test_overlapping_starts_reserve_before_writing_configs(self):
        entered, release = threading.Event(), threading.Event()
        def resolve_binary():
            entered.set()
            if not release.wait(timeout=5):
                raise RuntimeError("test start was not released")
            return Path("/fake/deepspeed")
        with patch.object(dpipe, "_resolve_deepspeed_bin", side_effect=resolve_binary):
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(dpipe.start_training, self.request)
                try:
                    self.assertTrue(entered.wait(timeout=5))
                    with self.assertRaises(dpipe.HTTPException) as error:
                        dpipe.start_training(self.request)
                    self.assertEqual(error.exception.status_code, 400)
                    self.assertFalse((dpipe.CONFIG_DIR / "training_config.toml").exists())
                finally:
                    release.set()
                self.assertEqual(first.result(timeout=5)["pid"], 123)
            with self.assertRaises(dpipe.HTTPException):
                dpipe.start_training(self.request)
        self.spawn.assert_called_once()

    def test_failed_start_releases_reservation(self):
        with patch.object(dpipe, "_resolve_deepspeed_bin", side_effect=RuntimeError("unavailable")):
            with self.assertRaises(RuntimeError):
                dpipe.start_training(self.request)
        with patch.object(dpipe, "_resolve_deepspeed_bin", return_value=Path("/fake/deepspeed")):
            self.assertEqual(dpipe.start_training(self.request)["pid"], 123)

    def test_logs_follow_active_then_latest_completed_run(self):
        dpipe._logs.update({1: deque(["old"]), 2: deque(["current"])})
        dpipe._procs[2] = object()
        self.assertEqual(dpipe.training_logs(), {"pid": 2, "lines": ["current"]})
        self.assertEqual(dpipe.training_logs(pid=1)["lines"], ["old"])
        self.assertEqual(dpipe.training_logs(pid=999)["lines"], [])
        dpipe._procs.clear()
        self.assertEqual(dpipe.training_logs(), {"pid": 2, "lines": ["current"]})


@unittest.skipIf(portal is None, "Portal test dependencies unavailable")
class BackgroundOutputTests(unittest.TestCase):
    def test_download_reports_progress_before_eof_across_chunks(self):
        queue = model_downloads.ModelPullQueue(lambda: "")
        job = model_downloads.ModelPullJob(name="test-download")
        chunks = iter([b"Downloading 25%\r\nDownloading 7", b"5%\n", b""])
        def read(_size):
            chunk = next(chunks)
            if not chunk:
                self.assertEqual(job.progress_pct, 75)
                self.assertEqual(job.last_line, "Downloading 75%")
                self.assertEqual(len(job.output_tail), 2)
            return chunk
        stream = MagicMock()
        stream.read.side_effect = read
        proc = SimpleNamespace(pid=123, stdout=stream, wait=lambda: 0)
        with patch.object(model_downloads.subprocess, "Popen", return_value=proc):
            queue.run_job(job, ["fake-download"])
        self.assertEqual(job.state, "done", job.error)
        self.assertEqual(job.progress_pct, 100)

    def test_download_bounds_unterminated_output_and_preserves_error(self):
        queue = model_downloads.ModelPullQueue(lambda: "")
        job = model_downloads.ModelPullJob(name="test-download")
        proc = SimpleNamespace(pid=123, stdout=io.BytesIO(b"x" * 50000 + b"failure detail"), wait=lambda: 1)
        with patch.object(model_downloads.subprocess, "Popen", return_value=proc):
            queue.run_job(job, ["fake-download"])
        self.assertEqual(job.state, "error")
        self.assertLessEqual(len(job.last_line), 8192)
        self.assertTrue(job.error.endswith("failure detail"))

    def test_copilot_timeout_preserves_partial_output(self):
        for stdout, stderr in [(b"partial\xff", b"error\xff"), ("partial", "error"), (None, None)]:
            with self.subTest(stdout=stdout, stderr=stderr):
                failure = subprocess.TimeoutExpired(["copilot"], 1, output=stdout, stderr=stderr)
                with patch.object(copilot, "_copilot_bin", return_value="/fake/copilot"), \
                     patch.object(copilot, "_resolve_workspace_cwd", return_value=Path("/tmp")), \
                     patch.object(copilot, "_ensure_trusted_folder"), \
                     patch.object(copilot.subprocess, "run", side_effect=failure):
                    result = copilot.chat(copilot.ChatRequest(prompt="test", timeout_seconds=1))
                self.assertFalse(result.ok)
                self.assertEqual(result.returncode, 124)
                self.assertIsInstance(result.stdout, str)
                self.assertIn("Timed out after 1s", result.stderr)
                if stdout:
                    self.assertTrue(result.stdout.startswith("partial"))
                if stderr:
                    self.assertTrue(result.stderr.startswith("error"))


if __name__ == "__main__":
    unittest.main()
