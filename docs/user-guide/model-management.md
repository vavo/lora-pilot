# Model Management

_Last updated: 2026-07-26_

ControlPilot manages the model catalogue in `/workspace/models`. On RunPod,
the pod terminal is already inside the LoRA Pilot container: run commands
directly. Do not use Docker inside the pod. On a separate Docker Compose host,
prefix commands with `docker exec lora-pilot`.

## ControlPilot

Open **Models** in ControlPilot to browse the bundled manifest, start a pull,
monitor its status, and delete an installed model. The browser uses the same
manifest and downloader as the CLI.

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
