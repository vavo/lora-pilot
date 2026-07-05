# Changelog

Canonical release history lives in the repository root file: `CHANGELOG`.

ControlPilot exposes the same content at:
- `GET /api/changelog`

## Current Release Entries (from `CHANGELOG`)

| Header in file | High-level highlights |
|---|---|
| `v2.5.7` | ComfyUI `v0.27.0`, ComfyUI-Manager `4.2.2`, and explicit core-venv ownership of `torchaudio`, `uv`, `transformers`, and `xformers` |
| `v2.5.6` | TrainPilot now warns before starting Kohya training if Kohya or TensorBoard is stopped, with an option to start the missing service(s) |
| `v2.5.5` | TagPilot dataset-open hotfix for ControlPilot Datasets links on Python 3.11 images; backend load keeps symlink-safe file iteration without unsupported `Path.is_file` arguments |
| `v2.5.4` | Kohya SDXL training compatibility repair for shared core Transformers 5.x images; launcher now checks the `CLIPFeatureExtractor` alias before accepting the installed package |
| `v2.5.3` | TensorBoard integrations completed for TrainPilot + Diffusion Pipe + Kohya + AI Toolkit, with shared `/api/tensorboard/status` discovery and Services page actions |
| `v2.5.1` | TagPilot frontend refresh (latest settings/models), restored embedded theme sync, dataset load/save integration, and path-hardening for dataset/training/model-pull flows |
| `v2.5.0` | CUDA 13.0 default plus CUDA 12.8 legacy profile, shared core GPU stack with fewer venvs, refreshed Comfy/Invoke/Jupyter/code-server/AI Toolkit/Diffusion Pipe pins, Ideogram/Lens/PixelDiT manifest additions |
| `v2.4.3` | TagPilot provider MIME fixes, Gemini/Grok API compatibility updates, persistent provider secrets, JSON provider errors, provider smoke script, dark-mode and preview-crop UX fixes, Dockerfile cache/finalization fixes |
| `v2.4.2` | CUDA 12.8/PyTorch 2.8 Blackwell baseline, refreshed Comfy/Kohya/Invoke/AI Toolkit/Diffusion Pipe pins, server-side TagPilot provider APIs |
| `v2.4.1` | CodeQL hardening, Dpipe Gradio retirement, core CUDA 12.8 stack preparation |
| `v2.4` | ControlPilot settings/security, embedded app layout cleanup, TrainPilot/Diffusion Pipe improvements, extracted Docker build scripts |
| `v2.3` | Pinned Comfy/Kohya/Diffusion Pipe/build dependency refresh and InvokeAI `6.11.1` baseline |
| `v2.2` | MediaPilot embed under `/mediapilot`, service update endpoints/jobs, TagPilot incremental save endpoint, InvokeAI `INVOKEAI_VERSION` pin update |
| `v2.0` | AI Toolkit integration, ControlPilot redesign/refactor, Copilot sidecar integration |
| `Version 1.99` | ComfyUI-Downloader, TrainPilot progress/log fixes, Docs markdown rendering + changelog in Docs |
| `Version 1.9` | Shutdown scheduler behavior updates, model/Comfy fixes, modular service refactor, Docker Compose improvements |
| `Version 1.8` | InvokeAI update to `6.10.0`, ControlPilot UX/security fixes, shutdown scheduler introduction |

## Notes About Format

- Entries are newest-first.
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

_Last updated: 2026-07-05_

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)
