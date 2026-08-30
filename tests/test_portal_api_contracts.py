import asyncio
import unittest
from unittest.mock import patch

try:
    from apps.Portal import app as portal_app
except ModuleNotFoundError as exc:
    if exc.name == "fastapi":
        portal_app = None
    else:
        raise


class PortalApiContractsTests(unittest.TestCase):
    def setUp(self):
        if portal_app is None:
            self.skipTest("FastAPI is not installed in this test environment")

    def test_set_hf_token_accepts_body_and_query(self):
        payload = portal_app.HfTokenRequest(token="  body-token ")
        with patch.object(portal_app, "_write_secrets_env_vars") as write_secrets:
            result = asyncio.run(portal_app.set_hf_token(payload=payload))
            self.assertEqual(result, {"status": "ok", "set": True})
            write_secrets.assert_called_once_with({"HF_TOKEN": "body-token"})

        with patch.object(portal_app, "_write_secrets_env_vars") as write_secrets:
            result = asyncio.run(portal_app.set_hf_token(token="query-token"))
            self.assertEqual(result, {"status": "ok", "set": True})
            write_secrets.assert_called_once_with({"HF_TOKEN": "query-token"})

    def test_parse_bool_env_default_when_empty(self):
        key = "PORTAL_TEST_BOOL"
        old = portal_app.os.environ.get(key)
        try:
            portal_app.os.environ[key] = ""
            self.assertTrue(portal_app._parse_bool_env(key, True))
            self.assertFalse(portal_app._parse_bool_env(key, False))
            portal_app.os.environ[key] = "true"
            self.assertTrue(portal_app._parse_bool_env(key, False))
            portal_app.os.environ[key] = "0"
            self.assertFalse(portal_app._parse_bool_env(key, True))
        finally:
            if old is None:
                portal_app.os.environ.pop(key, None)
            else:
                portal_app.os.environ[key] = old

    def test_dpipe_toml_omits_none_values(self):
        from apps.Portal.dpipe_api import _clean_toml_dict, toml

        sample_cfg = {
            "resolutions": [512, 512],
            "enable_ar_bucket": False,
            "ar_buckets": None,
            "directory": [{"path": "/workspace/datasets/test", "num_repeats": 1}],
            "monitoring": {
                "wandb_run_name": None,
                "enable_wandb": False,
            },
        }

        cleaned = _clean_toml_dict(sample_cfg)
        self.assertNotIn("ar_buckets", cleaned)
        self.assertNotIn("wandb_run_name", cleaned["monitoring"])
        self.assertFalse(cleaned["monitoring"]["enable_wandb"])

        dumped = toml.dumps(sample_cfg)
        self.assertNotIn("ar_buckets", dumped)
        self.assertNotIn('ar_buckets = ""', dumped)
        self.assertNotIn("wandb_run_name", dumped)
        self.assertIn("enable_wandb = false", dumped)

    def test_mediapilot_get_db_closes_connection(self):
        import sys
        import sqlite3
        from unittest.mock import MagicMock

        if "PIL" not in sys.modules:
            sys.modules["PIL"] = MagicMock()
            sys.modules["PIL.Image"] = MagicMock()

        from apps.MediaPilot.main import get_db

        with get_db() as conn:
            conn.execute("SELECT 1")

        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
