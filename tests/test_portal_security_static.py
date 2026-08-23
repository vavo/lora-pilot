import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_APP = ROOT / "apps" / "Portal" / "app.py"
COPILOT_SIDECAR_APP = ROOT / "apps" / "CopilotSidecar" / "app.py"


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

    def test_controlpilot_settings_writer_uses_private_atomic_write(self):
        text = PORTAL_APP.read_text(encoding="utf-8")
        helper = re.search(r"def _write_private_text\(.*?^def _write_controlpilot_settings", text, re.S | re.M)
        self.assertIsNotNone(helper)
        writer = re.search(r"def _write_controlpilot_settings\(.*?^def _merge_controlpilot_settings", text, re.S | re.M)
        self.assertIsNotNone(writer)

        helper_text = helper.group(0)
        writer_text = writer.group(0)
        self.assertNotIn("CONTROLPILOT_SETTINGS_PATH.write_text", writer_text)
        self.assertIn("_write_private_text(CONTROLPILOT_SETTINGS_PATH", writer_text)
        self.assertIn("os.open", helper_text)
        self.assertIn("0o600", helper_text)
        self.assertIn("os.replace", helper_text)
        self.assertIn("os.chmod", helper_text)

    def test_copilot_sidecar_config_writer_uses_private_atomic_write(self):
        text = COPILOT_SIDECAR_APP.read_text(encoding="utf-8")
        helper = re.search(r"def _write_private_text\(.*?^def _ensure_trusted_folder", text, re.S | re.M)
        self.assertIsNotNone(helper)
        writer = re.search(r"def _ensure_trusted_folder\(.*?^def _resolve_workspace_cwd", text, re.S | re.M)
        self.assertIsNotNone(writer)

        helper_text = helper.group(0)
        writer_text = writer.group(0)
        self.assertNotIn("cfg_path.write_text", writer_text)
        self.assertIn("_write_private_text(cfg_path", writer_text)
        self.assertIn("os.open", helper_text)
        self.assertIn("0o600", helper_text)
        self.assertIn("os.replace", helper_text)
        self.assertIn("os.chmod", helper_text)

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

    def test_tagpilot_save_checks_canonical_dataset_root_at_file_sinks(self):
        text = PORTAL_APP.read_text(encoding="utf-8")
        route = re.search(r"def tagpilot_save\(.*?^def tagpilot_save_item", text, re.S | re.M)
        self.assertIsNotNone(route)
        route_text = route.group(0)

        self.assertIn('dataset_root = os.path.realpath(str(_DATASET_ROOT))', route_text)
        self.assertIn('target = os.path.realpath(str(target))', route_text)
        self.assertIn('target.startswith(os.path.join(dataset_root, ""))', route_text)

    def test_supervisor_commands_use_literal_allowlists(self):
        text = PORTAL_APP.read_text(encoding="utf-8")
        helper = re.search(r"def _run_supervisorctl\(.*?^def _default_service_updates_config", text, re.S | re.M)
        self.assertIsNotNone(helper)
        helper_text = helper.group(0)

        self.assertIn('safe_action = _SUPERVISOR_ACTIONS.get(action)', helper_text)
        self.assertIn('safe_name = _SUPERVISOR_SERVICE_NAMES.get(name)', helper_text)
        self.assertIn('cmd = [SUPERVISORCTL, safe_action]', helper_text)

    def test_controlpilot_auth_covers_non_api_control_routes(self):
        app_text = PORTAL_APP.read_text(encoding="utf-8")
        comfy_text = (ROOT / "apps" / "Portal" / "services" / "comfy.py").read_text(encoding="utf-8")
        self.assertIn('path.startswith(("/api/", "/dpipe/", "/proxy/comfy/"))', app_text)
        self.assertIn('auth_checker=_controlpilot_cookie_authenticated', app_text)
        self.assertIn('websocket.close(code=4401', comfy_text)

    def test_removed_copilot_view_is_not_a_second_ui(self):
        index = (ROOT / "apps" / "Portal" / "static" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('/js/copilot.js', index)
        self.assertFalse((ROOT / "apps" / "Portal" / "static" / "js" / "copilot.js").exists())
        self.assertFalse((ROOT / "apps" / "Portal" / "static" / "views" / "copilot.html").exists())


if __name__ == "__main__":
    unittest.main()
