import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TrainPilotFrontendTests(unittest.TestCase):
    def test_trainpilot_preflights_sdxl_tokenizer(self):
        text = (ROOT / "apps/TrainPilot/trainpilot.sh").read_text(encoding="utf-8")
        self.assertIn("ensure_sdxl_tokenizer()", text)
        self.assertIn('local_files_only=True', text)
        self.assertIn('hf_bin="/opt/venvs/core/bin/hf"', text)
        self.assertIn("openai/clip-vit-large-patch14", text)

    def test_start_warns_and_starts_required_services_before_training(self):
        text = (ROOT / "apps/Portal/static/js/trainpilot.js").read_text(encoding="utf-8")

        self.assertIn('{ name: "kohya", label: "Kohya" }', text)
        self.assertIn('{ name: "diffpipe", label: "TensorBoard" }', text)
        self.assertIn("Start missing service(s) now?", text)
        self.assertIn("/api/services/${encodeURIComponent(service.name)}/start", text)
        self.assertLess(
            text.index("await ensureTrainpilotRuntimeServices(status)"),
            text.index('await fetchJson("/api/trainpilot/start"'),
        )


if __name__ == "__main__":
    unittest.main()
