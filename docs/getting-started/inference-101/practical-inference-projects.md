# Practical Inference Projects

_Last updated: 2026-07-05_

The fastest way to learn inference is to run small projects with boring constraints. Boring constraints are the point. They make it obvious which change helped and which change only looked impressive because everything moved at once.

Use these projects as short drills. Each one should take less than an hour and leave you with saved outputs, metadata, and one reusable workflow or preset.

## Project 1: Controlled Portrait Iteration

Create a simple portrait workflow with one checkpoint, one optional portrait LoRA, one prompt, one fixed seed, and batch size `1`. Generate a baseline image. Then run three controlled changes: lower CFG, higher CFG, and a small LoRA weight adjustment.

The goal is not the best portrait of your life. The goal is to see how guidance and LoRA weight affect identity, texture, and anatomy when the rest of the setup stays fixed.

Success looks like a small comparison set where the subject remains recognizable, detail improves without harsh distortions, and the winning settings are saved with the seed and model names.

## Project 2: Image-to-Image Style Transfer

Start with a source image that already has a readable composition. Run image-to-image with one style LoRA or one style-focused checkpoint. Keep the prompt simple. Test denoise in small steps, such as `0.25`, `0.45`, and `0.65`.

Watch how the source image changes. At low denoise, the structure should survive and the style may be subtle. At higher denoise, the style may become stronger while the original composition weakens. That tradeoff is the lesson.

Success means you can explain which denoise value preserved the source best and which value gave the strongest style without wrecking the image.

## Project 3: Inpainting Repair

Pick a generated image with one obvious flaw: a hand, logo detail, background object, eye, sleeve, or artifact. Mask only the bad region. Run an inpainting workflow with a conservative denoise value first, then one stronger pass.

The goal is to repair the image without regenerating everything else. If the edit spills into clean areas, inspect the mask and denoise before changing the prompt.

Success means the repaired region improves while the rest of the image remains stable enough that the original composition still feels intact.

## Project 4: ControlNet Composition Lock

Use a pose, depth map, canny edge image, or layout guide. Generate a text-to-image output with and without ControlNet using the same prompt and seed. Compare how strongly the composition holds.

This project teaches the difference between asking for structure in a prompt and supplying structure as an input. Prompts can suggest a pose. ControlNet can enforce one.

Success means the ControlNet version follows the guide clearly, while the non-ControlNet version shows why prompt-only control has limits.

## Project 5: First Image-to-Video Test

Start with one strong still image. Use an image-to-video workflow with a short duration and modest resolution. Keep the first test cheap. Change only one motion-related setting or prompt phrase between runs.

The goal is to learn whether the input image anchors identity and composition through motion. Do not try to repair the still image, change the style, and create complex camera movement in the same first test. That is not ambition. That is a blender with invoices.

Success means you get a short clip where the first frame still feels connected to the final motion, and the settings are saved well enough to repeat.

## What to Keep

For each project, save the workflow JSON or preset, generated outputs, prompt, negative prompt, seed, checkpoint, VAE, LoRA names and weights, sampler, scheduler, steps, CFG or guidance, denoise, resolution, and any ControlNet, upscale, or video settings.

The artifact is not just the image. The artifact is the repeatable path to the image.

## Where to Go Next

Move from these drills into the component docs for [ComfyUI](../../components/comfyui.md), [InvokeAI](../../components/invokeai.md), and the broader [Inference user guide](../../user-guide/inference.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
