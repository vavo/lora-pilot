# Models Manifest

_Last updated: 2026-09-07_

LoRA Pilot model downloads are driven by a pipe-delimited manifest file.

## Locations

Runtime paths used by scripts and ControlPilot:

- Active manifest: `/workspace/config/models.manifest`
- Default fallback: `/opt/pilot/config/models.manifest.default`

Repository sources:

- `config/models.manifest` (copied into the image as `/opt/pilot/config/models.manifest.default`)
- `config/models.manifest.default` (kept aligned as the repo reference list)

## Bootstrap Refresh Behavior

At container bootstrap, the bundled manifest is checked against the persistent runtime manifest:

- A missing runtime manifest is created from `/opt/pilot/config/models.manifest.default`.
- When a new image contains a different bundled manifest, the managed runtime manifest is refreshed.
- The first migration backs up the previous file as `/workspace/config/models.manifest.pre-refresh.<timestamp>`.
- If the runtime manifest was edited, bootstrap preserves it and logs that it is customized.

The bundle hash is stored at `/workspace/config/.models.manifest.bundle.sha256`. This lets persistent RunPod volumes receive catalogue updates without requiring Docker access inside the Pod.

## Line Format

One model per line:

```text
name|kind|source|subdir|include|size
```

Fields:

- `name`: stable ID used by CLI/API (`models pull <name>`, `/api/models/{name}/pull/start`)
- `kind`: `hf_file`, `hf_repo`, or `url`
- `source`:
  - `hf_file`: `<repo_id>:<path_in_repo>`
  - `hf_repo`: `<repo_id>`
  - `url`: direct URL
- `subdir`: destination under `/workspace/models`
- `include`: optional, only relevant for `hf_repo` (comma-separated glob patterns)
- `size`: optional expected size (`TB`, `GB`, `MB`, `KB`, or bytes). Bundled entries use exact bytes from upstream metadata; repository sizes sum the selected files.

Comments (`# ...`) and empty lines are ignored.

## Current Kind Usage (Repo Manifests)

- `hf_file`: primary mechanism
- `hf_repo`: used for selected repos
- `url`: direct download URLs for non-Hugging Face assets, including the current Real-ESRGAN and GFPGAN entries

## Real Examples

```text
sdxl-base|hf_file|stabilityai/stable-diffusion-xl-base-1.0:sd_xl_base_1.0.safetensors|checkpoints||6938078334
juggernaut-xl|hf_repo|RunDiffusion/Juggernaut-XL|checkpoints|*.safetensors|6938040706
wan2.2-animate-14b|hf_repo|Wan-AI/Wan2.2-Animate-14B|wan/wan2.2-animate-14b|*.json,*.safetensors,*.pth,google/umt5-xxl/*,README.md|56357501157
minimax-h3-fl2va-int8|hf_file|Comfy-Org/MiniMax-H3:diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors|diffusion_models||20970379616
ltx-2.5-distilled-int8|hf_file|Lightricks/LTX-2.5:diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors|diffusion_models||21504034224
```

The bundled manifests include Comfy-ready quantized Ideogram 4, Lens, and PixelDiT entries. They reuse the existing `flux2-vae` entry when a Flux 2 VAE is needed instead of duplicating that model under each pack.

## CLI + API That Use This Manifest

### CLI (`/opt/pilot/get-models.sh`, symlinked as `models` and `pilot-models`)

- `models list`
- `models pull <name>`
- `models pull-all`
- `models where`

Environment overrides:

- `WORKSPACE_ROOT` (default `/workspace`)
- `MODELS_DIR` (default `${WORKSPACE_ROOT}/models`)
- `MODELS_MANIFEST` (default `${WORKSPACE_ROOT}/config/models.manifest`)
- `DEFAULT_MODELS_MANIFEST` (default `/opt/pilot/config/models.manifest.default`)

### ControlPilot API

- `GET /api/models`
- `POST /api/models/{name}/pull`
- `POST /api/models/{name}/pull/start`
- `GET /api/models/{name}/pull/status`
- `GET /api/models/pulls`
- `POST /api/models/{name}/delete`
- `GET /api/models/workflows`
- `POST /api/models/workflows/{workflow_id}/plan`
- `POST /api/models/workflows/{workflow_id}/install`

Workflow plans derive their dependencies from `config/comfy-workflows/*.json`.
The plan request accepts `optional` filenames; installation accepts the same
selection plus the returned `plan_id` and repeats access/storage checks.

## Install Detection Rules (ControlPilot)

For each entry, `apps/Portal/services/models.py` computes `installed`, `size_bytes`, and links:

- `hf_file` and `url`: require a nonempty file at `<subdir>/<basename>` with the
  manifest's exact byte size, when specified as integer bytes. Rounded unit
  values in custom manifests remain estimates and use the legacy nonempty-file
  check. Legacy nested locations are
  reported separately and do not count as installed.
- `hf_repo`: requires a completion receipt matching the source/include filter,
  recorded file sizes and valid weights/shards. A pull creates or repairs it.

The single-file downloader uses an isolated staging directory, an atomic final
move, and a destination lock. Legacy HF files are reused only after hash
verification. See [migration details](../user-guide/model-management.md#existing-downloads-and-corrected-names).

## Deletion Behavior

Deletion uses manifest metadata to avoid broad accidental removal:

- `hf_file` and `url`: delete expected concrete files
- `hf_repo`: delete matched files only

For shared top-level model folders, repo-file selection has an extra guard to avoid deleting unrelated files when name matching fails.

## Editing Workflow

1. Ensure manifest exists:
   - run `models where` or open Models tab in ControlPilot.
2. Edit `/workspace/config/models.manifest`.
3. Validate quickly:
   - `models list`
4. Pull one entry:
   - `models pull <name>`
5. Refresh ControlPilot Models tab.

On RunPod, run the commands directly in the pod terminal. Do not use
`docker exec lora-pilot`; that prefix is only for a Docker Compose host.

## Related

- [Environment Variables](environment-variables.md)
- [Docker Compose](docker-compose.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
