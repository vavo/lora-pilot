# File Structure

_Last updated: 2026-09-10_

A project includes more than the final image. You may need the captions that shaped a LoRA, the configuration that produced a useful checkpoint, and the settings that let you repeat a generation. Knowing where those files live makes it easier to carry the work into your next session or recover it on another deployment.

LoRA Pilot separates the image's installed code from the workspace you use. Inside the container, `/opt/pilot` holds bundled code and assets. `/workspace` holds your project data and persistent application state. The host or cloud storage mounted there determines how long that data survives.

## Follow a project through the workspace

Downloaded model assets live under `/workspace/models`. A manifest entry defines the destination for each download, so use `models where` and the model catalog to confirm a path rather than guessing from a filename. The tree includes locations for checkpoints, LoRAs, VAEs, and other components that generation and training tools use.

Training collections live under `/workspace/datasets`. ControlPilot displays dataset folders with the `1_` prefix, such as `/workspace/datasets/1_ceramic_teapot`. Image-caption pairs stay together in those folders. Imported and completed saved archives use `/workspace/datasets/ZIPs`, while bootstrap also creates `/workspace/datasets/images` as part of the shared layout.

Generated work belongs under `/workspace/outputs`. ComfyUI uses the `comfy` subdirectory, InvokeAI uses `invoke` in the bundled integration, and AI Toolkit has an `ai-toolkit` output location. Check the chosen trainer's output configuration for a particular training run. The [dataset guide](../user-guide/dataset-preparation.md) and [inference guide](../user-guide/inference.md) explain how to use these locations from the interfaces.

## Preserve the settings around the files

Application state lives under `/workspace/apps` and `/workspace/config`. InvokeAI's root is `/workspace/apps/invoke`. ComfyUI's workspace-backed user assets and custom nodes live under `/workspace/apps/comfy`. Other applications have their own workspace roots or links into shared data; the [component guides](../components/README.md) describe their layouts.

MediaPilot keeps its database at `/workspace/config/mediapilot/data.db` in the bundled setup, and AI Toolkit uses `/workspace/config/ai-toolkit/aitk_db.db` by default. Applications create their database files as needed. Keep that state with the project if you want to preserve more than the underlying media files.

Runtime configuration includes `/workspace/config/models.manifest`, `/workspace/config/service-autostart.toml`, and `/workspace/config/service-updates.toml`. Service updates also use `/workspace/config/service-updates-rollback.jsonl` for their audit history. Some of these files appear after you use the corresponding feature, so a missing file in a fresh workspace does not by itself indicate a failed installation.

Bootstrap stores generated credentials in `/workspace/config/secrets.env`. Keep it private when backing up or sharing configuration. The `/workspace/home` directory also contains persistent home-directory state used by parts of the environment.

## Find the evidence for a failed run

Logs live under `/workspace/logs`. Each supervised service writes an output log and an error log. For example, ComfyUI uses `comfy.out.log` and `comfy.err.log`, while ControlPilot uses `controlpilot.out.log` and `controlpilot.err.log`. Supervisor writes `supervisord.log`.

Run `tail -n 120 /workspace/logs/comfy.err.log` inside the container to inspect a recent ComfyUI failure, or open its log from ControlPilot. Substitute the affected service's filename. The [debugging guide](../development/debugging.md) explains how to relate a browser symptom to the process doing the work.

Caches live under `/workspace/cache`, including MediaPilot thumbnails at `/workspace/cache/mediapilot/thumbs`. Temporary runtime locations serve a different purpose. Supervisor uses `/tmp/supervisor.sock` for local process control, and the Jupyter launcher uses `/tmp/jupyter-runtime`. These temporary files are not substitutes for saved project data.

## Understand what comes from the image

The bundled default manifest is `/opt/pilot/config/models.manifest.default`. The active workspace manifest may differ if you have customized it. Read the [manifest guide](../configuration/models-manifest.md) before copying one over the other.

The image carries documentation under `/opt/pilot/docs`, with a workspace copy under `/workspace/docs`. ControlPilot prefers the bundled location when available unless you configure a `DOCS_ROOT` override. Editing the workspace copy alone may therefore leave the displayed documentation unchanged.

The image bundles video workflow assets under `/opt/pilot/bundled/comfy-workflows`. ComfyUI seeds missing workflow files into its persistent user area during startup. Model weights remain separate downloads. Replacing the container replaces image-owned files; preserve your intended customizations through the workspace or a maintained image build.

## Locate the source for a change

In the repository checkout, `apps` contains first-party applications, including Portal, TagPilot, MediaPilot, TrainPilot, and CopilotSidecar. Service launchers and bootstrap code live in `scripts`, defaults live in `config`, and Supervisor definitions live in `supervisor`. The documentation source lives in `docs`, alongside the top-level Compose files and supporting `docker-compose` directory.

Use the [development guide](../development/README.md) to trace a behavior back to those sources. For an existing project, confirm the actual workspace mount before you move files or replace a container, and keep a separate backup of the data and settings you need to recover.
