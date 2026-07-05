# What is Inference?

_Last updated: 2026-07-06_

Training teaches the model. Inference uses what the model already learned. Every time you click Generate, queue a ComfyUI workflow, or run an image-to-video graph, you are doing inference.

That distinction matters because most beginner confusion comes from trying to fix an inference problem as if the model needs to be retrained.

If a generated image is close but not quite right, you usually start by changing inference inputs: prompt, seed, LoRA weight, guidance, denoise, sampler, resolution, or workflow shape. Training is the expensive answer. Inference is where you learn whether you even need that answer.

## The Generation Loop

A normal image generation run has four parts.

The model stack supplies the visual knowledge. A checkpoint gives the base style and capability. A LoRA can add a trained subject, character, product, or style. A VAE turns latent data back into pixels, and the wrong VAE can make a good workflow look washed out, black, flat, or just cursed in the boring technical way.

The prompt describes what you want. The negative prompt describes what you want the model to avoid. Prompts are not commands in the usual software sense. They are conditioning signals. A prompt can strongly influence the output, but it does not override a poor model choice, a mismatched workflow, or settings copied from the wrong model family.

The sampler turns noise into an image over a series of steps. This is where seed, CFG or guidance, sampler, scheduler, denoise, and resolution start to matter. These controls are connected. Raising steps while also changing CFG and sampler tells you almost nothing, because every variable moved at once.

The output is the evidence. Save the image, metadata, workflow JSON, and model names when a run is worth revisiting. If you cannot reproduce a result later, it was a lucky accident, not a workflow.

## Why the First Week Feels Messy

Most beginners do not fail because Stable Diffusion is impossible. They fail because they test like chaos scientists with no notebook. A weak result appears, then everything changes at once: new seed, stronger prompt, different checkpoint, extra LoRA, higher CFG, more steps, larger resolution, new sampler, maybe a ControlNet for morale. The next image changes. Nobody knows why.

The practical fix is simple: keep one starter setup untouched. Duplicate it for experiments. Change one variable. Compare side by side. Keep the metadata for anything good enough to repeat. This habit is more valuable than knowing the names of twenty samplers.

## Inference Is Also Workflow Choice

Not every task should start from a blank prompt. If you already have an image and want a variation, you are in image-to-image territory. If only one region should change, you want inpainting. If pose, depth, edges, or composition must survive, ControlNet is probably the right tool. If identity or style must carry through, a LoRA may be the important part. If the result needs motion, text-to-video or image-to-video changes the whole setup.

Before tuning settings, ask what kind of job you are doing. Then pick the workflow shape that gives the model the right kind of input.

## Next

Continue to [Inference Stacks](inference-stacks.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
