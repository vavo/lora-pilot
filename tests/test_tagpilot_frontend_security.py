import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAGPILOT_HTML = ROOT / "apps" / "TagPilot" / "index.html"


class TagPilotFrontendSecurityTests(unittest.TestCase):
    def test_provider_keys_are_not_persisted_in_browser_storage(self):
        text = TAGPILOT_HTML.read_text(encoding="utf-8")

        self.assertNotIn("getProviderKeyStorageName", text)
        self.assertNotRegex(text, re.compile(r"localStorage\.(?:getItem|setItem)\([^)]*ApiKey"))
        self.assertNotRegex(text, re.compile(r"localStorage\.setItem\([^,]+,\s*apiKeyInputs"))


if __name__ == "__main__":
    unittest.main()
