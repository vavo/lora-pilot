# Changelog

_Last updated: 2026-07-06_

Canonical release history lives in the repository root file: `CHANGELOG`.

ControlPilot exposes the same content at:
- `GET /api/changelog`

## Current Release Entries (from `CHANGELOG`)

| Header in file | High-level highlights |
|---|---|
| `v2.5.4` | July 5 build/runtime refresh, CUDA profile cleanup, ComfyUI Manager/runtime fixes, and code-scanning vulnerabilities reduced to 0 |
| `v2.5.3` | July 3 TagPilot frontend refresh, TensorBoard integration, and JupyterLab/code-server update |
| `v2.5.0` | CUDA 13.0 default profile, shared core Python stack, refreshed bundled tools, and manifest/build updates |
| `v2.4.3` | TagPilot provider compatibility, persisted provider keys, dark-mode/crop fixes, and Docker layer cleanup |
| `v2.4.2` | Blackwell/CUDA baseline refresh, AI Toolkit isolation, and backend TagPilot provider APIs |
| `v2.4.1` | CodeQL hardening, legacy Diffusion Pipe Gradio retirement, and CUDA 12.8 stack preparation |
| `v2.4` | ControlPilot settings/security, embedded app layout cleanup, TrainPilot/Diffusion Pipe improvements, extracted Docker build scripts |
| `v2.3` | Pinned Comfy/Kohya/Diffusion Pipe/build dependency refresh and InvokeAI `6.11.1` baseline |
| `v2.2` | MediaPilot embed under `/mediapilot`, service update endpoints/jobs, TagPilot incremental save endpoint, InvokeAI `INVOKEAI_VERSION` pin update |
| `v2.0` | AI Toolkit integration, ControlPilot redesign/refactor, Copilot sidecar integration |
| `Version 1.99` | ComfyUI-Downloader, TrainPilot progress/log fixes, Docs markdown rendering + changelog in Docs |
| `Version 1.9` | Shutdown scheduler behavior updates, model/Comfy fixes, modular service refactor, Docker Compose improvements |
| `Version 1.8` | InvokeAI update to `6.10.0`, ControlPilot UX/security fixes, shutdown scheduler introduction |

## Notes About Format

- Entries are newest-first.
- Release notes are grouped by release date, with at most one changelog version per day.
- Keep highlights broad and user-facing; detailed commit history belongs in git.
- Version headers currently mix formats (`v2.2` vs `Version 1.99`).
- Recent v2.x entries include calendar dates in the root `CHANGELOG`; older entries may not.

## How to Update

When adding a new release:

1. Add the new section at the top of `CHANGELOG`.
2. Keep entries focused on user-visible behavior changes.
3. Include API path changes explicitly when relevant.

## Related

- [API Reference](../development/api-reference.md)
- [Documentation Home](../README.md)

---

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
