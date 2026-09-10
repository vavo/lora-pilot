# Development

_Last updated: 2026-09-10_

A change in LoRA Pilot can improve an entire creative session. A clearer download error helps someone get a model into ComfyUI. A reliable dataset save protects the work they will train on. A corrected startup path lets them return to the same workspace tomorrow. The development work connects those moments across tools with different runtimes and requirements.

The repository contains the container build, service launchers, and first-party interfaces that connect those tools. You can contribute to a focused part of that system without rewriting the training or generation engine behind it.

## Find the boundary your change belongs to

Begin with [architecture](architecture.md) to understand the relationship between the image and the workspace. Bundled code lives under `/opt/pilot` in the container. User data and settings live under `/workspace`. A fix that works in a source checkout must also work with that packaged layout and with an existing workspace from an earlier session.

For a ControlPilot interaction, start in `apps/Portal`. Its FastAPI backend works with the JavaScript views under `static`, and feature services hold supporting logic. Service launches belong in `scripts`, with process definitions under `supervisor`. Image installation and dependency choices start in `Dockerfile` and `scripts/build`.

Read the [API reference](api-reference.md) when connecting a user action to a backend route. Use [debugging](debugging.md) when you have a failure to reproduce. Both help you narrow the change to the boundary that owns the behavior.

## Build around the existing environments

The [build guide](building.md) covers image construction and overrides. The [CUDA compatibility guide](cuda-compatibility.md) explains the separate service environments and the checks needed on GPU hardware. Model files can share storage while the applications that use them retain different Python dependencies.

If you change a dependency pin, inspect its matching values in `Dockerfile`, `Makefile`, and `build.env.example`. The repository tests enforce that relationship. If you change model catalog entries, keep `config/models.manifest` and `config/models.manifest.default` identical so source and packaged defaults describe the same catalog.

For interface or launcher work, the development Compose file mounts selected source paths into a running container. You can use that to shorten the edit-and-test loop, then verify behavior in the packaged layout before treating the work as complete.

## Verify the behavior a reader or creator will use

Run `make build-check` for the build configuration checks and `python3 -m unittest discover -s tests` for the Python regression suite from the repository root. Use a Python environment with the dependencies needed by the tests. The repository does not provide a root `requirements-dev.txt` or a pre-commit setup, so do not assume those installation steps are available.

Choose runtime validation according to the change. A documentation edit needs accurate instructions and working links. A Models page fix needs the affected responses and a populated browser view. A GPU dependency change needs evidence from the installed environment on suitable hardware. Record the boundary you tested so a passing unit suite does not imply a generation run you have not performed.

Use [contributing](contributing.md) for the contribution process, while treating the current build files and test entry points here as the authority for executable commands. Keep a change focused enough that another reader can connect the original problem, the correction, and the result you verified. Return to [configuration](../configuration/README.md) for runtime settings or the [documentation home](../README.md) to follow the user-facing workflow your change supports.
