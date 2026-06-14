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
    def test_invokeai_613_uses_required_diffusers_pin(self):
        expected = "0.37.0"
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                self.assertEqual(read_pin(path, "INVOKEAI_VERSION"), "6.13.0")
                self.assertEqual(read_pin(path, "INVOKE_DIFFUSERS_VERSION"), expected)

    def test_invokeai_613_uses_supported_cuda_torch_stack(self):
        expected = {
            "INVOKE_TORCH_VERSION": "2.7.1+cu128",
            "INVOKE_TORCHVISION_VERSION": "0.22.1+cu128",
            "INVOKE_TORCH_INDEX_URL": "https://download.pytorch.org/whl/cu128",
        }
        for path in ("Dockerfile", "Makefile", "build.env.example"):
            with self.subTest(path=path):
                for name, value in expected.items():
                    self.assertEqual(read_pin(path, name), value)

    def test_generated_invoke_constraints_use_invoke_torch_stack(self):
        env = os.environ.copy()
        env.update(
            {
                "TORCH_VERSION": "2.12.0",
                "TORCHVISION_VERSION": "0.27.0",
                "TORCHAUDIO_VERSION": "",
                "XFORMERS_VERSION": "0.0.35",
                "BITSANDBYTES_VERSION": "0.49.2",
                "CORE_DIFFUSERS_VERSION": "0.38.0",
                "TRANSFORMERS_VERSION": "5.11.0",
                "PEFT_VERSION": "0.19.1",
                "ACCELERATE_VERSION": "1.14.0",
                "HF_HUB_VERSION": "1.19.0",
                "INVOKE_TORCH_VERSION": "2.7.1+cu128",
                "INVOKE_TORCHVISION_VERSION": "0.22.1+cu128",
                "INVOKE_DIFFUSERS_VERSION": "0.37.0",
                "INVOKE_TRANSFORMERS_VERSION": "4.57.6",
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
        self.assertIn("diffusers==0.37.0\n", constraints)
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
