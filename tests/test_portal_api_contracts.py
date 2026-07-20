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


if __name__ == "__main__":
    unittest.main()
