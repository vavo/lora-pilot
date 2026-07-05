# Inference Workflows

_Last updated: 2026-07-05_

A repeatable process beats random trial-and-error every time.

## 6-Step Workflow

1. Pick your baseline checkpoint and model family.
2. Use a known-good starter workflow before adding custom nodes.
3. Generate with a fixed seed and batch size 1.
4. Adjust one variable: prompt, LoRA weight, CFG, steps, sampler, scheduler, denoise, or resolution.
5. Re-run and compare side by side.
6. Lock winning settings into a named preset or workflow JSON.
7. Save final metadata with outputs.

## Save Rules

- Save workflows with clear names, e.g. `sdxl-product-v1.json` and `sdxl-product-v2-upscale.json`.
- Keep the winning prompt, negative prompt, seed, sampler, scheduler, CFG, steps, denoise, dimensions, checkpoint, VAE, and LoRA weights.
- Keep one "known-good" starter setup untouched.
- In ComfyUI, keep generated PNGs when testing. Dragging them back onto the canvas can recover the embedded workflow metadata.
- When you import a community workflow, save a local copy before replacing models or installing missing nodes.

## Quality Control Loop

- If results drift: go back to your starter setup
- If identity/style weak: adjust LoRA weight slightly
- If output overcooked: reduce CFG or steps
- If a workflow breaks after import: check missing custom nodes and missing model files before editing the graph.
- If an output goes black or flat: check the VAE path and the `VAEDecode` connection.

## Imported Workflow Checklist

Before queueing a workflow from Civitai, GitHub, or Discord:

1. Read the workflow notes for required checkpoints, LoRAs, VAEs, upscalers, and custom nodes.
2. Confirm model family: SD 1.5, SDXL, Flux, Wan, LTX, etc.
3. Replace missing checkpoints with the same model family, not whatever happens to be in the dropdown.
4. Install missing custom nodes through ComfyUI Manager, then restart ComfyUI.
5. Run a small resolution test before queueing a heavy final render.

## Next

Continue to [Performance Optimization](performance-optimization.md).

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
