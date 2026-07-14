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
        rf"ARG {re.escape(name)}=([^\s#]*)",
        rf"{re.escape(name)} \?= ?([^\s#]*)",
        rf"^{re.escape(name)}=([^\s#]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return match.group(1)
    raise AssertionError(f"{name} not found in {path}")


class BuildPinTests(unittest.TestCase):
    def test_node_tooling_uses_pinned_npm_version(self):
        expected_node = "24"
        expected_npm = "11.18.0"
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                self.assertEqual(read_pin(path, "NODE_MAJOR"), expected_node)
                self.assertEqual(read_pin(path, "NPM_VERSION"), expected_npm)

        make_text = (ROOT / "Makefile").read_text()
        system_tools = (ROOT / "scripts/build/install-system-tools.sh").read_text()

        self.assertIn('--build-arg NODE_MAJOR="$(NODE_MAJOR)"', make_text)
        self.assertIn('--build-arg NPM_VERSION="$(NPM_VERSION)"', make_text)
        self.assertIn(': "${NODE_MAJOR:?NODE_MAJOR is required}"', system_tools)
        self.assertIn(': "${NPM_VERSION:?NPM_VERSION is required}"', system_tools)
        self.assertIn("https://deb.nodesource.com/node_${NODE_MAJOR}.x", system_tools)
        self.assertNotIn("setup_20.x", system_tools)
        self.assertNotIn("| bash", system_tools)
        self.assertIn('npm install -g "npm@${NPM_VERSION}"', system_tools)

    def test_ai_toolkit_patch_removes_deprecated_next_dev_indicator(self):
        patch_text = (ROOT / "scripts/build/patches/patch-ai-toolkit.sh").read_text()

        self.assertIn("next.config.ts", patch_text)
        self.assertIn("devIndicators", patch_text)
        self.assertIn("buildActivity", patch_text)

    def test_ai_toolkit_patch_preserves_ltx23_model_support(self):
        patch = ROOT / "scripts/build/patches/patch-ai-toolkit.sh"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "ai-toolkit"
            ltx2_dir = repo / "extensions_built_in/diffusion_models/ltx2"
            ltx2_dir.mkdir(parents=True)
            init_file = repo / "extensions_built_in/diffusion_models/__init__.py"
            init_file.write_text(
                "from .ltx2 import LTX2Model, LTX23Model\n"
                "AI_TOOLKIT_MODELS = [LTX2Model, LTX23Model]\n"
            )
            (ltx2_dir / "__init__.py").write_text(
                "from .ltx2 import LTX2Model, LTX23Model\n"
            )

            subprocess.run(["bash", str(patch), str(repo), "0"], check=True)

            self.assertTrue(ltx2_dir.is_dir())
            self.assertIn("LTX23Model", init_file.read_text())

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
            "COMFYUI_DOWNLOADER_REF": "03146df738191004a8aad8264dca5c3530907f56",
        }
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                for name, value in expected.items():
                    self.assertEqual(read_pin(path, name), value)

        install_text = (ROOT / "scripts/build/install-comfy.sh").read_text()
        comfy_script = (ROOT / "scripts/comfy.sh").read_text()
        self.assertIn(": \"${COMFYUI_DOWNLOADER_REF:?COMFYUI_DOWNLOADER_REF is required}\"", install_text)
        self.assertIn("comfyui_manager==${COMFYUI_MANAGER_REF}", install_text)
        self.assertIn("manager_requirements.txt", install_text)
        self.assertIn("${COMFYUI_DOWNLOADER_REF}", install_text)
        self.assertIn("MANAGER_FLAGS=(--enable-manager)", comfy_script)
        self.assertIn("COMFY_MANAGER_LEGACY_UI", comfy_script)
        self.assertIn("MANAGER_FLAGS=(--enable-manager-legacy-ui)", comfy_script)
        self.assertIn('COMFY_MANAGER_NETWORK_MODE="${COMFY_MANAGER_NETWORK_MODE:-personal_cloud}"', comfy_script)
        self.assertIn('COMFY_MANAGER_SECURITY_LEVEL="${COMFY_MANAGER_SECURITY_LEVEL:-normal}"', comfy_script)
        self.assertIn('"allow_git_url_install", "COMFY_MANAGER_ALLOW_GIT_URL_INSTALL"', comfy_script)
        self.assertIn('"allow_pip_install", "COMFY_MANAGER_ALLOW_PIP_INSTALL"', comfy_script)
        self.assertNotIn("custom_nodes/ComfyUI-Manager", install_text)
        self.assertNotIn("/opt/pilot/bundled/comfy-custom-nodes/ComfyUI-Manager", comfy_script)
        self.assertNotIn("git clone --depth 1 https://github.com/romandev-codex/ComfyUI-Downloader.git", install_text)

    def test_diffpipe_uses_latest_verified_ref(self):
        expected = "a7e7decf4325c1f03e4b88b7de93640029abd011"
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                self.assertEqual(read_pin(path, "DIFFPIPE_REF"), expected)

    def test_core_stack_uses_cu130_torch_triplet(self):
        expected = {
            "TORCH_VERSION": "2.11.0",
            "TORCHVISION_VERSION": "0.26.0",
            "TORCHAUDIO_VERSION": "2.11.0",
            "XFORMERS_VERSION": "0.0.35",
            "TRANSFORMERS_VERSION": "5.11.0",
            "UV_VERSION": "0.11.26",
            "DEEPDIFF_VERSION": "9.1.0",
            "GGUF_VERSION": "0.19.0",
        }
        for path in ("Dockerfile", "build.env.example"):
            with self.subTest(path=path):
                for name, value in expected.items():
                    self.assertEqual(read_pin(path, name), value)

        make_text = (ROOT / "Makefile").read_text()
        self.assertIn("TORCH_VERSION ?= 2.11.0", make_text)
        self.assertIn("TORCHVISION_VERSION ?= 0.26.0", make_text)
        self.assertIn("TORCHAUDIO_VERSION ?= 2.11.0", make_text)
        self.assertRegex(make_text, r"TORCHVISION_VERSION \?= 0\.26\.0\nTORCHAUDIO_VERSION \?= 2\.11\.0\nTORCH_INDEX_URL \?= https://download\.pytorch\.org/whl/cu130")

        core_stack = (ROOT / "scripts/build/install-core-stack.sh").read_text()
        self.assertIn('"torchaudio==${TORCHAUDIO_VERSION}"', core_stack)
        self.assertRegex(core_stack, r'"xformers==\$\{XFORMERS_VERSION\}" \\\n\s+--index-url "\$\{TORCH_INDEX_URL\}"')
        self.assertIn('"uv==${UV_VERSION}"', core_stack)
        self.assertIn('"deepdiff==${DEEPDIFF_VERSION}"', core_stack)
        self.assertIn('"gguf==${GGUF_VERSION}"', core_stack)
        self.assertIn('core_import_modules="torchaudio ${core_import_modules}"', core_stack)
        self.assertIn('CORE_IMPORT_MODULES="${core_import_modules}"', core_stack)

    def test_runtime_service_dependencies_are_pinned(self):
        expected = {
            "FASTAPI_VERSION": "0.139.0",
            "UVICORN_VERSION": "0.50.0",
            "PYDANTIC_VERSION": "2.13.4",
            "PYTHON_MULTIPART_VERSION": "0.0.32",
            "FLASK_VERSION": "3.1.3",
            "FLASK_CORS_VERSION": "6.0.5",
            "REQUESTS_VERSION": "2.34.2",
            "PYTHON_DOTENV_VERSION": "1.2.2",
            "PYTHON_SOCKETIO_VERSION": "5.16.3",
            "WEBSOCKETS_VERSION": "16.0",
            "HTTPX_VERSION": "0.28.1",
            "TENSORBOARD_VERSION": "2.21.0",
        }
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                for name, value in expected.items():
                    self.assertEqual(read_pin(path, name), value)

        core_stack = (ROOT / "scripts/build/install-core-stack.sh").read_text()
        self.assertIn('"fastapi==${FASTAPI_VERSION}"', core_stack)
        self.assertIn('"uvicorn[standard]==${UVICORN_VERSION}"', core_stack)
        self.assertIn('"httpx==${HTTPX_VERSION}"', core_stack)

        diffpipe = (ROOT / "scripts/build/install-diffpipe.sh").read_text()
        self.assertIn(': "${TENSORBOARD_VERSION:?TENSORBOARD_VERSION is required}"', diffpipe)
        self.assertIn('"tensorboard==${TENSORBOARD_VERSION}"', diffpipe)

    def test_generated_invoke_constraints_use_invoke_torch_stack(self):
        env = os.environ.copy()
        env.update(
            {
                "TORCH_VERSION": "2.11.0",
                "TORCHVISION_VERSION": "0.26.0",
                "TORCHAUDIO_VERSION": "2.11.0",
                "XFORMERS_VERSION": "0.0.35",
                "BITSANDBYTES_VERSION": "0.49.2",
                "CORE_DIFFUSERS_VERSION": "0.38.0",
                "TRANSFORMERS_VERSION": "5.11.0",
                "UV_VERSION": "0.11.26",
                "DEEPDIFF_VERSION": "9.1.0",
                "GGUF_VERSION": "0.19.0",
                "TOMLKIT_VERSION": "0.15.0",
                "PEFT_VERSION": "0.19.1",
                "ACCELERATE_VERSION": "1.14.0",
                "HF_HUB_VERSION": "1.19.0",
                "FASTAPI_VERSION": "0.139.0",
                "UVICORN_VERSION": "0.50.0",
                "PYDANTIC_VERSION": "2.13.4",
                "PYTHON_MULTIPART_VERSION": "0.0.32",
                "FLASK_VERSION": "3.1.3",
                "FLASK_CORS_VERSION": "6.0.5",
                "REQUESTS_VERSION": "2.34.2",
                "PYTHON_DOTENV_VERSION": "1.2.2",
                "PYTHON_SOCKETIO_VERSION": "5.16.3",
                "WEBSOCKETS_VERSION": "16.0",
                "HTTPX_VERSION": "0.28.1",
                "INVOKE_TORCH_VERSION": "2.7.1+cu128",
                "INVOKE_TORCHVISION_VERSION": "0.22.1+cu128",
                "INVOKE_XFORMERS_VERSION": "0.0.31.post1",
                "INVOKE_DIFFUSERS_VERSION": "0.37.0",
                "INVOKE_TRANSFORMERS_VERSION": "5.5.4",
                "INVOKE_ACCELERATE_VERSION": "1.14.0",
                "INVOKE_HF_HUB_VERSION": "1.22.0",
                "DIFFPIPE_DIFFUSERS_VERSION": "0.38.0",
                "DIFFPIPE_TRANSFORMERS_VERSION": "5.11.0",
                "TENSORBOARD_VERSION": "2.21.0",
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                ["bash", str(ROOT / "scripts/build/write-constraints.sh"), tmp],
                check=True,
                env=env,
            )
            constraints = (Path(tmp) / "invoke-constraints.txt").read_text()
            core_constraints = (Path(tmp) / "core-constraints.txt").read_text()
            diffpipe_constraints = (Path(tmp) / "diffpipe-constraints.txt").read_text()

        self.assertIn("torch==2.7.1+cu128\n", constraints)
        self.assertIn("torchvision==0.22.1+cu128\n", constraints)
        self.assertIn("xformers==0.0.31.post1\n", constraints)
        self.assertIn("diffusers==0.37.0\n", constraints)
        self.assertIn("transformers==5.5.4\n", constraints)
        self.assertNotIn("torch==2.11.0\n", constraints)
        self.assertNotIn("torchaudio==", constraints)
        self.assertIn("torchaudio==2.11.0\n", core_constraints)
        self.assertIn("torchaudio==2.11.0\n", diffpipe_constraints)
        self.assertIn("deepdiff==9.1.0\n", core_constraints)
        self.assertIn("gguf==0.19.0\n", core_constraints)

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
        core_run = text.index("\n    /opt/pilot/build/install-core-stack.sh")
        ai_toolkit_copy = text.index("COPY scripts/build/install-ai-toolkit.sh")
        invoke_copy = text.index("COPY scripts/build/install-invoke.sh")
        self.assertGreater(ai_toolkit_copy, core_run)
        self.assertGreater(invoke_copy, core_run)

    def test_dependency_cache_busts_cover_relevant_pins(self):
        text = (ROOT / "Dockerfile").read_text()
        expected = {
            "TORCH_CACHE_BUST": (
                "TORCH_VERSION",
                "TORCHVISION_VERSION",
                "TORCHAUDIO_VERSION",
                "XFORMERS_VERSION",
                "BITSANDBYTES_VERSION",
                "CORE_DIFFUSERS_VERSION",
                "TRANSFORMERS_VERSION",
                "DEEPDIFF_VERSION",
                "GGUF_VERSION",
                "HF_HUB_VERSION",
                "FASTAPI_VERSION",
                "PYDANTIC_VERSION",
            ),
            "DIFFPIPE_CACHE_BUST": (
                "DIFFPIPE_REF",
                "DIFFPIPE_DIFFUSERS_VERSION",
                "DIFFPIPE_TRANSFORMERS_VERSION",
                "TENSORBOARD_VERSION",
            ),
            "INVOKE_CACHE_BUST": (
                "INVOKEAI_VERSION",
                "INVOKE_TORCH_VERSION",
                "INVOKE_TORCHVISION_VERSION",
                "INVOKE_XFORMERS_VERSION",
                "INVOKE_DIFFUSERS_VERSION",
                "INVOKE_TRANSFORMERS_VERSION",
                "INVOKE_ACCELERATE_VERSION",
                "INVOKE_HF_HUB_VERSION",
            ),
            "AI_TOOLKIT_CACHE_BUST": (
                "AI_TOOLKIT_REF",
                "AI_TOOLKIT_DIFFUSERS_VERSION",
                "INSTALL_AI_TOOLKIT_UI",
            ),
        }
        for name, pins in expected.items():
            with self.subTest(name=name):
                match = re.search(rf"ARG {name}=([^\n]+)", text)
                self.assertIsNotNone(match)
                value = match.group(1)
                for pin in pins:
                    self.assertIn(pin, value)
                self.assertIn(f'echo "{name}=${{{name}}}" >/dev/null', text)

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
        for path in (
            "comfy_extras/nodes_audio.py",
            "comfy_extras/nodes_lt.py",
            "comfy_extras/nodes_lt_audio.py",
            "comfy_extras/nodes_audio_encoder.py",
            "comfy_extras/nodes_wandancer.py",
        ):
            with self.subTest(path=path):
                self.assertIn(path, patch_text)

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
