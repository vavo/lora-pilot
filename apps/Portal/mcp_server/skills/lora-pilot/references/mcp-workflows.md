# MCP workflows

Contract checked against LoRA Pilot source on 2026-11-22. Discover the deployed schemas before use; this reference does not grant capabilities.

## Dataset review

Call `datasets_list` and follow `next_cursor` until it is null. Call `dataset_review` with a returned `dataset_id`, not a folder name. List and review only the granted datasets. If the expected dataset is absent, ask the owner to add it through Settings → MCP → Connections → Edit grants.

Review returns `images`, `size_bytes`, `complete` and `counts`: `small` (a side below 512 pixels), `duplicate` (identical image bytes), `empty_caption`, `missing_caption` and `orphan_caption`. Counts overlap. Do not subtract their sum from image count to invent a usable-image total. Byte-identical detection is not perceptual similarity; orphan captions and missing captions are different problems. The bounded scan can reject oversized datasets instead of returning a partial review.

Prioritize unreadable files or a rejected scan, missing/empty matching captions, exact duplicates, then small images. A 512-pixel threshold is a diagnostic, not a universal rejection rule for every architecture. Suggest the matching TagPilot/quality-review action. MCP cannot read or rewrite captions, delete duplicates, inspect faces, verify consent or judge identity consistency. Request user-provided examples when that judgment is needed.

For identity training, describe changeable pose, clothing, background and lighting so they are not all absorbed into the trigger. For style training, describe visible content separately from the intended style. Match tag-based versus natural-language captions to the chosen trainer/model. Do not automatically convert an existing collection's caption style or invent attributes. The image-model guide explains prompting, not a universal training caption template.

## Model checks

Page through `models_list`. Its fields are `catalog_id`, `kind`, `installed` and `size_bytes`; it has no architecture metadata, download link or filesystem path. Resolve an alias through the project's manifest/model card when available, or ask for the exact checkpoint if ambiguous. Model-catalog pagination includes components as well as main weights.

Check the base model plus its required encoder(s), VAE, and any workflow-specific LoRA, refiner, upscaler or image encoder. Keep these verdicts separate: listed, installed, compatible with the selected workflow, and proven to run. An installed flag alone establishes only installation detection. The catalog does not establish a trained LoRA's parent architecture. Ask the owner to install missing entries in Models; there is no MCP download/install tool.

For GGUF, confirm the matching GGUF loader and format, rather than inserting it into an ordinary checkpoint loader. Quantization changes memory use and sometimes output; it is not a new base family and does not guarantee a fixed VRAM requirement. Inference-only quantized or distilled checkpoints must not silently replace the full/base weights required by training.

## Training

Read `workspace_status`, review the selected dataset and check the required base. `gpu_available` may be null; MCP does not measure free VRAM or report GPU capacity. Ask for hardware information only when needed to make a recommendation. Training and ComfyUI may share GPU memory; do not stop ComfyUI by default or claim a concurrency guarantee.

The current `training_plan` schema accepts `dataset_id`, `output_name`, `family="sdxl"`, `profile="quick_test"`, `max_steps` (1–600, default 100), and `max_seconds` (60–3600, default 1800). The recipe fixes rank 16 and AdamW and requires the installed SDXL Base checkpoint. Those limits bound work; they are neither a quality promise nor a spending cap. Do not silently change a request for FLUX, Qwen, Anima, Lumina, Hunyuan or Wan into an SDXL run. Prepare a trainer/UI handoff instead.

Write tools require operator-verified deployment gates and connection grants. If absent, explain the missing capability and continue read-only preparation. Do not set `MCP_STORAGE_VERIFIED` or `MCP_GPU_VERIFIED` on the user's behalf merely to bypass the gate. The user's requested model, dataset and budget still govern an unattended connection.

Show the returned plan summary. If approval is pending, the owner uses Settings → MCP → Pending approvals; a plan expires after ten minutes. Once approved, call `training_start` with its `plan_id` and a new, saved lowercase UUIDv4 `request_id`. Reuse that ID and identical payload on a transport retry. After acceptance, retain `operation_id` and poll `operation_get` at `next_poll_after_ms` or slower. Inspect both `state` and `error`; an HTTP/tool success is not a completed training run.

Use `runs_list` and `run_get` for granted run summaries and checkpoint handles. Queued, running, succeeded, stopped and interrupted are distinct. A paused queue leaves work waiting; MCP cannot unpause it. `run_cancel`, when exposed and explicitly requested, takes `run_id` and `request_id` and can lose progress since the last checkpoint. Do not cancel as a diagnosis or invent a resume tool.

## Comparisons and inference

`comparison_plan` accepts a granted `run_id`, `checkpoint_id`, `prompt` (1–2000 characters), `seed` (0–2^32−1; default 31337) and `strength` (0–2; default 1). Checkpoint IDs come from `run_get`. The run must be terminal, SDXL, and created by MCP recipe version 1. A run created in the UI can be visible but ineligible; `UNAPPROVED_RECIPE` does not mean the LoRA is corrupt.

This recipe creates two images: baseline and one selected checkpoint, at 1024 square, 20 steps, CFG 7, `dpmpp_2m` / `normal`, full denoise. These are current recipe settings, not a general SDXL recommendation. It does not accept width, height, CFG, negative prompt, sampler, scheduler, batch count or arbitrary workflow. ComfyUI must already be running and required models installed.

For each authorized comparison, plan → owner approval when required → `comparison_start` with a saved fresh `request_id` → poll the resulting operation. To compare several eligible checkpoints, keep the same prompt and seed and use a separate approved plan/operation per checkpoint within the user's budget. Reuse the original request ID only for retries of that same operation. Aggregate labels and operation IDs; do not claim a single MCP grid endpoint exists.

The ControlPilot **Try my LoRA** UI has broader family support and an all-checkpoint grid; that is a handoff when the MCP recipe cannot do the requested comparison. A successful MCP comparison does not expose pixels through `run_get`. Owner-approved exports can include selected comparison images; downloading requires the separate artifact-read grant and permission to disclose the selected content. No export is needed merely to recommend settings. If previews are unavailable, request the results instead of describing imaginary differences.

## Common outcomes

| Outcome | Response |
|---|---|
| Tool missing | Inspect discovered capabilities and grants; continue supported read-only work. |
| `NOT_AUTHORIZED` | Ask the owner to review the connection's grants/expiry; do not rotate tokens or broaden access automatically. |
| `CAPACITY_UNKNOWN` / `LIMIT_EXCEEDED` | Inspect the plan/budget and ask the owner to review capacity; do not lower verification requirements. |
| `CONFLICT` / `UNAPPROVED_RECIPE` | Confirm terminal state, family and MCP provenance; use the appropriate UI for unsupported runs. |
| `unknown` or ambiguous write timeout | Inspect the saved operation and provider state; retry only with the original request ID and payload. |
| No images/captions exposed | Give structural advice; obtain visible examples before qualitative claims. |

Deployment/setup details and export semantics are in the server resource `lorapilot://docs/mcp` and the repository's `docs/configuration/mcp.md`. Never confuse that short server resource with the full local setup document.
