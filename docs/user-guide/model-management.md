# Model Management

_Last updated: 2026-09-10_

A video workflow may depend on several downloads before you can generate a frame. The main model is only part of the setup; text encoders, VAEs, and other components each have a place in the workflow. ControlPilot's Models page lets you review those requirements together and see what you already have.

Use the catalog to prepare for a specific project. You can search by family, inspect a workflow's files, and download what is missing into the shared workspace. That gives you a clearer starting point than a collection of filenames with no connection to the task you want to run.

## Choose a family and review its requirements

Open **Models** in ControlPilot. The **Catalog** view groups entries by model family and provides search, task, and family filters. Select a row to open its details panel. For LTX-2.5 and MiniMax H3, choose **Text to video** or **Image to video**, then select **Review installation**.

The review shows required files, installed files it can reuse, download sizes, destinations, available space, and source access. For LTX, the prompt enhancer is optional. Read the review before choosing **Download missing files**, especially if you are working with limited storage or a source that requires Hugging Face approval.

The requirements come from the four bundled workflow graphs. If you edit a graph or import another version, check its requirements as a separate workflow. Other catalog families expose individual models and components; select the variants that match the tool and workflow you intend to use.

## Follow the download through to completion

**Download missing files** queues the missing components and reuses active jobs. Access or disk-space failures block installation. Use **Downloads** to follow progress and inspect errors. After resolving a failure, retry the affected download or review the workflow again to skip components that have finished.

The queue belongs to the running ControlPilot process. Restarting ControlPilot loses that queue, while completed files remain on the persistent volume. After a restart, reopen the review and queue the remaining files. Avoid treating a queued job as a completed installation.

Open **Installed** to inspect downloaded entries, their file paths, and removal controls. Installation status describes file checks. You still need compatible nodes, an appropriate GPU setup, and a completed generation to establish that the workflow runs on your machine. The [inference guide](inference.md) covers that next stage.

## Understand what the file checks establish

For a single-file entry with an exact integer byte size in the manifest, the installed-state check expects that size at the canonical destination. Rounded sizes in older custom manifests remain estimates. Workflow preflight retrieves exact sizes for missing files when checking their sources.

For a repository entry, a successful pull records the required files and verifies weights and indexed shards. LoRA Pilot keeps that record under `/workspace/models/.download-state`. If you have an older repository download without a record, run `models pull` with its catalog name to verify cached files and create the record.

These checks help distinguish complete downloads from folders that merely exist. They do not replace a model compatibility check or a test generation. If a consuming application cannot see a completed download, check its model setup and refresh behavior before fetching another copy.

## Keep the catalog and destinations clear

The default active manifest is `/workspace/config/models.manifest`. The image's bundled default is `/opt/pilot/config/models.manifest.default`. Use `models where` inside the pod or container to identify the configured paths before editing or troubleshooting the catalog.

Bootstrap tracks the bundled manifest so it can refresh a previously seeded copy during upgrades and preserve later customizations. A workspace without that tracking record receives a one-time refresh. Back up a customized manifest before upgrading an older workspace, then compare your entries with the bundled catalog.

Each line uses the format `name|kind|source|subdir|include|size(optional)`. Supported kinds are `url`, `hf_file`, and `hf_repo`. The destination comes from the entry, under the model root, rather than from a category you choose afterward. Read the [manifest guide](../configuration/models-manifest.md) before adding a source or changing its layout.

Hugging Face downloads can use `HF_TOKEN` or the token configured through ControlPilot. A token does not grant access that the source account has not received. If access fails, read the job's response and check the relevant source and account permissions.

## Use the terminal for a named download

On RunPod, run operational commands in the pod's terminal. On a Docker Compose host, enter the container with `docker compose exec lora-pilot bash` first. The following example inspects the configured catalog and downloads the SDXL base entry.

```bash
models where
models list
models pull sdxl-base
```

Use `models help` to inspect the supported syntax. The CLI accepts one manifest name per pull. It also provides `models pull-all`, which targets the entire active catalog. Review the scope and storage before using that command for a workspace with many large entries.

An optional `--dir` changes the download destination relative to the model root. For example, `models pull sdxl-base --dir custom/sdxl-base` writes into that alternate location. It does not update the catalog's canonical installed-state path. Use the default destination unless your workflow has a reason to use another one.

For a single command from a Compose host, use `docker compose exec lora-pilot models pull sdxl-base`. The [CLI reference](../reference/cli-commands.md) explains service controls and the other supported commands. Removal belongs to ControlPilot's **Installed** view rather than a `models remove` subcommand.

## Connect an automated workflow

For automation, `GET /api/models` returns catalog entries and `GET /api/models/pulls` returns recent download jobs. Start a background download with `POST /api/models/{name}/pull/start` and inspect it through `GET /api/models/{name}/pull/status`. The synchronous alternative is `POST /api/models/{name}/pull`, while removal uses `POST /api/models/{name}/delete`.

Bundled workflow metadata is available through `GET /api/models/workflows`. Use the workflow-specific `/plan` and `/install` routes to review and submit a complete installation; installation requires the current plan identifier. Authenticated requests use the `controlpilot_session` cookie when password protection is enabled. Consult the [API reference](../development/api-reference.md) and preserve the browser's review-before-install behavior in your own integration.

## Existing downloads and corrected names

Single Hugging Face files use the entry's subdirectory followed by the filename, without repeating upstream directories such as `vae/vae`. The downloader verifies a source hash before reusing a legacy nested file. It preserves legacy copies and keeps an existing file intact until its replacement finishes. Removing an entry targets its canonical file.

Older ControlNet and VAE files named `diffusion_pytorch_model.safetensors` can be ambiguous. The corrected entries use model-specific subdirectories and preserve the old files. Z-Image's `ae.safetensors` uses `vae/z-image` to distinguish it from FLUX's file with the same name.

Some catalog names also changed. `realistic-vision-v6-sd15` replaces the misleading `realistic-vision-xl` name and identifies an SD1.5 model. `swin2sr-4x` replaces `swinir-4x`, and `gfpgan-v1.4` replaces `esrgan-4x`. The CLI accepts those old names as aliases when the active manifest contains the corrected entries. Existing GFPGAN and Swin2SR files remain preserved, but their corrected destinations need another pull. Real-ESRGAN entries are unchanged.

## Diagnose a failed download or catalog load

For a failed download, read its job output in **Downloads** and check the active manifest with `models where`. Run `df -h /workspace/models` inside the container to inspect available space. The ControlPilot logs at `/workspace/logs/controlpilot.err.log` and `/workspace/logs/controlpilot.out.log` provide additional context.

For a 404 from a model source, compare the repository and file path in the active manifest with the current upstream source. Preserve your custom catalog and correct the affected entry rather than replacing unrelated entries. The [debugging guide](../development/debugging.md) explains the relevant API checks.

An affected v2.5.8-era container can show **Could not load models: Internal Server Error** because its code looks for workflow assets in `/opt/pilot/config/comfy-workflows`, while the image stores them in `/opt/pilot/bundled/comfy-workflows`. The corrected source reads the bundled path and retains a local-development fallback. Existing images require a rebuild to include that change.

For that specific path mismatch, confirm that the bundled directory exists and the expected configuration path is absent. Then run this command in the affected container and refresh Models.

```bash
ln -sT /opt/pilot/bundled/comfy-workflows /opt/pilot/config/comfy-workflows
```

The compatibility link refuses to overwrite an existing destination and requires no service restart. It leaves model weights in place. Because the link belongs to the container filesystem, use an image containing the source fix when you replace the container. Other HTTP 500 failures need their own log diagnosis.
