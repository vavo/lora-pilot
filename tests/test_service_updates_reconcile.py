import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "service-updates-reconcile.py"
SPEC = importlib.util.spec_from_file_location("service_updates_reconcile", MODULE_PATH)
service_updates_reconcile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(service_updates_reconcile)


class ServiceUpdatesReconcileTests(unittest.TestCase):
    def test_image_managed_git_services_are_skipped(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "service-updates.toml"
            rollback_log_path = tmp_path / "service-updates-rollback.jsonl"
            config_path.write_text(
                """
enabled = true

[services.comfy]
auto_update = true
target_ref = "main"
""".lstrip(),
                encoding="utf-8",
            )

            calls = []
            original_run_cmd_stream = service_updates_reconcile.run_cmd_stream

            def fail_if_called(cmd):
                calls.append(cmd)
                raise AssertionError(f"unexpected update command: {cmd}")

            service_updates_reconcile.run_cmd_stream = fail_if_called
            try:
                output = io.StringIO()
                with redirect_stdout(output):
                    rc = service_updates_reconcile.run_reconcile(config_path, rollback_log_path)
            finally:
                service_updates_reconcile.run_cmd_stream = original_run_cmd_stream

            self.assertEqual(rc, 0)
            self.assertEqual(calls, [])
            self.assertFalse(rollback_log_path.exists())
            self.assertIn("image-managed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
