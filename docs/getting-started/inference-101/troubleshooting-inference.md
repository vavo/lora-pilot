# Troubleshooting Inference

_Last updated: 2026-07-05_

Troubleshooting inference is mostly about refusing to panic-edit the workflow. A bad output is evidence. A validation error is evidence. A missing model dropdown value is evidence. Read the evidence before moving ten knobs at once.

Start from the smallest reproduction you can build. If the full graph fails, test the base text-to-image chain. If the base chain works, add the missing piece back. This is not glamorous, which is why it tends to work.

## Output Quality Suddenly Drops

When a result gets worse after earlier good runs, first confirm that the model stack did not change. Check checkpoint, LoRA files, LoRA weights, VAE, sampler, scheduler, seed, CFG, steps, denoise, and resolution.

Re-run a known-good seed and prompt. If the known-good run still works, the model stack is fine and the new change caused the problem. If the known-good run fails, something deeper changed: model files, workflow wiring, VAE, custom nodes, or runtime state.

## Distortions, Harsh Detail, or Broken Anatomy

Lower guidance before rewriting the prompt. Reduce LoRA weight if a trained concept is overpowering the base model. Keep sampler and seed fixed while testing.

If a model family recommends lower guidance or special settings, follow that. Generic SDXL settings are not a treaty signed by every future model.

## Image-to-Image or Inpainting Ignores the Source

Check denoise. High denoise gives the sampler more freedom and can destroy the input. Low denoise preserves more of the source and may barely change it. For inpainting, also inspect the mask. A sloppy mask creates sloppy edits with a straight face.

If only one region should change, make sure the workflow is actually using an inpainting path and not a full image-to-image pass pretending to be careful.

## Black, Gray, Flat, or Washed-Out Output

Check the VAE or decoder path. In ComfyUI, follow the `VAE` connection into `VAEDecode`. Confirm the VAE belongs to the same model family and exists in the expected folder.

Also check the model card. Some checkpoints have a baked-in VAE, some recommend a separate file, and newer families may use different decoder assumptions.

## ComfyUI Shows Red Missing-Node Blocks

Use ComfyUI Manager to install missing custom nodes, restart ComfyUI, then reload the workflow. If nodes stay red, read the ComfyUI log for the failed import or dependency error.

Missing nodes are only one half of the problem. Imported workflows can also reference missing checkpoints, LoRAs, VAEs, upscalers, ControlNet models, or video model files. Those do not appear just because the node package installed successfully.

## ComfyUI Says a Model Value Is Not in the List

Find the loader named in the error, often `CheckpointLoaderSimple`, `LoraLoader`, `VAELoader`, `ControlNetLoader`, or an upscaler loader. Select a file that exists in the dropdown and belongs to the workflow family.

If the model is supposed to be managed by LoRA Pilot, pull it through model management when it exists in the manifest. Restart or refresh ComfyUI after adding model files.

## CUDA Out of Memory

Set batch size to `1`. Lower width and height. Disable optional branches. Close or stop other GPU-heavy services. Prefer FP8 or quantized variants when the model family supports them. Restart ComfyUI after several failed heavy runs.

If a workflow fails at high resolution, rerun it at a small test size. A small successful test tells you the graph is probably valid and the failure is capacity. A small failed test tells you not to waste time turning up the resolution like a threat.

## A Short Escalation Path

When stuck, reproduce with the saved starter workflow, change one variable, compare side by side, check loader nodes for missing or wrong-family models, check ComfyUI Manager and service logs, then document the winning config.

If the starter workflow is gone, rebuild one. That hurts once. Debugging without it hurts repeatedly.

## Next

Continue to [Practical Inference Projects](practical-inference-projects.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
