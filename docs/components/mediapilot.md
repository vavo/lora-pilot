# MediaPilot

MediaPilot is the built-in gallery and curation layer for generated images in LoRA Pilot. It is embedded into ControlPilot and optimized for large output directories.

## 🎯 Overview

MediaPilot gives you:
- Fast gallery browsing with generated WebP thumbnails
- Search over extracted metadata (prompt, LoRA, sampler, scheduler, steps, CFG)
- Image curation tools: like, tag/move, delete
- Bulk actions: ZIP download and ComfyUI upscale queue
- Optional password gate for shared environments

## 🚀 Access

- **ControlPilot tab**: `MediaPilot`
- **Direct route**: `http://localhost:7878/mediapilot/`
- **Status check**: `GET /api/mediapilot/status`

In LoRA Pilot, MediaPilot is mounted inside ControlPilot (same host/port), not exposed as a separate default port.

## 📂 Data Sources and Paths

Default LoRA Pilot bootstrap values:
- `MEDIAPILOT_OUTPUT_DIR=/workspace/outputs/comfy`
- `MEDIAPILOT_INVOKEAI_DIR=/workspace/outputs/invoke`
- `MEDIAPILOT_THUMBS_DIR=/workspace/cache/mediapilot/thumbs`
- `MEDIAPILOT_DB_FILE=/workspace/config/mediapilot/data.db`
- `MEDIAPILOT_COMFY_API_URL=http://127.0.0.1:5555`

Config file location:
- `/workspace/apps/MediaPilot/.env`

## ⚙️ Environment Variables

Key variables:

| Variable | Purpose | Default |
|---|---|---|
| `MEDIAPILOT_OUTPUT_DIR` | Main image root (Comfy outputs) | `./data/output` |
| `MEDIAPILOT_INVOKEAI_DIR` | InvokeAI image root | `./data/invokeai` |
| `MEDIAPILOT_THUMBS_DIR` | Thumbnail cache root | `./data/thumbs` |
| `MEDIAPILOT_DB_FILE` | SQLite likes/tags DB file | `./data/data.db` |
| `MEDIAPILOT_MAX_BULK_DOWNLOAD_FILES` | Bulk ZIP file count cap | `500` |
| `MEDIAPILOT_MAX_BULK_UPSCALE_FILES` | Bulk upscale file count cap | `50` |
| `MEDIAPILOT_COMFY_API_URL` | ComfyUI API base URL | `http://127.0.0.1:5555` |
| `MEDIAPILOT_UPSCALE_WORKFLOW_FILE` | Workflow template JSON for upscaling | `./comfy_upscale_workflow.json` |
| `MEDIAPILOT_ACCESS_PASSWORD` | Enables auth when non-empty | empty |
| `MEDIAPILOT_ALLOW_ORIGINS` | CORS origins (comma-separated) | `*` |

## 🔍 Search and Filtering

Search supports free text and field filters:

```text
portrait cinematic
lora:my_style
sampler:uni_pc
scheduler:sgm_uniform
steps:24
steps>=20
cfg:4.5
cfg<7
```

Metadata is extracted from image metadata and ComfyUI prompt JSON where available.

## 🧰 Common Workflows

### 1. Curate Comfy/Invoke outputs
1. Open `MediaPilot` in ControlPilot.
2. Choose folder (`Untagged`, `InvokeAI`, or custom folders).
3. Use search to isolate candidates.
4. Like, tag/move, or delete in bulk.

### 2. Download selected images as ZIP
1. Select images in gallery.
2. Use bulk download action.
3. MediaPilot generates a temporary archive and streams it.

### 3. Send selected images to ComfyUI upscale queue
1. Configure `MEDIAPILOT_UPSCALE_WORKFLOW_FILE`.
2. Use placeholder `__INPUT_IMAGE__` for input image and `__OUTPUT_PREFIX__` for output prefix.
3. Select images and run bulk upscale.

## ⌨️ Keyboard Shortcuts

### Gallery view

| Shortcut | Action |
|---|---|
| `Delete` / `Backspace` | Delete selected images |
| `Space` (`Spacebar` legacy) | Like/unlike selected images |
| `Enter` | Open tag menu for selected images |

Notes:
- Gallery shortcuts work only when at least one image is selected.
- Shortcuts are ignored while typing in inputs/textareas/contenteditable fields.

### Modal view

| Shortcut | Action |
|---|---|
| `Escape` | Close modal |
| `Delete` / `Backspace` | Delete current image |
| `ArrowLeft` / `ArrowRight` | Previous / next image |
| `ArrowUp` / `ArrowDown` | Move up / down by grid row |
| `Space` | Like/unlike current image |
| `Enter` | Open tag dropdown |
| `M` | Toggle magnifier at cursor |

## 🔌 API Reference (Core)

| Endpoint | Method | Description |
|---|---|---|
| `/healthz` | `GET` | Health check |
| `/auth/status` | `GET` | Auth enabled/authenticated state |
| `/auth/login` | `POST` | Login when password auth enabled |
| `/folders` | `GET` | List folders |
| `/folders` | `POST` | Create folder |
| `/images` | `GET` | Paginated image list |
| `/like/{filename}` | `POST` | Like image |
| `/unlike/{filename}` | `POST` | Unlike image |
| `/tag` | `POST` | Move image between folders |
| `/image/{filename}` | `DELETE` | Delete image from root |
| `/image/{folder}/{filename}` | `DELETE` | Delete image from folder |
| `/download/bulk` | `POST` | Download selected files as ZIP |
| `/upscale/bulk` | `POST` | Queue selected files to ComfyUI |

## 🧪 Thumbnail Pre-generation

For large libraries, you can prebuild thumbnails:

```bash
cd /workspace/apps/MediaPilot
/opt/venvs/core/bin/python pregenerate_thumbs.py
```

## 🛠️ Troubleshooting

### MediaPilot section is blank in ControlPilot
- Check status API:
```bash
curl -s http://localhost:7878/api/mediapilot/status
```
- If `available=false`, confirm app files exist at `/workspace/apps/MediaPilot` (or bundled `/opt/pilot/apps/MediaPilot`).

### Gallery loads but images are missing
- Verify `MEDIAPILOT_OUTPUT_DIR` and `MEDIAPILOT_INVOKEAI_DIR` in `/workspace/apps/MediaPilot/.env`.
- Confirm files exist and are readable.

### Upscale action fails
- Confirm `MEDIAPILOT_COMFY_API_URL` points to active ComfyUI.
- Validate workflow JSON at `MEDIAPILOT_UPSCALE_WORKFLOW_FILE`.
- Ensure workflow has either placeholders or a `LoadImage` node.

### Auth issues after enabling password
- Set `MEDIAPILOT_ACCESS_PASSWORD` in `.env`.
- If running behind HTTPS, set `MEDIAPILOT_AUTH_COOKIE_SECURE=true`.

## Related

- [ControlPilot](../user-guide/control-pilot.md)
- [ComfyUI](comfyui.md)
- [Model Management](../user-guide/model-management.md)
- [Section Index](README.md)
- [Documentation Home](../README.md)

---

_Last updated: 2026-02-11_
