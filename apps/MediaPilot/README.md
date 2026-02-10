# MediaPilot (Your AI output folder. Finally usable.)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-vavo-5F7FFF?style=for-the-badge&logo=buy-me-a-coffee&logoColor=white)](https://www.buymeacoffee.com/vavo) [![GitHub Sponsors](https://img.shields.io/github/sponsors/vavo?style=for-the-badge&logo=github)](https://github.com/sponsors/vavo)
![MediaPilot logo](static/logo-mediapilot.svg)

You generated 3,000 images. You need 12. You can find... maybe 2.

MediaPilot is the control layer for image-generation workflows: a fast local web app to browse, search, tag, and batch-process outputs without folder archaeology at 2 AM.

Built for ComfyUI, InvokeAI, and any folder-based pipeline where speed matters more than ceremony.

## Why MediaPilot

- Instant WebP thumbnails for huge output folders
- Smart metadata search across prompt, LoRA, sampler, scheduler, steps, and CFG
- Bulk actions that actually save time: like, tag, delete, ZIP download, upscale queue
- Optional password gate (server-side cookie session)
- FastAPI backend + vanilla JS frontend for easy deployment and low overhead

## Quick Start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create config:

```bash
cp .env.example .env
```

3. Edit `.env` paths/password.

4. Start server:

```bash
uvicorn main:app --host 0.0.0.0 --port 6666 --reload
```

5. Optional: pre-generate thumbnails:

```bash
python pregenerate_thumbs.py
```

## Keyboard Shortcuts

### Gallery View

- `Delete` / `Backspace`: delete selected images
- `Space` (and legacy `Spacebar`): like/unlike selected images
- `Enter`: open tag menu for selected images

Notes:
- Shortcuts are active only when at least one image is selected.
- Shortcuts are ignored while typing in inputs/textareas/contenteditable fields.

### Modal View

- `Escape`: close modal
- `Delete` / `Backspace`: delete current image
- `ArrowLeft` / `ArrowRight`: previous / next image
- `ArrowUp` / `ArrowDown`: move up / down by grid row
- `Space`: like/unlike current image
- `Enter`: open tag dropdown
- `M`: toggle magnifier at cursor

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `MEDIAPILOT_OUTPUT_DIR` | `./data/output` | Main image directory |
| `MEDIAPILOT_THUMBS_DIR` | `./data/thumbs` | Thumbnail storage |
| `MEDIAPILOT_INVOKEAI_DIR` | `./data/invokeai` | Optional InvokeAI image directory |
| `MEDIAPILOT_DB_FILE` | `./data/data.db` | SQLite file path |
| `MEDIAPILOT_MAX_BULK_DOWNLOAD_FILES` | `500` | Max files per bulk ZIP download |
| `MEDIAPILOT_MAX_BULK_UPSCALE_FILES` | `50` | Max files per bulk upscale request |
| `MEDIAPILOT_COMFY_API_URL` | `http://127.0.0.1:8188` | ComfyUI API base URL |
| `MEDIAPILOT_UPSCALE_WORKFLOW_FILE` | `./comfy_upscale_workflow.json` | Workflow JSON used for batch upscale |
| `MEDIAPILOT_UPSCALE_INPUT_PLACEHOLDER` | `__INPUT_IMAGE__` | Placeholder replaced with uploaded input image |
| `MEDIAPILOT_UPSCALE_OUTPUT_PLACEHOLDER` | `__OUTPUT_PREFIX__` | Placeholder replaced with output prefix |
| `MEDIAPILOT_UPSCALE_OUTPUT_PREFIX` | `mediapilot-upscaled` | Base prefix for saved upscaled images |
| `MEDIAPILOT_COMFY_REQUEST_TIMEOUT` | `60` | Timeout (seconds) for Comfy API calls |
| `MEDIAPILOT_ACCESS_PASSWORD` | empty | Enables auth when set |
| `MEDIAPILOT_AUTH_COOKIE_NAME` | `mediapilot_auth` | Session cookie name |
| `MEDIAPILOT_AUTH_COOKIE_SECURE` | `false` | Set `true` behind HTTPS |
| `MEDIAPILOT_ALLOW_ORIGINS` | `*` | Comma-separated CORS origins |

## API (core)

| Endpoint | Method | Purpose |
|---|---|---|
| `/auth/status` | `GET` | Auth enabled/authenticated flags |
| `/auth/login` | `POST` | Login with password |
| `/images` | `GET` | Paginated image listing |
| `/folders` | `GET` | Folder/tag list |
| `/folders` | `POST` | Create folder/tag |
| `/like/{filename}` | `POST` | Like image |
| `/unlike/{filename}` | `POST` | Unlike image |
| `/image/{filename}` | `DELETE` | Delete root image |
| `/image/{folder}/{filename}` | `DELETE` | Delete image in folder |
| `/download/bulk` | `POST` | Download selected images as ZIP |
| `/images?search=...` | `GET` | Smart metadata search in image listing |
| `/upscale/bulk` | `POST` | Queue selected images for ComfyUI upscale |
| `/tag` | `POST` | Move/tag image |

## Search Query Syntax

Examples:

- `portrait cinematic` (free text across prompt + LoRA + sampler + scheduler)
- `lora:pzm` (LoRA name contains value)
- `sampler:uni_pc`
- `scheduler:sgm_uniform`
- `steps:24` or `steps>=20`
- `cfg:4.5` or `cfg<7`

## Comfy Upscale Workflow

To use batch upscale:

1. Start from `comfy_upscale_workflow.example.json` or export your own Comfy workflow in API JSON format.
2. Save it to `MEDIAPILOT_UPSCALE_WORKFLOW_FILE` (default: `./comfy_upscale_workflow.json`).
3. In the workflow JSON, use:
   - `__INPUT_IMAGE__` where the input image filename should go (usually `LoadImage.inputs.image`)
   - `__OUTPUT_PREFIX__` where output prefix should go (usually `SaveImage.inputs.filename_prefix`)
4. Use the new gallery bulk action button (upscale icon) after selecting images.

## Notes

- `.env` and runtime data are ignored by git.
- If you expose this publicly, set `MEDIAPILOT_ACCESS_PASSWORD` and restrict `MEDIAPILOT_ALLOW_ORIGINS`.
