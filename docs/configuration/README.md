# Configuration

_Last updated: 2026-09-10_

You may begin with the default setup and later want a different arrangement: models on a separate disk, a service on another port, or fewer applications starting with the container. LoRA Pilot gives you several places to make those changes. Knowing which one owns a setting helps you keep the next startup predictable.

Separate the container's deployment settings from the preferences you save through an application. A port mapping belongs to the deployment. A model catalog override belongs to the workspace. A service's current running state is different from its saved autostart preference.

## Choose the deployment shape

The [Docker Compose guide](docker-compose.md) explains the standard, development, and CPU configurations. The standard file maps a host workspace into `/workspace` and exposes the service ports. The development file adds source mounts for editing. The CPU file omits the NVIDIA runtime and exposes a smaller set of interfaces by default.

For Compose, create `.env` from `.env.example` if you do not have one. Read the variables referenced by the Compose file you are using before adding values. Compose uses `.env` for substitution; an entry reaches the application only if the configuration passes it into the container. The [environment-variable reference](environment-variables.md) connects the available settings to their purpose.

Use [custom setup](custom-setup.md) for image overrides, storage mounts, and port changes. After changing the selected image, environment, or mounts, apply the deployment configuration with Compose and verify the resulting service state. Restarting one application inside an existing container does not change that container's mounts or published ports.

## Save service preferences at the right level

Open **Services** in ControlPilot to inspect the tools you use. Starting a service changes its current state; its autostart setting controls whether it starts during boot. LoRA Pilot saves autostart preferences in `/workspace/config/service-autostart.toml` by default and applies them to the Supervisor configuration.

The [Supervisor guide](supervisor.md) explains the managed processes, log locations, and service identifiers. Use those identifiers for terminal operations so you target the intended process. For example, the ComfyUI service is named `comfy`, while the InvokeAI service is `invoke`.

Service update preferences have a separate file at `/workspace/config/service-updates.toml`. Keep a record of changes you make to a working environment and test the affected workflow afterward. Opening an updated interface confirms less than completing a familiar generation or training task.

## Adapt the catalog without losing track of its source

The model catalog describes named downloads and their destinations. Its default runtime location is `/workspace/config/models.manifest`; the image carries a default copy under `/opt/pilot/config/models.manifest.default`. The [manifest guide](models-manifest.md) explains the fields, while [model management](../user-guide/model-management.md) covers the browser and terminal workflows.

Before editing an existing catalog, save a copy and use `models where` inside the container to identify the active path. Bootstrap can refresh a previously seeded catalog during an image upgrade. Its tracking file distinguishes later user edits, but a workspace without that tracking file receives a one-time refresh. Keep your own copy of a customized manifest before upgrading an older workspace.

## Configure access for the interface you expose

Use ControlPilot's settings for its login configuration. If you want ComfyUI to use the protected entry point, follow [ComfyUI access protection](comfy-access.md). That guide explains the browser session and the separate Comfy-only API token.

Treat the other exposed services according to their own access configuration. A password on ControlPilot does not establish protection for an independent port. Keep `/workspace/config/secrets.env` private and inspect individual settings without copying the whole file into a support request.

## Distinguish build choices from runtime choices

The image build determines which applications and dependency versions are installed. Those choices come from `Dockerfile`, `Makefile`, and `build.env.example`; the [build guide](../development/building.md) explains how to change them. Runtime settings come from the deployment environment, persisted configuration, and the service launchers under `scripts`.

After a change, open ControlPilot, inspect the affected service, and repeat the action that prompted the change. Use [debugging](../development/debugging.md) if it fails, or return to the [user guide](../user-guide/README.md) to continue your project.
