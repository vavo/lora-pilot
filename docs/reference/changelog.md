# Changelog

_Last updated: 2026-10-05_

The repository's root [CHANGELOG](../../CHANGELOG) is the canonical release history. You can also read it in ControlPilot Docs or retrieve it from `GET /api/changelog`.

## Current unreleased work

VS Code Server is now an [optional install](../components/code-server.md) from **ControlPilot → Services**. The default Docker image no longer bundles the editor. Choose **Install VS Code**, wait for verification to finish, then **Start service**. The executable persists in the workspace, existing editor data is preserved, and fresh workspaces leave autostart off. Port 8443 remains reserved so installation does not require recreating a standard Compose container.

The current MCP source adds an optional connection between ControlPilot and compatible assistant clients. You choose the datasets, runs and permissions each connection receives, then review proposed operations in Settings. Tokens expire and can be rotated or revoked. Write operations remain behind deployment verification gates. The [MCP guide](../configuration/mcp.md) explains setup, supported clients and approval behavior; the [validation record](../development/mcp-validation.md) separates completed checks from the remaining GPU, volume and public-proxy work.

Services now has a selectable directory, status filters and a detail panel for controls, startup preferences, versions and recent logs. Running browser tools have a direct Open shortcut. A shared service registry supplies names, configured ports and capabilities, with checks against Supervisor's programs, launchers and log paths. Copilot and AI Toolkit honor their configured ports. See [ControlPilot](../user-guide/control-pilot.md#manage-services-and-model-files) for the interface and [Supervisor](../configuration/supervisor.md#keeping-service-definitions-consistent) for the configuration contract.

The October 3 source changes add read-only dataset quality review, the optional orange robot first-LoRA guide, editable GPU suggestions informed by matching local runs, and previewed experiment ZIP exports. The guide uses original video assets as training inputs. No published cross-GPU benchmark or trained demo result is implied. See [TrainPilot](../components/trainpilot.md) for the workflow and validation limits.

The RunPod integration now uses REST v2 for shutdown, reads allocated workspace storage, and separates hourly cost, estimated session spending and recorded daily pod charges. Credentials remain on the backend. Volume and billing details are optional when permission is missing. See [RunPod integration](../configuration/runpod.md) for configuration and the limits of each figure.

Training and ComfyUI can now use the GPU concurrently. GPU occupancy and unavailable telemetry are advisory during training preflight, while managed training jobs remain serialized. Try My LoRA comparisons can also run alongside training. Storage cleanup retains its workload protection.

The current entry adds persistent training history, a serial queue with managed trainer conflict checks, guided FLUX.1 dev training alongside SDXL, and a checkpoint comparison grid in ComfyUI. You can start from the Dashboard, inspect dataset previews and caption coverage, queue a run, then move or copy its saved LoRA files into the shared library. Moved checkpoints remain available for downloads and comparisons. The comparison begins with the base model without LoRA, followed by every saved checkpoint in training order. The ComfyUI handoff confirms that the prepared workflow loaded and keeps a manual download available. The grouped sidebar retains light and dark controls, and Models opens Connections without losing the selected catalog family.

The September 21 additions bring checkpoint downloads, searchable and paginated training history, actionable failure messages, and elapsed time with cautious estimates. The new Storage page shows category usage and offers explicit reviewed cleanup of private files from finished guided runs, with workload and file-change checks. Original datasets, shared models, and run history stay protected.

This section also records the Settings redesign, the Models HTTP 500 fix, and repaired documentation images. These are source changes awaiting a release. A changelog entry does not establish that a Docker image contains the change or that training has passed on a target GPU.

## Implementation and delivery status

The October 6 ComfyUI startup fix removes a Python import collision with ControlPilot's `services/comfy.py`. It preserves access protection and upgrades an existing authentication hook without installing it twice. All 401 Python tests passed, including 27 ComfyUI tests. The regression test executes the launcher setup against ComfyUI's namespace-package layout with protection both on and off; this is separate from live GPU validation.

The optional-editor implementation at `99b07d3` passed 399 Python tests and 17 Services/lifecycle JavaScript tests, Docker build checks for cu130 and cu128, desktop/mobile installation and retry checks, and an isolated Linux amd64 installation and password-gated startup using the real release archive. Two broader Settings JavaScript failures also occurred on the unchanged parent commit. These checks do not certify GPU training. Development images are published through the [GitHub Actions workflow](../development/building.md#publish-a-development-image-with-github-actions); verify the successful run and image revision before deploying a mutable tag.

The October 3 service registry refactor at `2b310e1` passed 328 Python tests and 53 JavaScript tests. Local browser checks covered custom-port links, simulated service stop/start, desktop light mode and mobile dark mode. Those checks did not launch the real container services. MCP has a separate [validation record](../development/mcp-validation.md); this documentation update does not add an image publication or deployment result.

The September 21 implementation through `e70a86b` passed 229 Python tests and 8 frontend tests. Local browser checks covered checkpoint downloads, history filters, progress estimates, reviewed cleanup, mobile layout, and both themes. Cleanup checks used disposable files. The local Docker build check could not reach a running daemon; that task did not publish a new image or validate a training run on a live GPU.

The documentation home now links to a [product roadmap](../product/roadmap.md) and [ideas document](../product/ideas.md). The roadmap records implemented behavior and proposed priorities; ideas remain exploratory. Neither document promises that an installed image contains a source change.

## Published release notes

Read the [v2.5.8 release notes](../releases/v2.5.8.md) for the Models catalog, workflow installation review, backend extraction, and runtime fixes. That GitHub release compares against [v2.5.4](../releases/v2.5.4.md) and includes the intervening v2.5.5 through v2.5.7 changelog entries, which did not have separate GitHub releases. Earlier entries remain in the root history.

## Maintain the history

Add user-visible changes to the newest Unreleased section. Keep them there until a version is assigned, and describe what a user can do or what changed in an existing flow. Mention API additions when they affect integrations. Detailed implementation history belongs in Git.

When publishing a release, give its section a version and date, add the release notes under `docs/releases/`, and link them here. Keep Docker publication and GPU validation separate from GitHub release publication so readers can tell what they can deploy and what has been tested.

See the [API reference](../development/api-reference.md) for integration details or return to the [documentation home](../README.md).
