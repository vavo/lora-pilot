# LoRA Pilot Agent Notes

## Scope

- This repo builds the LoRA Pilot Docker image and bundled runtime workspace. Keep changes surgical; image build pins, startup scripts, manifests, and docs are tightly coupled.
- Treat `docs/configuration/environment-variables.md`, `docs/development/building.md`, and `docs/configuration/models-manifest.md` as the current reference docs when touching build args or model manifest behavior.
- Do not touch generated or host noise files such as `.DS_Store`.

## Commands

- `make build-check` runs Docker buildx static checks with the full Makefile build-arg set, without running install layers.
- `make build CUDA_PROFILE=cu130` builds the default Blackwell/CUDA 13.0 image and runs `build-check` first.
- `make build CUDA_PROFILE=cu128` uses the legacy CUDA 12.8 profile.
- `make run`, `make logs`, `make shell`, and `make urls` operate on the local `lp-test` container and bind-mount `./workspace` to `/workspace`.
- Lightweight local regression checks:
  - `python3 -m unittest tests/test_build_pins.py`
  - `python3 -m unittest tests/test_models_manifest.py`

## Build Pin Workflow

- Keep Dockerfile `ARG`s, Makefile defaults/build args, `build.env.example`, and build docs aligned when changing build-time variables.
- `CUDA_PROFILE=cu130` currently leaves `TORCHAUDIO_VERSION` empty because there is no matching torchaudio wheel in the official cu130 index.
- InvokeAI uses its own CUDA 12.8-compatible Torch/xFormers stack inside `/opt/venvs/invoke`; do not collapse it back into the shared core stack just because it looks tidier.
- AI Toolkit keeps its own venv and imports the shared core GPU stack via the build helper `.pth` flow.

## Model Manifest Workflow

- Keep `config/models.manifest` and `config/models.manifest.default` byte-identical.
- Validate manifest edits with `python3 -m unittest tests/test_models_manifest.py` and, in an image/container, `models list` or `scripts/get-models.sh list`.
- Verify exact upstream filenames, repo ids, include globs, and release URLs before changing manifest entries. Guessing model URLs is how stale links get reincarnated with better punctuation.
- Runtime manifest seeding uses `/workspace/config/models.manifest` with `/opt/pilot/config/models.manifest.default` as the image fallback.

## Runtime Notes

- Diffusion Pipe starts TensorBoard only when `DIFFPIPE_CONFIG` is unset; with a config it launches TensorBoard plus `deepspeed`.
- Kohya and Diffusion Pipe launchers intentionally suppress the `pkg_resources` warning at runtime rather than installing older setuptools during startup.
- ComfyUI has a build patch for optional torchaudio behavior under the cu130 profile; keep `scripts/build/patches/patch-comfy.sh` and its tests aligned if Comfy upstream changes.
