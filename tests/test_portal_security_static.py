import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_APP = ROOT / "apps" / "Portal" / "app.py"


class PortalSecurityStaticTests(unittest.TestCase):
    def test_secret_env_writer_uses_secure_atomic_write(self):
        text = PORTAL_APP.read_text(encoding="utf-8")
        match = re.search(r"def _write_secrets_env_vars\(.*?^def _read_secret_env_var", text, re.S | re.M)
        self.assertIsNotNone(match)
        writer = match.group(0)

        self.assertNotIn("write_text", writer)
        self.assertIn("os.open", writer)
        self.assertIn("0o600", writer)
        self.assertIn("os.replace", writer)

    def test_dataset_file_iterator_resolves_existing_dataset_before_walk(self):
        text = PORTAL_APP.read_text(encoding="utf-8")
        match = re.search(r"def _iter_dataset_files\(.*?^def _write_dataset_zip", text, re.S | re.M)
        self.assertIsNotNone(match)
        iterator = match.group(0)
        resolver = re.search(r"def _resolve_existing_dataset_dir\(.*?^def _iter_tensorboard_events", text, re.S | re.M)
        self.assertIsNotNone(resolver)

        self.assertIn("entries = sorted(os.listdir(dataset_root))", resolver.group(0))
        self.assertIn("dataset_root = _safe_dataset_path(_DATASET_ROOT)", iterator)
        self.assertIn("target_name = _resolve_existing_dataset_dir(root).name", iterator)
        self.assertIn("os.walk(dataset_root, followlinks=False)", iterator)
        self.assertNotIn("os.walk(dataset_dir", iterator)
        self.assertNotIn("os.scandir", iterator)


if __name__ == "__main__":
    unittest.main()
