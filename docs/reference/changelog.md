# Changelog

_Last updated: 2026-11-22_

The repository's root [CHANGELOG](../../CHANGELOG) is the canonical release history. You can also read it in ControlPilot Docs or retrieve it from `GET /api/changelog`.

## Unreleased

Create Photo references with RealVisXL V5.0 at 896 × 1152, DPM++ SDE Karras, 30 steps and CFG 7. ControlPilot downloads missing weights when you start. Illustration mode keeps SDXL Base and its existing settings; uploaded references need neither T2I checkpoint. Qwen Image Edit variations still use the approved reference.

Review images using the arrows beside the comparison images or the left/right keyboard keys. **Keep image** saves your decision without a confirmation popup, including when checks are pending or flag a concern. Specific warnings remain visible. The image-choice API no longer requires `confirm_unchecked`.

The dataset builder distinguishes people from non-human characters and starts with three trial variations before the remaining batch. Save any kept subset to TagPilot, even fewer images than requested. TagPilot remains the caption/tag editor, with local Qwen3-VL, browser-draft recovery and unfinished-batch resume. Save your captions before continuing to Guided training. GPU generation and vision-model inference still need pod acceptance testing.

Guided training adds Anima, Lumina-Image 2.0 and HunyuanImage 2.1 with model downloads, Kohya recipes and saved queue settings. Each family keeps the same three quality profiles. Compare the original model with one checkpoint or all saved checkpoints in training order. Anima and HunyuanImage comparisons prepare ComfyUI-compatible copies without changing the originals. GPU validation remains outstanding.

MCP setup adds owner-only connection diagnostics, Codex configuration instructions and a public connection test. Check the configured address, proxy and runtime before connecting an agent. See the [MCP setup guide](../configuration/mcp.md).

## Current release: v2.6

ControlPilot adds scoped MCP connections, a redesigned Dashboard, Settings and Services, and an integrated Caption images editor. Guided training now includes FLUX.1 dev, a persistent queue, checkpoint recovery, searchable history and comparison grids. Dataset quality reports, the orange robot starter guide and experiment exports support the full training workflow.

RunPod integration moves to REST v2 with optional storage and spending information. Storage gains visual usage and reviewed cleanup. VS Code becomes an optional persistent install, while ComfyUI gains bundled GGUF and VideoHelperSuite extensions. Reliability fixes cover startup, access protection, training, model loading and screen navigation.

See the root [CHANGELOG](../../CHANGELOG) for the complete release summary, the [MCP setup guide](../configuration/mcp.md) for execution limits, and the [build guide](../development/building.md) for image publication. Verify an image's revision before deploying it.

## Published release notes

Read the [v2.6 release notes](../releases/v2.6.md) for ControlPilot, guided training, MCP access and upgrade details.

Read the [v2.5.8 release notes](../releases/v2.5.8.md) for the Models catalog, workflow installation review, backend extraction, and runtime fixes. That GitHub release compares against [v2.5.4](../releases/v2.5.4.md) and includes the intervening v2.5.5 through v2.5.7 changelog entries, which did not have separate GitHub releases. Earlier entries remain in the root history.

## Maintain the history

Add user-visible changes to the newest Unreleased section. Keep them there until a version is assigned, and describe what a user can do or what changed in an existing flow. Mention API additions when they affect integrations. Detailed implementation history belongs in Git.

When publishing a release, give its section a version and date, add the release notes under `docs/releases/`, and link them here. Keep Docker publication and GPU validation separate from GitHub release publication so readers can tell what they can deploy and what has been tested.

See the [API reference](../development/api-reference.md) for integration details or return to the [documentation home](../README.md).
