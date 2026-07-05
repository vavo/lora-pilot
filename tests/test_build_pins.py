import re
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_pin(path, name):
    text = (ROOT / path).read_text()
    patterns = [
        rf"ARG {re.escape(name)}=([^\s]+)",
        rf"{re.escape(name)} \?= ([^\s]+)",
        rf"^{re.escape(name)}=([^\s]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return match.group(1)
    raise AssertionError(f"{name} not found in {path}")


class BuildPinTests(unittest.TestCase):
    def test_node_tooling_uses_pinned_npm_version(self):
        expected = "11.17.0"
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                self.assertEqual(read_pin(path, "NPM_VERSION"), expected)

        make_text = (ROOT / "Makefile").read_text()
        system_tools = (ROOT / "scripts/build/install-system-tools.sh").read_text()

        self.assertIn('--build-arg NPM_VERSION="$(NPM_VERSION)"', make_text)
        self.assertIn(': "${NPM_VERSION:?NPM_VERSION is required}"', system_tools)
        self.assertIn('npm install -g "npm@${NPM_VERSION}"', system_tools)

    def test_ai_toolkit_patch_removes_deprecated_next_dev_indicator(self):
        patch_text = (ROOT / "scripts/build/patches/patch-ai-toolkit.sh").read_text()

        self.assertIn("next.config.ts", patch_text)
        self.assertIn("devIndicators", patch_text)
        self.assertIn("buildActivity", patch_text)

    def test_invokeai_6135_uses_required_dependency_pins(self):
        expected = {
            "INVOKEAI_VERSION": "6.13.5",
            "INVOKE_DIFFUSERS_VERSION": "0.37.0",
            "INVOKE_TRANSFORMERS_VERSION": "5.5.4",
        }
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                for name, value in expected.items():
                    self.assertEqual(read_pin(path, name), value)

    def test_invokeai_613_uses_supported_cuda_torch_stack(self):
        expected = {
            "INVOKE_TORCH_VERSION": "2.7.1+cu128",
            "INVOKE_TORCHVISION_VERSION": "0.22.1+cu128",
            "INVOKE_TORCH_INDEX_URL": "https://download.pytorch.org/whl/cu128",
            "INVOKE_XFORMERS_VERSION": "0.0.31.post1",
        }
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                for name, value in expected.items():
                    self.assertEqual(read_pin(path, name), value)

    def test_comfy_uses_latest_verified_refs(self):
        expected = {
            "COMFYUI_REF": "v0.27.0",
            "COMFYUI_MANAGER_REF": "4.2.2",
        }
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                for name, value in expected.items():
                    self.assertEqual(read_pin(path, name), value)

    def test_core_stack_installs_required_comfy_modules(self):
        expected = {
            "TORCHAUDIO_VERSION": "2.11.0",
            "XFORMERS_VERSION": "0.0.35",
            "TRANSFORMERS_VERSION": "5.11.0",
            "UV_VERSION": "0.11.26",
        }
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                for name, value in expected.items():
                    self.assertEqual(read_pin(path, name), value)

        core_stack = (ROOT / "scripts/build/install-core-stack.sh").read_text()
        self.assertIn('"torchaudio==${TORCHAUDIO_VERSION}"', core_stack)
        self.assertIn('"uv==${UV_VERSION}"', core_stack)
        self.assertIn('core_import_modules="torchaudio ${core_import_modules}"', core_stack)
        self.assertIn('CORE_IMPORT_MODULES="${core_import_modules}"', core_stack)

    def test_generated_invoke_constraints_use_invoke_torch_stack(self):
        env = os.environ.copy()
        env.update(
            {
                "TORCH_VERSION": "2.12.0",
                "TORCHVISION_VERSION": "0.27.0",
                "TORCHAUDIO_VERSION": "2.11.0",
                "XFORMERS_VERSION": "0.0.35",
                "BITSANDBYTES_VERSION": "0.49.2",
                "CORE_DIFFUSERS_VERSION": "0.38.0",
                "TRANSFORMERS_VERSION": "5.11.0",
                "UV_VERSION": "0.11.26",
                "PEFT_VERSION": "0.19.1",
                "ACCELERATE_VERSION": "1.14.0",
                "HF_HUB_VERSION": "1.19.0",
                "INVOKE_TORCH_VERSION": "2.7.1+cu128",
                "INVOKE_TORCHVISION_VERSION": "0.22.1+cu128",
                "INVOKE_XFORMERS_VERSION": "0.0.31.post1",
                "INVOKE_DIFFUSERS_VERSION": "0.37.0",
                "INVOKE_TRANSFORMERS_VERSION": "5.5.4",
                "INVOKE_ACCELERATE_VERSION": "1.14.0",
                "INVOKE_HF_HUB_VERSION": "0.36.2",
                "DIFFPIPE_DIFFUSERS_VERSION": "0.38.0",
                "DIFFPIPE_TRANSFORMERS_VERSION": "5.11.0",
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                ["bash", str(ROOT / "scripts/build/write-constraints.sh"), tmp],
                check=True,
                env=env,
            )
            constraints = (Path(tmp) / "invoke-constraints.txt").read_text()

        self.assertIn("torch==2.7.1+cu128\n", constraints)
        self.assertIn("torchvision==0.22.1+cu128\n", constraints)
        self.assertIn("xformers==0.0.31.post1\n", constraints)
        self.assertIn("diffusers==0.37.0\n", constraints)
        self.assertIn("transformers==5.5.4\n", constraints)
        self.assertNotIn("torch==2.12.0\n", constraints)

    def test_makefile_passes_service_install_flags_to_docker(self):
        text = (ROOT / "Makefile").read_text()
        for name in (
            "INSTALL_COMFY",
            "INSTALL_KOHYA",
            "INSTALL_DIFFPIPE",
            "INSTALL_AI_TOOLKIT_UI",
            "INSTALL_COPILOT_CLI",
        ):
            with self.subTest(name=name):
                self.assertIn(f"{name} ?= 1", text)
                self.assertIn(f"--build-arg {name}=$({name})", text)

    def test_makefile_passes_all_non_cache_docker_args(self):
        docker_text = (ROOT / "Dockerfile").read_text()
        make_text = (ROOT / "Makefile").read_text()
        docker_args = re.findall(
            r"^ARG\s+([A-Za-z_][A-Za-z0-9_]*)(?:=.*)?$",
            docker_text,
            re.MULTILINE,
        )
        make_args = set(
            re.findall(
                r"--build-arg\s+([A-Za-z_][A-Za-z0-9_]*)=",
                make_text,
            )
        )
        skipped = {"BUILDPLATFORM", "TARGETPLATFORM"}
        missing = [
            name
            for name in docker_args
            if name not in make_args and name not in skipped and not name.endswith("CACHE_BUST")
        ]
        self.assertEqual(missing, [])

    def test_service_scripts_are_copied_after_core_stack_for_cache_stability(self):
        text = (ROOT / "Dockerfile").read_text()
        core_run = text.index("RUN /opt/pilot/build/install-core-stack.sh")
        ai_toolkit_copy = text.index("COPY scripts/build/install-ai-toolkit.sh")
        invoke_copy = text.index("COPY scripts/build/install-invoke.sh")
        self.assertGreater(ai_toolkit_copy, core_run)
        self.assertGreater(invoke_copy, core_run)

    def test_build_scripts_are_copied_before_they_are_used(self):
        lines = (ROOT / "Dockerfile").read_text().splitlines()
        copied = {}
        used = {}
        for index, line in enumerate(lines):
            for script in re.findall(r"scripts/build/(?:lib/|patches/)?([^\s/]+\.sh)", line):
                copied.setdefault(script, index)
            if line.lstrip().startswith("COPY "):
                continue
            for script in re.findall(r"/opt/pilot/build/(?:lib/|patches/)?([^\s/]+\.sh)", line):
                if not script.startswith("*"):
                    used.setdefault(script, index)

        missing = sorted(script for script in used if script not in copied)
        late = sorted(script for script, index in used.items() if copied.get(script, index + 1) > index)
        self.assertEqual(missing, [])
        self.assertEqual(late, [])

    def test_comfy_torchaudio_patch_is_applied_during_build(self):
        install_text = (ROOT / "scripts/build/install-comfy.sh").read_text()
        docker_text = (ROOT / "Dockerfile").read_text()
        patch_text = (ROOT / "scripts/build/patches/patch-comfy.sh").read_text()
        self.assertIn("/opt/pilot/build/patches/patch-comfy.sh /opt/pilot/repos/ComfyUI", install_text)
        self.assertIn("COPY scripts/build/patches/patch-comfy.sh /opt/pilot/build/patches/", docker_text)
        self.assertIn("def _require_torchaudio()", patch_text)
        self.assertIn("except ModuleNotFoundError:", patch_text)

    def test_invoke_installs_local_xformers_to_shadow_core(self):
        text = (ROOT / "scripts/build/install-invoke.sh").read_text()
        self.assertIn(": \"${INVOKE_XFORMERS_VERSION:?INVOKE_XFORMERS_VERSION is required}\"", text)
        self.assertIn("\"xformers==${INVOKE_XFORMERS_VERSION}\"", text)

    def test_kohya_launchers_suppress_pkg_resources_warning_without_runtime_pip(self):
        warning_filter = "ignore:pkg_resources is deprecated as an API:UserWarning"
        for path in ("scripts/start-kohya.sh", "scripts/kohya.sh"):
            with self.subTest(path=path):
                text = (ROOT / path).read_text()
                self.assertIn(warning_filter, text)
                self.assertIn("from transformers import CLIPFeatureExtractor, Dinov2WithRegistersConfig", text)
                self.assertNotIn('pip install "setuptools<81.0"', text)

    def test_diffusion_pipe_suppresses_tensorboard_pkg_resources_warning(self):
        text = (ROOT / "scripts/diffusion-pipe.sh").read_text()

        self.assertIn('TENSORBOARD_WARNING_FILTER="ignore:pkg_resources is deprecated as an API:UserWarning"', text)
        self.assertIn('TENSORBOARD_PYTHONWARNINGS="${PYTHONWARNINGS:+${PYTHONWARNINGS},}${TENSORBOARD_WARNING_FILTER}"', text)
        self.assertGreaterEqual(text.count('PYTHONWARNINGS="${TENSORBOARD_PYTHONWARNINGS}"'), 3)
        self.assertNotIn('PYTHONWARNINGS="${PYTHONWARNINGS:-ignore:pkg_resources is deprecated as an API:UserWarning}"', text)

    def test_make_build_runs_dockerfile_check_first(self):
        text = (ROOT / "Makefile").read_text()
        self.assertIn(".PHONY: help build build-check", text)
        self.assertIn("build: build-check", text)
        self.assertIn("docker buildx build --check --platform $(PLATFORM)", text)

    def test_ai_toolkit_import_smoke_is_skipped_for_cross_platform_builds(self):
        text = (ROOT / "scripts/build/install-ai-toolkit.sh").read_text()
        self.assertIn(
            'Skipping AI Toolkit import smoke during cross-platform build (${BUILDPLATFORM} -> ${TARGETPLATFORM})',
            text,
        )
        self.assertIn(
            'if [[ -z "${BUILDPLATFORM}" || -z "${TARGETPLATFORM}" || "${BUILDPLATFORM}" == "${TARGETPLATFORM}" ]]; then\n'
            "  /opt/venvs/ai-toolkit/bin/python -c 'import peft; import timm; import open_clip; import lycoris; import lycoris.kohya; import torchao; import optimum.quanto'",
            text,
        )


if __name__ == "__main__":
    unittest.main()
