# Advanced Techniques

_Last updated: 2026-07-06_

Advanced generation is not about using a larger workflow. It is about giving the model the right kind of input for the job.

A prompt is enough when you only need a new image. The moment you need to preserve a face, edit one region, follow a pose, extend a canvas, reuse a product, or turn an image into video, you need more than text. That is where inpainting, image-to-image, ControlNet, reference adapters, upscaling, and multi-stage ComfyUI graphs become useful.

## Choose the Technique by the Job

| Job | Start With |
|---|---|
| Fix one bad area | Inpainting |
| Make a variation of an existing image | Image-to-image |
| Extend an image beyond its border | Outpainting |
| Preserve pose, depth, edges, or layout | ControlNet |
| Borrow style or identity from a reference image | Reference adapter |
| Reuse a character, product, or style across many prompts | LoRA |
| Improve a finished image | Upscale or refinement pass |
| Build a complex repeatable pipeline | ComfyUI workflow |

The mistake is using the most complicated graph first. Start with the simplest technique that supplies the missing control.

> **Why does this work?** Text prompts are weak at geometry and exact placement. Image inputs, masks, ControlNet maps, reference adapters, and LoRAs add different kinds of constraint. Each constraint narrows the model's choices in a way text alone cannot.

## Inpainting: Change One Region

Use inpainting when most of the image works and one area needs repair or replacement: a hand, face, logo, object, sky, background patch, or clothing detail.

The mask tells the workflow where the model may change pixels. The prompt tells it what belongs in that masked area. Keep the prompt local: describe the replacement region and enough surrounding context for lighting and style.

Good inpainting habits:

- mask a little beyond the broken edge
- use mask blur or feathering when available
- keep denoise high enough to fix the problem
- avoid rewriting the whole scene in the prompt
- save the original before editing

In ComfyUI, inpainting usually means an image input, a mask, a VAE encode path, a sampler, and a decode/save path. In ControlPilot, use the ComfyUI or InvokeAI surface that exposes the inpaint workflow you need.

> **Try this variation:** Take one generated portrait with a flawed hand. Mask only the hand and wrist. Generate three fixes with the same seed and different denoise values. You will learn the difference between "repair" and "replace" fast.

## Image-to-Image: Keep the Starting Point

Image-to-image starts from an existing image and lets the model reinterpret it. Denoise controls how far the output may drift.

Low denoise preserves structure. High denoise gives the model more freedom. If the output barely changes, raise denoise. If it destroys the source composition, lower denoise.

Use image-to-image for:

- style variations
- mood changes
- rough sketch to finished image
- photo to illustration
- product scene variations
- early concept exploration

Do not use image-to-image when you need one precise region fixed. Use inpainting for that. Do not use it when you need exact pose control. Use ControlNet or a pose/reference workflow.

## Outpainting: Extend the Canvas

Outpainting is inpainting outside the original image. You expand the canvas, mask the empty area, and ask the model to continue the scene.

Outpainting works best when the original image gives the model enough perspective, lighting, and style to continue. Huge expansions in one pass can drift. Expand in stages when the scene matters.

Good outpainting prompts sound like continuation notes:

```text
continue the same mountain landscape, same sunset lighting, distant pine forest, natural perspective
```

Keep the original image anchored. If each expansion changes the style, stop and lower denoise or use a stronger reference workflow.

## ControlNet: Preserve Structure

ControlNet workflows give the model a structural guide: pose, depth, edges, line art, segmentation, normal map, canny edges, or another control signal.

Use ControlNet when the layout matters more than prompt freedom:

- a character must keep a pose
- a product must sit at a specific angle
- architecture must preserve lines
- a sketch should become a finished image
- a depth map should guide scene structure

Control strength matters. More strength means more pressure, not better output. Too much can make the image stiff or ugly. Too little lets the model ignore the guide.

In ComfyUI, ControlNet is easiest to understand as a branch: source image -> preprocessor -> ControlNet -> sampler conditioning. Keep that branch visible and save a small baseline workflow before adding more branches.

## Reference Adapters: Borrow Style or Identity

Reference adapters, IP-Adapter-style workflows, Flux Redux-style workflows, and similar systems let one or more images influence the output without training a LoRA.

Use them for:

- moodboards
- one-off style borrowing
- early identity tests
- blending two references
- fast art direction

Use a LoRA instead when the same subject or style must work across many sessions, prompts, poses, and scenes. A reference adapter is a good sketchpad. A LoRA is a reusable asset.

See [Reference Image Workflows](../inference-101/reference-image-workflows.md) for the longer guide.

## Upscaling and Refinement

Upscaling should happen after composition works. Beginners often upscale too early because a larger image feels more professional. A bad composition at 4K is still a bad composition, now with more pixels to regret.

Use this order:

1. Generate small enough to iterate.
2. Pick the best composition.
3. Fix obvious problems with inpainting.
4. Upscale or refine the winner.
5. Save the workflow and output metadata.

Some upscalers increase resolution. Some add detail. Some change texture. Test them on copies, not your only good output.

## Multi-Stage ComfyUI Workflows

ComfyUI shines when a result needs stages:

- load model stack
- encode prompt
- generate base image
- apply ControlNet or reference branch
- inpaint or detail a region
- upscale
- save outputs and metadata

Build that graph one branch at a time. Run after each branch. If you import a community workflow, get the smallest version working before you add custom models, LoRAs, and video nodes.

ControlPilot helps start, stop, restart, and reach ComfyUI. MediaPilot helps review the outputs. The workflow itself still needs discipline. A graph with 80 nodes can be a production pipeline or a filing cabinet that learned to draw.

## A Practical Learning Path

Learn the techniques in this order:

1. **Image-to-image** to understand denoise.
2. **Inpainting** to repair one area.
3. **ControlNet** to preserve structure.
4. **Reference adapters** to borrow visual direction.
5. **Upscaling** to finish selected images.
6. **Multi-stage ComfyUI workflows** to combine the pieces.

Each step teaches a different kind of control. Do not skip straight to a giant workflow unless the goal is dependency management with occasional pictures.

## Next

Continue with [Character Consistency](character-consistency.md) or [Inference Workflow Types](../inference-101/workflow-types.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
