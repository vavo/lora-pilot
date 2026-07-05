import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TrainPilotFrontendTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
