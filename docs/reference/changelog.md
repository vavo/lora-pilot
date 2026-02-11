# Changelog

Canonical release history lives in the repository root file: `CHANGELOG`.

ControlPilot exposes the same content at:
- `GET /api/changelog`

## Current Release Entries (from `CHANGELOG`)

| Header in file | High-level highlights |
|---|---|
| `v2.2` | MediaPilot embed under `/mediapilot`, service update endpoints/jobs, TagPilot incremental save endpoint, InvokeAI `INVOKEAI_VERSION` pin update |
| `v2.0` | AI Toolkit integration, ControlPilot redesign/refactor, Copilot sidecar integration |
| `Version 1.99` | ComfyUI-Downloader, TrainPilot progress/log fixes, Docs markdown rendering + changelog in Docs |
| `Version 1.9` | Shutdown scheduler behavior updates, model/Comfy fixes, modular service refactor, Docker Compose improvements |
| `Version 1.8` | InvokeAI update to `6.10.0`, ControlPilot UX/security fixes, shutdown scheduler introduction |

## Notes About Format

- Entries are newest-first.
- Version headers currently mix formats (`v2.2` vs `Version 1.99`).
- Exact calendar release dates are **Not found in repo**.

## How to Update

When adding a new release:

1. Add the new section at the top of `CHANGELOG`.
2. Keep entries focused on user-visible behavior changes.
3. Include API path changes explicitly when relevant.

## Related

- [API Reference](../development/api-reference.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
