# Inference Workflows

_Last updated: 2026-07-06_

A workflow is not only a graph or a preset. It is the way you move from idea to output without losing the trail. The graph generates the image. The workflow helps you understand why that image happened.

The best inference workflows are boring in a useful way: a known baseline, one change at a time, clear saved versions, and enough metadata to reproduce the result later.

## Start With a Baseline

Before experimenting, create one small setup that works. For text-to-image in ComfyUI, that means a checkpoint loader, two prompt encoders, an empty latent image, a sampler, a VAE decode node, and a save node. For InvokeAI, it means one model, one prompt, one seed, one resolution, and one settings preset.

Do not keep editing the only working copy. Save it as the starter. Duplicate it for experiments. A baseline is not sacred because it is perfect; it is sacred because it gives you a place to return when the experiment turns into a crime scene.

When learning a new ComfyUI model family, an official Workflow Template is often the best baseline. Templates are built around supported model graphs and can surface missing model files before you waste time debugging a half-loaded canvas.

## Make One Change Per Run

Once the baseline works, choose a single variable. Change the prompt, or the LoRA weight, or CFG, or steps, or sampler, or denoise, or resolution. Not all of them. Generate, compare, and decide whether the change helped.

The fixed seed is your friend during this phase. It keeps the composition similar enough that you can see what your change actually did. When you want new compositions, randomize the seed on purpose.

## Compare Outputs Side by Side

Your eyes are unreliable when images arrive one at a time. Compare candidates side by side with the prompt, model, seed, sampler, scheduler, CFG, steps, denoise, resolution, VAE, and LoRA weights nearby. MediaPilot exists for this job: use it to review outputs, keep winners, and avoid turning your downloads folder into a landfill with thumbnails.

In ComfyUI, keep generated PNGs while testing. Dragging a ComfyUI-generated PNG back onto the canvas can recover the embedded workflow metadata. In InvokeAI, keep boards and metadata organized so good outputs do not become folklore.

## Import Community Workflows Carefully

Community workflows are useful because someone else already built the graph. They are also fragile because the graph assumes specific checkpoints, LoRAs, VAEs, upscalers, custom nodes, model families, and sometimes old node versions.

When importing a workflow, read the notes first. Install missing custom nodes through ComfyUI Manager, restart ComfyUI from ControlPilot, then reload the workflow. Replace missing models with the same family, not the first file that appears in a dropdown. Run a small resolution test before sending a heavy render. If the small test fails, the large render was not going to become wise through suffering.

Remember that the JSON is not the whole workflow. A ComfyUI graph may depend on source images, masks, video files, audio files, model weights, custom nodes, and Python packages. If any of those are missing, the graph can be perfectly valid and still fail.

## Name Versions Like You Expect to Reuse Them

Useful names include the model family, purpose, and stage. `sdxl-product-v1.json`, `sdxl-product-v2-upscale.json`, `flux-poster-controlnet-v3.json`, and `wan-i2v-product-spin-v1.json` tell future-you something. `final-final-new.json` tells future-you to make coffee.

Keep one known-good starter untouched. Save milestones when a workflow starts using extra branches such as ControlNet, inpainting, LoRAs, upscalers, face/detailer passes, or video-specific loaders.

## A Practical Daily Loop

Use this loop for normal work:

| Phase | What Happens | What Stays Fixed |
|---|---|---|
| Baseline | Confirm the model and workflow run correctly. | Model family, seed, sampler, resolution. |
| Explore | Try prompt and composition variants. | Model stack and core settings. |
| Tune | Adjust CFG, steps, denoise, LoRA weight, or sampler. | Only one variable moves at a time. |
| Select | Compare candidates and pick winners. | Metadata stays attached. |
| Polish | Upscale, refine, inpaint, or detail selected outputs. | Original winner remains saved. |

This loop is intentionally plain. Inference already has enough knobs. The process does not need to cosplay as a research paper.

For API work, use ComfyUI's API-format workflow export rather than the regular editor JSON. The editor file preserves canvas layout; the API format is what `POST /prompt` expects.

## Next

Continue to [Performance Optimization](performance-optimization.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
