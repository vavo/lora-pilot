# Models Manifest

LoRA Pilot model downloads are driven by a pipe-delimited manifest file.

## Locations

Runtime paths used by scripts and ControlPilot:

- Active manifest: `/workspace/config/models.manifest`
- Default fallback: `/opt/pilot/config/models.manifest.default`

Repository sources:

- `config/models.manifest` (copied into the image as `/opt/pilot/config/models.manifest.default`)
- `config/models.manifest.default` (additional reference list in repo)

## Seeding Behavior

Both the CLI downloader and ControlPilot manifest parser call `ensure_manifest(...)`:

- If `/workspace/config/models.manifest` is missing
- And `/opt/pilot/config/models.manifest.default` exists
- It copies the default into `/workspace/config/models.manifest`

That means first run creates an editable workspace-local manifest automatically.

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
- `size`: optional expected size (`TB`, `GB`, `MB`, `KB`, or bytes)

Comments (`# ...`) and empty lines are ignored.

## Current Kind Usage (Repo Manifests)

- `hf_file`: primary mechanism
- `hf_repo`: used for selected repos
- `url`: supported by downloader/parser, but no current entries in `config/models.manifest` or `config/models.manifest.default`

## Real Examples

```text
sdxl-base|hf_file|stabilityai/stable-diffusion-xl-base-1.0:sd_xl_base_1.0.safetensors|checkpoints||6.94GB
juggernaut-xl|hf_repo|RunDiffusion/Juggernaut-XL|checkpoints|*.safetensors|6.94GB
wan2.2-animate-14b|hf_repo|Wan-AI/Wan2.2-Animate-14B|wan/wan2.2-animate-14b|*.json,diffusion_pytorch_model*.safetensors,model_index.json,README.md|72.40GB
```

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

## Install Detection Rules (ControlPilot)

For each entry, `apps/Portal/services/models.py` computes `installed`, `size_bytes`, and links:

- `hf_file`: expects file path from `source` (with basename fallback)
- `url`: expects URL basename in target dir
- `hf_repo`: scans target dir (optionally filtered by `include` glob list)

If matching files exist:

- `installed=true`
- `size_bytes` sums matched files (prefers `.safetensors` when available)

If no match but `size` exists:

- `installed=false`
- `size_bytes` uses parsed expected size

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

## Related

- [Environment Variables](environment-variables.md)
- [Docker Compose](docker-compose.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
