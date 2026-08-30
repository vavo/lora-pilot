import unittest
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TrainPilotFrontendTests(unittest.TestCase):
    def test_trainpilot_preflights_sdxl_tokenizer(self):
        text = (ROOT / "apps/TrainPilot/trainpilot.sh").read_text()
        self.assertIn("ensure_sdxl_tokenizer()", text)
        self.assertIn('local_files_only=True', text)
        self.assertIn("from huggingface_hub import hf_hub_download", text)
        self.assertIn("hf_hub_download(repo_id=repo_id, filename=filename)", text)
        self.assertNotIn('hf_bin="/opt/venvs/core/bin/hf"', text)
        self.assertIn("openai/clip-vit-large-patch14", text)

    def test_start_warns_and_starts_required_services_before_training(self):
        text = (ROOT / "apps/Portal/static/js/trainpilot.js").read_text()

        self.assertIn('{ name: "kohya", label: "Kohya" }', text)
        self.assertIn('{ name: "diffpipe", label: "TensorBoard" }', text)
        self.assertIn("Start missing service(s) now?", text)
        self.assertIn("/api/services/${encodeURIComponent(service.name)}/start", text)
        self.assertLess(
            text.index("await ensureTrainpilotRuntimeServices(status)"),
            text.index('await fetchJson("/api/trainpilot/start"'),
        )

    def test_completed_training_offers_to_move_new_loras(self):
        text = (ROOT / "apps/Portal/static/js/trainpilot.js").read_text()

        self.assertIn("data.move_available", text)
        self.assertIn("Move the new LoRA file(s) to /workspace/models/loras?", text)
        self.assertIn('fetchJson("/api/trainpilot/move-loras"', text)
        self.assertIn("data.run_id !== tpMovePromptedRunId", text)

    def test_move_loras_moves_only_current_run_artifacts(self):
        try:
            from apps.Portal import app as portal_app
        except ModuleNotFoundError as exc:
            if exc.name == "fastapi":
                self.skipTest("FastAPI is not installed in this test environment")
            raise

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            output_dir = workspace / "outputs" / "run"
            output_dir.mkdir(parents=True)
            new_lora = output_dir / "run000001.safetensors"
            new_lora.write_bytes(b"lora")
            old_state = (
                portal_app.MODELS_DIR,
                portal_app._OUTPUT_ROOT,
                portal_app._tp_output_dir,
                portal_app._tp_run_id,
                portal_app._tp_exit_code,
                portal_app._tp_output_baseline,
                portal_app._tp_moved_run_id,
            )
            try:
                portal_app.MODELS_DIR = workspace / "models"
                portal_app._OUTPUT_ROOT = workspace / "outputs"
                portal_app._tp_output_dir = output_dir
                portal_app._tp_run_id = "current-run"
                portal_app._tp_exit_code = 0
                portal_app._tp_output_baseline = {}
                portal_app._tp_moved_run_id = None

                result = portal_app.trainpilot_move_loras(
                    portal_app.TrainPilotMoveRequest(run_id="current-run")
                )

                self.assertEqual(result["files"], ["run000001.safetensors"])
                self.assertFalse(new_lora.exists())
                self.assertTrue((portal_app.MODELS_DIR / "loras" / new_lora.name).exists())
            finally:
                (
                    portal_app.MODELS_DIR,
                    portal_app._OUTPUT_ROOT,
                    portal_app._tp_output_dir,
                    portal_app._tp_run_id,
                    portal_app._tp_exit_code,
                    portal_app._tp_output_baseline,
                    portal_app._tp_moved_run_id,
                ) = old_state


if __name__ == "__main__":
    unittest.main()
