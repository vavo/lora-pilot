import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAGPILOT_HTML = ROOT / "apps" / "TagPilot" / "index.html"
DATASETS_JS = ROOT / "apps" / "Portal" / "static" / "js" / "datasets.js"


class TagPilotFrontendSecurityTests(unittest.TestCase):
    def test_provider_keys_are_not_persisted_in_browser_storage(self):
        text = TAGPILOT_HTML.read_text(encoding="utf-8")

        self.assertNotIn("getProviderKeyStorageName", text)
        self.assertNotRegex(text, re.compile(r"localStorage\.(?:getItem|setItem)\([^)]*ApiKey"))
        self.assertNotRegex(text, re.compile(r"localStorage\.setItem\([^,]+,\s*apiKeyInputs"))

    def test_loaded_dataset_text_files_are_decoded_from_base64(self):
        text = TAGPILOT_HTML.read_text(encoding="utf-8")

        self.assertIn("function base64ToText(base64)", text)
        self.assertIn("new TextDecoder('utf-8').decode(byteArray)", text)
        self.assertIn("if (lower.endsWith('.txt'))", text)
        self.assertIn("if (lower.endsWith('.caption') && !textFiles.has(baseName))", text)
        self.assertIn("textFiles.set(baseName, base64ToText(file?.b64).trim())", text)
        self.assertNotIn("textFiles.set(baseName, String(file?.b64 || '').trim())", text)

    def test_dataset_list_does_not_render_api_values_as_html(self):
        text = DATASETS_JS.read_text(encoding="utf-8")

        self.assertNotIn("tr.innerHTML", text)
        self.assertIn("anchor.textContent = d.display || d.name", text)
        self.assertIn("button.dataset[action] = datasetName", text)


if __name__ == "__main__":
    unittest.main()
