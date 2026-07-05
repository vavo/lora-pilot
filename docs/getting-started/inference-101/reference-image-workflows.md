# Reference Image Workflows

_Last updated: 2026-07-06_

Text prompts are only one way to steer a model. Reference-image workflows start with pixels: a source image, a pose, a depth map, a style reference, a face reference, a sketch, or several images that should influence the result.

This matters because some jobs are painful to solve with words alone. You can describe a pose for twenty minutes and still get a shrug from the sampler. A reference workflow gives the model structure or style directly.

## The Main Families

Image-to-image is the direct version. The workflow encodes the source image into latent space, then samples a new image from that starting point. Denoise controls how far the model may drift. Lower denoise preserves more of the source. Higher denoise gives the prompt more room to rewrite the image.

ControlNet is the structure version. A preprocessor extracts something useful from the source, such as edges, depth, pose, line art, or segmentation. The model then uses that structure while generating a new image. This is the better tool when composition, pose, or layout must survive but the visual details can change.

Reference adapter workflows are the style and identity version. IP-Adapter-style workflows, Flux Redux-style workflows, and similar reference-image systems use one or more images as conditioning. They can transfer style, blend references, preserve a face, or steer a composition without training a LoRA. These workflows are powerful, but they are also more model-family and custom-node dependent than basic image-to-image.

Caption-assisted image-to-image sits between prompt and image control. A captioning model such as Florence2 or JoyCaption can describe the input image, then that generated description becomes part of the prompt. This helps the workflow preserve important content while still allowing an edit instruction.

## Choosing the Right Reference Method

| Job | Better Starting Point | Why |
|---|---|---|
| Keep most of an image but change style or details | Image-to-image | Denoise gives direct control over how much changes. |
| Keep pose, layout, edges, or depth | ControlNet | The control image carries structure that the prompt alone cannot hold reliably. |
| Apply a style from one image to another | Reference adapter | The style image can condition the model without training a style LoRA. |
| Blend multiple references into one output | Reference adapter or Redux-style workflow | The workflow can weight several image inputs plus a text prompt. |
| Preserve a face or identity from one image | Face/reference adapter or trained LoRA | Use adapters for quick one-off work, LoRAs for repeatable identity across many images. |
| Edit using natural language while keeping a source image | Image edit model or caption-assisted img2img | The model needs both the source image and a clear edit instruction. |

## Denoise Is Still the First Lever

In image-to-image, inpainting, and many refinement workflows, denoise is the most important control. Around the middle range, the result often keeps the source composition while changing details. Near `1.0`, the source becomes more of a suggestion. Very low values may barely change anything.

The exact value depends on the model and workflow. Treat denoise as an experiment, not a rule. Fix seed, model, resolution, sampler, and prompt first, then test a few denoise values side by side.

## ControlNet Strength Is Not a Quality Button

ControlNet has its own strength and timing controls. More strength means more structural pressure, not automatically better output. Too much control can make an image stiff or ugly. Too little control can let the model ignore the guide.

Start with one control type. Compare Canny, depth, and pose only when the job calls for them. Canny tends to preserve edges. Depth tends to preserve spatial layout. OpenPose focuses on human pose and leaves more visual detail to the model and prompt.

## Reference Adapters Are Fast, Not Magic

Reference adapters are tempting because they can feel like a one-image LoRA. That is useful framing, but it is not the same as training. A reference adapter can quickly borrow style, identity, or composition from an image. A trained LoRA is still better when you need a concept to survive across many prompts, poses, scenes, and sessions.

Use reference adapters for exploration, one-off style transfer, moodboarding, blends, and early art direction. Use LoRA training when the same subject or style needs to become a reusable asset.

## A Safe Test Pattern

Start with a source image that already works. Run a plain image-to-image test with fixed seed and a few denoise values. Add ControlNet only if structure drifts. Add a reference adapter only if style or identity needs stronger image-based guidance. Save each stage as a separate workflow.

Do not add image-to-image, ControlNet, two style references, a face adapter, an upscaler, and a detailer in the first run. It may work. It may also fail in six places and teach you nothing, which is the less charming option.

## Next

Continue to [Inference Workflows](inference-workflows.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
