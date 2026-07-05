# Performance Optimization

_Last updated: 2026-07-05_

Inference performance is not about making every render tiny and ugly. It is about spending expensive settings only when they can actually improve the result.

The fastest workflow is usually two-phase: cheap previews while ideas are weak, then higher-quality passes only for the images worth keeping.

## Preview First, Polish Later

During exploration, keep batch size at `1`, use a moderate resolution, avoid unnecessary upscalers, and do not overpay for steps. A preview does not need to be final quality. It needs to answer whether the composition, prompt, model, and workflow direction are worth continuing.

Once a candidate works, move into a final pass. Increase resolution if the model family supports it, add upscale or refinement nodes, raise steps only if detail is still improving, and keep metadata attached. This is where quality settings belong.

## Resolution Is the Expensive Lever

Width and height affect VRAM more aggressively than most beginners expect. A small increase in each dimension can become a large memory increase overall. If you hit CUDA out-of-memory, reduce resolution before rewriting the whole workflow.

Use model-appropriate starter sizes. Upscale winners instead of forcing huge base generations. This gives you faster iteration and fewer memory failures.

## Steps Have a Plateau

Steps are useful until the image has enough refinement. After that, they become a time tax. If a model looks finished at 24 steps, rendering 45 steps may only make you feel productive while the GPU quietly disagrees.

Some model families are designed for fewer steps. Distilled, turbo, LCM, and some modern image or video workflows may have recommended ranges far below older SDXL habits. Check the model notes before assuming more steps means better output.

## Keep the Graph Small While Debugging

Every extra branch costs attention and often memory. Disable upscalers, face/detailer passes, extra ControlNet branches, heavy preprocessors, and large batch runs until the base image is good. Add the expensive pieces only after the core workflow is stable.

In ComfyUI, this also makes errors easier to read. A simple graph with one missing model is annoying. A giant graph with missing nodes, wrong-family models, and multiple failed branches is a support ticket with lighting effects.

## VRAM Triage

When memory fails, try the boring fixes first: batch size `1`, lower width and height, fewer active branches, smaller preview settings, quantized or FP8 model variants when the model family supports them, and a ComfyUI restart after several failed heavy runs.

If a workflow worked earlier and suddenly crawls, check whether another GPU-heavy service is running in LoRA Pilot. Training, tagging, notebooks, and inference can compete for memory. The model is not always the villain.

## Optimization Means Reproducible Speed

If you cannot reproduce the result, it is not optimized yet. Save the workflow, prompt, seed, model names, VAE, LoRA weights, sampler, scheduler, steps, CFG, denoise, resolution, and any upscale settings. Then make it faster.

Performance without reproducibility is just rushing into a wall with metrics.

## Next

Continue to [Troubleshooting Inference](troubleshooting-inference.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
