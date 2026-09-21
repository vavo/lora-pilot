# Changelog

_Last updated: 2026-09-21_

The repository's root [CHANGELOG](../../CHANGELOG) is the canonical release history. You can also read it in ControlPilot Docs or retrieve it from `GET /api/changelog`.

## Current unreleased work

The current entry adds persistent training history, a serial queue with GPU conflict checks, guided FLUX.1 dev training alongside SDXL, and a paired LoRA comparison in ComfyUI. You can start from the Dashboard, inspect dataset previews and caption coverage, queue a run, then copy its saved LoRA files into the shared library without removing the originals. The grouped sidebar retains light and dark controls, and Models opens Connections without losing the selected catalog family.

The September 21 additions bring checkpoint downloads, searchable and paginated training history, actionable failure messages, and elapsed time with cautious estimates. The new Storage page shows category usage and offers explicit reviewed cleanup of private files from finished guided runs, with workload and file-change checks. Original datasets, shared models, and run history stay protected.

This section also records the Settings redesign, the Models HTTP 500 fix, and repaired documentation images. These are source changes awaiting a release. A changelog entry does not establish that a Docker image contains the change or that training has passed on a target GPU.

## Published release notes

Read the [v2.5.8 release notes](../releases/v2.5.8.md) for the Models catalog, workflow installation review, backend extraction, and runtime fixes. That GitHub release compares against [v2.5.4](../releases/v2.5.4.md) and includes the intervening v2.5.5 through v2.5.7 changelog entries, which did not have separate GitHub releases. Earlier entries remain in the root history.

## Maintain the history

Add user-visible changes to the newest Unreleased section. Keep them there until a version is assigned, and describe what a user can do or what changed in an existing flow. Mention API additions when they affect integrations. Detailed implementation history belongs in Git.

When publishing a release, give its section a version and date, add the release notes under `docs/releases/`, and link them here. Keep Docker publication and GPU validation separate from GitHub release publication so readers can tell what they can deploy and what has been tested.

See the [API reference](../development/api-reference.md) for integration details or return to the [documentation home](../README.md).
