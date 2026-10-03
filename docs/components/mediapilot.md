# MediaPilot

_Last updated: 2026-07-05_

MediaPilot is the built-in gallery and curation layer for generated images in LoRA Pilot. It is embedded into ControlPilot and optimized for large output directories.

##  Overview

MediaPilot gives you:
- Fast gallery browsing with generated WebP thumbnails
- Search over extracted metadata (prompt, LoRA, sampler, scheduler, steps, CFG)
- Image curation tools: like, tag/move, delete
- Bulk actions: ZIP download and ComfyUI upscale queue
- Optional password gate for shared environments

##  Access

- **ControlPilot tab**: `MediaPilot`
- **Direct route**: `http://localhost:7878/mediapilot/`
- **Status check**: `GET /api/mediapilot/status`

In LoRA Pilot, MediaPilot is mounted inside ControlPilot (same host/port), not exposed as a separate default port.

##  Data Sources and Paths

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

##  Search and Filtering

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

The paths below are relative to MediaPilot. In LoRA Pilot, prefix them with `/mediapilot` on the ControlPilot origin, for example `http://localhost:7878/mediapilot/images`. Standalone MediaPilot uses the unprefixed paths.

| Endpoint | Method | Description |
|---|---|---|
| `/healthz` | `GET` | Health check |
| `/auth/status` | `GET` | Auth enabled/authenticated state |
| `/auth/login` | `POST` | Login when password auth enabled |
| `/auth/logout` | `POST` | Invalidate MediaPilot session and clear cookie |
| `/folders` | `GET` | List folders |
| `/folders` | `POST` | Create folder |
| `/images` | `GET` | Paginated image list |
| `/like/{filename}` | `POST` | Like image |
| `/unlike/{filename}` | `POST` | Unlike image |
| `/tag` | `POST` | Move image between folders |
| `/image/{filename}` | `DELETE` | Delete image from root |
| `/image/{folder:path}/{filename}` | `DELETE` | Delete image from folder |
| `/download/bulk` | `POST` | Download selected files as ZIP |
| `/upscale/bulk` | `POST` | Queue selected files to ComfyUI |

### API request and response contracts

Current limitation: with a separate MediaPilot password enabled, the embedded app checks prefixed request paths against unprefixed public-path rules. Local mounted-app checks return 401 for `/mediapilot/auth/login`, `/mediapilot/auth/status` and `/mediapilot/healthz` before their handlers run. Use ControlPilot password protection with the separate MediaPilot password unset for the embedded gallery until this is fixed. Standalone `/auth/login` works.

Send JSON bodies except for `/tag`, which takes query parameters. When embedded, ControlPilot enforces its own password gate before MediaPilot handles requests. A separate `MEDIAPILOT_ACCESS_PASSWORD`, if configured, adds MediaPilot's cookie requirement. A MediaPilot login does not grant access to ControlPilot APIs. See [ControlPilot authentication](../development/api-reference.md#authentication-and-settings).

| Route | Input | Success response |
|---|---|---|
| `GET /healthz` | None | `{"ok":true}` |
| `GET /auth/status` | Cookie if present | `enabled`, `authenticated` |
| `POST /auth/login` | `{"password":"..."}` | `ok`, `enabled`; sets `mediapilot_auth` by default; wrong password returns 401 |
| `POST /auth/logout` | Session cookie; no body | `{"ok":true}`; invalidates this MediaPilot session |
| `GET /folders` | None | `{"folders":["..."]}` |
| `POST /folders` | `{"name":"selected"}` | `{"created":true,"folder":"selected"}` |
| `GET /images` | Query `page=1`, `limit=50`, `folder=_root`, `sort=NEWEST`, `search=` | `page`, `pages`, `images`; use positive page/limit values |
| `POST /like/{filename}` / `POST /unlike/{filename}` | No body | `{"ok":true}` |
| `POST /tag` | Required query `filename`, `old_folder`, `new_folder` | `{"moved":true}`; physically moves the file; missing source returns 404, occupied destination 409 |
| `DELETE /image/{filename}` / `DELETE /image/{folder:path}/{filename}` | Path parameters | `{"deleted":true}`; removes image, thumbnail and metadata; also succeeds for an absent file |
| `POST /download/bulk` | `{"folder":"_root","filenames":["example.png"]}` | ZIP attachment; skips missing files, returns 404 if none exist |
| `POST /upscale/bulk` | Same JSON shape as download | `ok`, `queued`, `submitted`, `failed`; submits ComfyUI jobs without waiting for generation |

`_root` selects the configured output root, `InvokeAI` selects the separate InvokeAI image directory, and other folder values are relative paths beneath the output root. Image listing reads one folder at a time. Sort accepts `NEWEST`, `OLDEST`, or `ALPHABETICALLY` (case-insensitive); unrecognized values use newest first. Search uses the metadata syntax described above. URL-encode filenames and folder segments.

Image entries contain `filename`, `thumb_url`, `full_url`, `liked`, `tagged`, `created_at` (Unix seconds), and nullable generation metadata: `prompt`, `lora_name`, `lora_strength`, `lora_name_2`, `lora_strength_2`, `steps`, `cfg`, `sampler`, `scheduler`. Resolve the returned `./output`, `./thumbs`, or `./invoke` URLs relative to `/mediapilot/` when embedded. Likes use filenames as database keys, so equal filenames in different folders share like state.

Bulk calls require a nonempty filename list. The default limits are 500 download selections and 50 upscale selections, configurable through the environment variables above. Duplicate names are processed once; the selection limit applies before deduplication. Upscale `submitted` entries contain `filename`, `prompt_id` and `comfy_input_image`; `failed` entries contain `filename` and `error`. Partial success returns HTTP 200; if all attempted submissions fail, HTTP 502 contains `detail.submitted` and `detail.failed`. Inspect both lists before retrying to avoid duplicate jobs.

MediaPilot serves files through `/output/{path}`, `/thumbs/{path}` and `/invoke/{path}`, and its frontend through `/` and `/static/{path}`. Its own schema and interactive docs live at `/openapi.json`, `/docs`, and `/redoc`; prefix those with `/mediapilot` in ControlPilot. These surfaces follow the applicable authentication gates. MediaPilot sessions live in memory and disappear on restart.

Example move within the gallery, using a cookie jar with the required login cookies:

```bash
curl --fail-with-body -sS -b "$COOKIE_JAR" -X POST \
  'http://localhost:7878/mediapilot/tag?filename=example.png&old_folder=_root&new_folder=selected'
```

## 🧪 Thumbnail Pre-generation

For large libraries, you can prebuild thumbnails:

```bash
cd /workspace/apps/MediaPilot
/opt/venvs/core/bin/python pregenerate_thumbs.py
```

##  Troubleshooting

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

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)


