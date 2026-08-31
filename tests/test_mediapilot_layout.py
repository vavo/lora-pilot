import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MediaPilotLayoutTests(unittest.TestCase):
    def test_mediapilot_uses_full_pane_and_hides_copilot(self):
        index = (ROOT / "apps/Portal/static/index.html").read_text(encoding="utf-8")
        main = (ROOT / "apps/Portal/static/js/main.js").read_text(encoding="utf-8")
        view = (ROOT / "apps/Portal/static/views/mediapilot.html").read_text(encoding="utf-8")

        self.assertIn(".main.main--mediapilot", index)
        self.assertIn(".main.main--mediapilot #content", index)
        self.assertIn("height: calc(100vh - 80px)", index)
        self.assertIn('mainEl?.classList.toggle("main--mediapilot", disabled)', main)
        self.assertIn("fab.hidden = disabled", main)
        self.assertIn("drawer.hidden = disabled", main)
        self.assertIn('section === "mediapilot"', main)
        self.assertIn('view: "/views/mediapilot.html?v=20260831a"', main)
        self.assertIn('src="/js/main.js?v=20260831a"', index)
        self.assertIn("height: 100vh", view)
        self.assertNotIn("margin: -24px", view)
        self.assertNotIn("margin: -16px", view)


if __name__ == "__main__":
    unittest.main()
