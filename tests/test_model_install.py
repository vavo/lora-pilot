import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from apps.Portal.services import model_files, model_install, models
from apps.Portal import app as portal

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/models.manifest"


class FileDownloadTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.content = b"complete model"
        self.metadata = SimpleNamespace(size=len(self.content), etag=hashlib.sha256(self.content).hexdigest())

        def download(repo, remote, local_dir, token):
            path = local_dir / remote
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.content)
            return str(path)

        self.hub = SimpleNamespace(get_hf_file_metadata=Mock(return_value=self.metadata),
                                   hf_hub_url=Mock(return_value="https://huggingface.co/example"),
                                   hf_hub_download=Mock(side_effect=download))
        self.stack.enter_context(patch.dict(sys.modules, {"huggingface_hub": self.hub}))

    def pull(self, source="org/model:vae/model.safetensors", subdir="vae"):
        model_files.download_hf_file(source, subdir, self.root)

    def test_nested_download_is_flat_and_receipt_reuses_it(self):
        self.pull()
        self.assertEqual((self.root / "vae/model.safetensors").read_bytes(), self.content)
        self.assertFalse((self.root / "vae/vae/model.safetensors").exists())
        self.pull()
        self.assertEqual(self.hub.hf_hub_download.call_count, 1)

    def test_verified_legacy_file_is_reused_and_preserved(self):
        legacy = self.root / "vae/vae/model.safetensors"
        legacy.parent.mkdir(parents=True)
        legacy.write_bytes(self.content)
        self.pull()
        self.hub.hf_hub_download.assert_not_called()
        self.assertEqual(legacy.stat().st_ino, (self.root / "vae/model.safetensors").stat().st_ino)

    def test_same_size_wrong_legacy_file_is_not_reused(self):
        legacy = self.root / "vae/vae/model.safetensors"
        legacy.parent.mkdir(parents=True)
        legacy.write_bytes(b"x" * len(self.content))
        self.pull()
        self.hub.hf_hub_download.assert_called_once()
        self.assertEqual(legacy.read_bytes(), b"x" * len(self.content))

    def test_failed_replacement_preserves_existing_file(self):
        target = self.root / "vae/model.safetensors"
        target.parent.mkdir()
        target.write_bytes(b"original")
        self.hub.hf_hub_download.side_effect = RuntimeError("network failed")
        with self.assertRaises(RuntimeError):
            self.pull()
        self.assertEqual(target.read_bytes(), b"original")

    def test_receipt_does_not_skip_changed_upstream_file_or_allow_source_collision(self):
        self.pull()
        with self.assertRaisesRegex(ValueError, "another model source"):
            self.pull("org/other:vae/model.safetensors")
        self.content = b"updated complete model"
        self.metadata.size = len(self.content)
        self.metadata.etag = hashlib.sha256(self.content).hexdigest()
        self.pull()
        self.assertEqual((self.root / "vae/model.safetensors").read_bytes(), self.content)
        self.assertEqual(self.hub.hf_hub_download.call_count, 2)

    def test_traversal_and_symlink_escape_are_rejected(self):
        (self.root / "escape").symlink_to(self.root.parent, target_is_directory=True)
        for subdir in ["../outside", "/absolute", "escape"]:
            with self.subTest(subdir=subdir), self.assertRaises(ValueError):
                self.pull(subdir=subdir)


class WorkflowPlanTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.manifest = self.root / "manifest"
        # Small real files exercise installed-state handling without model weights.
        lines = []
        for line in MANIFEST.read_text().splitlines():
            if line and not line.startswith("#"):
                columns = line.split("|"); columns[-1] = "14"; line = "|".join(columns)
            lines.append(line)
        self.manifest.write_text("\n".join(lines))
        self.entries = models.parse_manifest(self.manifest, self.manifest, self.root / "models", self.root / "config")
        self.check = self.stack.enter_context(patch.object(model_install, "check_source", return_value={"size_bytes": 14, "access": "Verified"}))
        self.stack.enter_context(patch.object(model_install.shutil, "disk_usage", return_value=SimpleNamespace(free=10000)))

    def plan(self, workflow_id="video_ltx2_5_t2v", optional=None):
        return model_install.installation_plan(workflow_id, optional or [], self.entries, self.root / "models", None)

    def test_all_four_workflows_have_exact_unique_manifest_components(self):
        self.assertEqual(len(model_install.catalog()), 4)
        for workflow in model_install.catalog():
            plan = self.plan(workflow["id"])
            self.assertTrue(plan["can_install"], plan["errors"])
            self.assertEqual(len(plan["files"]), 5)
            self.assertEqual(len({f["path"] for f in plan["files"]}), 5)
            self.assertEqual(plan["download_bytes"], 70)

    def test_optional_is_explicit_and_installed_files_are_reused(self):
        initial = self.plan()
        target = Path(initial["files"][0]["path"])
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b"complete model")
        self.entries = models.parse_manifest(self.manifest, self.manifest, self.root / "models", self.root / "config")
        self.check.reset_mock()
        plan = self.plan(optional=["gemma4_e2b_it_int8_convrot.safetensors"] * 2)
        self.assertEqual(len(plan["files"]), 6)
        self.assertEqual(plan["installed_count"], 1)
        self.assertEqual(plan["download_bytes"], 70)
        self.assertEqual(self.check.call_count, 5)
        self.assertEqual(self.plan()["plan_id"], initial["plan_id"])
        with self.assertRaises(ValueError):
            self.plan(optional=["arbitrary-file"])

    def test_missing_manifest_access_size_and_disk_failures_block_install(self):
        for check in [{"error": "Access denied"}, {"error": "Source missing"}, {"size_bytes": 100}]:
            self.check.return_value = check
            self.assertFalse(self.plan()["can_install"])
        self.check.return_value = {"size_bytes": 14}
        with patch.object(model_install.shutil, "disk_usage", return_value=SimpleNamespace(free=1)):
            self.assertIn("Insufficient", self.plan()["errors"][-1])
        self.entries = []
        self.assertFalse(self.plan()["can_install"])
        with self.assertRaises(ValueError):
            self.plan("../../secret")

    def test_partial_file_and_legacy_copy_do_not_claim_installed(self):
        entry = next(m for m in self.entries if m.name == "ltx-2.5-audio-vae-bf16")
        canonical, legacy = model_files.file_paths(entry.kind, entry.source, entry.subdir, self.root / "models")
        canonical.parent.mkdir(parents=True, exist_ok=True); canonical.write_bytes(b"partial")
        legacy[0].parent.mkdir(parents=True, exist_ok=True); legacy[0].write_bytes(b"complete model")
        parsed = models.parse_manifest(self.manifest, self.manifest, self.root / "models", self.root / "config")
        updated = next(m for m in parsed if m.name == entry.name)
        self.assertFalse(updated.installed)
        self.assertEqual(updated.legacy_path, str(legacy[0]))
        models.delete_model(entry.name, self.manifest, self.root / "models")
        self.assertTrue(legacy[0].exists())

    def test_rounded_custom_sizes_remain_estimates_and_preflight_uses_source_size(self):
        self.manifest.write_text(self.manifest.read_text().replace("|14", "|1GB"))
        self.entries = models.parse_manifest(self.manifest, self.manifest, self.root / "models", self.root / "config")
        plan = self.plan()
        self.assertTrue(plan["can_install"], plan["errors"])
        self.assertEqual(plan["download_bytes"], 70)
        target = Path(plan["files"][0]["path"])
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b"complete model")
        self.entries = models.parse_manifest(self.manifest, self.manifest, self.root / "models", self.root / "config")
        self.assertEqual(self.plan()["installed_count"], 1)
        self.assertEqual(self.plan()["plan_id"], plan["plan_id"])

    def test_start_revalidates_and_deduplicates_queued_downloads(self):
        plan = self.plan()
        payload = portal.WorkflowInstallRequest(plan_id=plan["plan_id"])
        with patch.object(portal, "plan_model_workflow", return_value=plan), patch.object(portal, "_model_pull_jobs", {}), patch.object(portal.threading, "Thread") as thread:
            first = portal.install_model_workflow("video_ltx2_5_t2v", payload)
            second = portal.install_model_workflow("video_ltx2_5_t2v", payload)
            self.assertEqual(len(first["jobs"]), 5)
            self.assertEqual(first, second)
            thread.assert_called_once()
            with self.assertRaises(portal.HTTPException) as error:
                portal.install_model_workflow("video_ltx2_5_t2v", portal.WorkflowInstallRequest(plan_id="stale"))
            self.assertEqual(error.exception.status_code, 409)
            plan["can_install"] = False
            with self.assertRaises(portal.HTTPException):
                portal.install_model_workflow("video_ltx2_5_t2v", payload)

    def test_bundle_skips_newly_installed_files_and_continues_after_failure(self):
        jobs = [portal.ModelPullJob(name=name, state="queued") for name in ["ready", "failed", "next"]]
        def run(job, cmd):
            job.state = "error" if job.name == "failed" else "done"
        with patch.object(portal, "list_models", return_value=[SimpleNamespace(name="ready", installed=True)]), patch.object(portal, "_run_model_pull_job", side_effect=run) as pull:
            portal._run_workflow_pulls(jobs)
        self.assertEqual([job.state for job in jobs], ["done", "error", "done"])
        self.assertEqual(pull.call_count, 2)


class ManifestRepairTests(unittest.TestCase):
    def test_cli_alias_uses_canonical_receipt_name_and_preserves_custom_old_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, helper, cli, calls = [root / n for n in ("manifest", "helper.py", "hf", "calls")]
            helper.write_text("import os,sys\nwith open(os.environ['TEST_CALLS'], 'a') as f:f.write(sys.argv[1]+' '+sys.argv[2]+'\\n')\n")
            cli.write_text("#!/bin/sh\nexit 0\n"); cli.chmod(0o755)
            env = {**os.environ, "WORKSPACE_ROOT": str(root), "MODELS_MANIFEST": str(manifest),
                   "MODELS_DIR": str(root / "models"), "MODEL_STATE_HELPER": str(helper),
                   "VENV_PY": sys.executable, "HF_BIN": str(cli), "TEST_CALLS": str(calls)}
            for name in ["swin2sr-4x", "swinir-4x"]:
                manifest.write_text(f"{name}|hf_repo|org/repo|diffusers/swin2sr|*.json|14\n")
                calls.write_text("")
                subprocess.run(["bash", str(ROOT / "scripts/get-models.sh"), "pull", "swinir-4x"], env=env, check=True, capture_output=True)
                self.assertEqual(calls.read_text().splitlines(), [f"begin {name}", f"complete {name}"])

    def test_access_errors_do_not_expose_provider_exception_details(self):
        for status, expected in [(401, "Access denied"), (403, "Access denied"), (404, "not found"), (503, "connectivity")]:
            error = RuntimeError("secret request header must stay private")
            error.response = SimpleNamespace(status_code=status)
            hub = SimpleNamespace(get_hf_file_metadata=Mock(side_effect=error), hf_hub_url=Mock(return_value="https://huggingface.co/example"))
            with patch.dict(sys.modules, {"huggingface_hub": hub}):
                result = model_install.check_source("org/repo:file", "test-token")
            self.assertIn(expected, result["error"])
            self.assertNotIn("secret", result["error"])

    def test_single_file_destinations_do_not_collide(self):
        seen = set()
        for line in MANIFEST.read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            name, kind, source, subdir, *_ = line.split("|")
            if kind == "hf_repo":
                continue
            path, _ = model_files.file_paths(kind, source, subdir, Path("/workspace/models"))
            self.assertNotIn(path, seen, name)
            seen.add(path)

    def test_repo_filters_include_tokenizer_merges_and_wan_dependencies(self):
        entries = {line.split("|")[0]: line.split("|") for line in MANIFEST.read_text().splitlines() if line and not line.startswith("#")}
        for name in ["ragnarok-xl", "epicrealism-xl"]:
            patterns = entries[name][4].split(",")
            self.assertTrue(models._matches_any_pattern("tokenizer/merges.txt", patterns))
            self.assertTrue(models._matches_any_pattern("tokenizer_2/merges.txt", patterns))
        patterns = entries["wan2.2-animate-14b"][4].split(",")
        for file in ["Wan2.1_VAE.pth", "models_t5_umt5-xxl-enc-bf16.pth", "google/umt5-xxl/spiece.model"]:
            self.assertTrue(models._matches_any_pattern(file, patterns), file)
