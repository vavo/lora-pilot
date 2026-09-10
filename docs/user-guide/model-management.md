# Model Management

_Last updated: 2026-09-09_

ControlPilot manages the model catalogue in `/workspace/models`. On RunPod,
the pod terminal is already inside the LoRA Pilot container: run commands
directly. Do not use Docker inside the pod. On a separate Docker Compose host,
prefix commands with `docker exec lora-pilot`.

## ControlPilot

Open **Models** in ControlPilot. **Catalog** lists model families with task and
installation status. Search the list or narrow it with the task and family
filters. Select a row to open its details panel. For LTX-2.5 and MiniMax H3,
choose **Text to video** or **Image to video**, then **Review installation**.
The review lists exact required files, installed files to reuse, download sizes,
destinations, free space and source access. The LTX prompt enhancer is optional.
**Download missing files** queues only missing components and reuses active jobs.
Failed downloads can be retried from **Downloads**; reviewing again skips files
that have since finished. Access or disk-space failures block installation.

These lists come directly from the four bundled workflow graphs. They describe
the bundled versions, not user-edited copies. Other families expose individual
models and components; choose the variants your workflow needs.

**Installed** lists downloaded entries with file paths and removal controls.
**Downloads** shows recent progress, errors, and retries. Queued jobs run in the
Portal process; restarting Portal loses the queue. Completed files remain on
the persistent volume. Reopen the review to queue the remaining files.
File installation does not confirm GPU compatibility or successful generation.

Repository (`hf_repo`) entries appear installed only after a successful pull
records required files and verifies weights and indexed shards. The record lives
under `/workspace/models/.download-state`. Existing repository downloads without
a record need one `models pull <name>` to verify cached files and create it.
Single files must have the exact byte size at their canonical destination when
the manifest specifies integer bytes. Rounded sizes in older custom manifests
remain estimates; workflow preflight fetches exact sizes for missing files.

## Models page reports Internal Server Error

The v2.5.8 image code looks for workflow assets in `/opt/pilot/config/comfy-workflows`, while Docker bundles them in `/opt/pilot/bundled/comfy-workflows`. A failed `/api/models/workflows` request prevents the page from showing the catalog, even when `/api/models` succeeds.

The source fix reads the bundled directory and keeps the repository path for local development. For an existing affected container, run this in its terminal, then refresh Models:

```bash
ln -sT /opt/pilot/bundled/comfy-workflows /opt/pilot/config/comfy-workflows
```

This command creates a compatibility link and refuses to overwrite an existing destination. It does not move model weights or require a service restart. The link belongs to the container filesystem; use a rebuilt image containing the fix when replacing the container.

## Existing downloads and corrected names

Single Hugging Face files now land at `<subdir>/<filename>`, without repeating
upstream directories such as `vae/vae`. A pull verifies the source hash before
reusing a legacy nested file. Existing files remain intact until a replacement
finishes, and legacy copies are preserved. Removing an entry deletes only its
canonical file. Old ControlNet/VAE files named `diffusion_pytorch_model.safetensors`
are ambiguous: the downloader preserves them and fetches into a model-specific
subdirectory. Z-Image's `ae.safetensors` also has its own `vae/z-image` directory
to avoid shared deletion with FLUX.

The corrected names are `realistic-vision-v6-sd15` (SD1.5, formerly
`realistic-vision-xl`), `swin2sr-4x` (a Transformers repository, formerly
`swinir-4x`), and `gfpgan-v1.4` (face restoration, formerly `esrgan-4x`). The CLI
accepts the old names as aliases when the active manifest uses the new names.
Old GFPGAN and Swin2SR downloads are preserved; their corrected destinations
need a new pull. Real-ESRGAN entries are unchanged.

## Supported CLI

The image currently exposes these commands:

```bash
models list
models pull <name> [--dir SUBDIR]
models pull-all
models where
models help
```

Examples for a RunPod terminal:

```bash
models list
models where
models pull sdxl-base
models pull sdxl-base --dir custom/sdxl-base
models pull-all
```

The `--dir` value is relative to `/workspace/models` and cannot escape that
directory. `models where` prints the active manifest and model directory.

Docker Compose host equivalents:

```bash
docker exec lora-pilot models list
docker exec lora-pilot models pull sdxl-base
```

The CLI accepts one manifest name per `models pull` invocation. It does not
support `validate`, `update`, `cleanup`, collections, arbitrary repository IDs,
or the other subcommands/flags sometimes shown in older guides. Use the
ControlPilot API for browser-managed pulls and deletion.

## Manifest and storage

The active manifest is `/workspace/config/models.manifest`. The bundled image
default is `/opt/pilot/config/models.manifest.default`; bootstrap refreshes
bundled app/docs/default content while preserving user-customized runtime
configuration.

Model files are stored below:

```text
/workspace/models/
├── checkpoints/
├── loras/
├── vae/
├── controlnet/
├── upscale_models/
└── ...
```

The exact destination is defined by each manifest entry. Use `models list` and
`models where` rather than assuming a category directory or model name.

Manifest entries use this format:

```text
name|kind|source|subdir|include|size(optional)
```

Supported kinds are `url`, `hf_file`, and `hf_repo`. Gated Hugging Face pulls
use the `HF_TOKEN` environment variable or the token configured through
ControlPilot.

## Download failures

Run these checks directly on RunPod:

```bash
models where
models list
ls -la /workspace/config/models.manifest
df -h /workspace/models
command -v hf || ls -l /opt/venvs/core/bin/hf /opt/venvs/core/bin/huggingface-cli
```

For a failed model, check the ControlPilot job output and the service logs:

```bash
tail -n 200 /workspace/logs/controlpilot.err.log
tail -n 200 /workspace/logs/controlpilot.out.log
```

If a Hugging Face entry returns 404, verify the repository and file path in
the active manifest against the current upstream repository. Do not replace a
user-customized manifest automatically; edit or restore that entry explicitly.

## Integration

ComfyUI, Kohya, AI Toolkit, and InvokeAI share `/workspace/models`. A model
download succeeding only means the files were written; the consuming service
may need a restart or a model-library refresh before the file appears in its
UI.

## API endpoints

ControlPilot exposes model operations at:

```text
GET  /api/models
POST /api/models/{name}/pull
POST /api/models/{name}/pull/start
GET  /api/models/{name}/pull/status
GET  /api/models/pulls
POST /api/models/{name}/delete
```

Authenticated API requests must send the `controlpilot_session` cookie when
password protection is enabled.
