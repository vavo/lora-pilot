# Model Selection for Inference

_Last updated: 2026-07-05_

Model selection is the quiet part of inference that decides whether the rest of your settings make sense. A good prompt with the wrong model family is still the wrong setup. A correct LoRA on an incompatible checkpoint is not "almost right"; it is a small ceremony for wasting GPU time.

Think of the model stack as three layers: the checkpoint, optional LoRAs, and the VAE or decoder. Keep those layers compatible before you tune anything else.

## The Checkpoint Sets the World

The checkpoint is the base model. It decides the general visual language, supported resolution range, prompt behavior, architecture, and often the expected workflow nodes. SD 1.5, SDXL, Flux, Wan, LTX, HunyuanVideo, and other families do not all want the same loaders, guidance values, latent sizes, or auxiliary files.

When you download a model, read the model card before trusting generic settings. Many modern models are distilled, turbo-style, or built around family-specific guidance. Copying an old SDXL preset into a newer model family is how people get bad images and then blame the prompt like it personally betrayed them.

## LoRAs Add a Specific Bias

A LoRA is not a replacement checkpoint. It nudges a compatible base model toward a trained subject, style, character, product, clothing item, lighting pattern, or other concept. Start with one LoRA, confirm that it works, then add complexity.

For many image workflows, a LoRA weight around `0.6` to `0.9` is a sensible first test. Too low and the concept may disappear. Too high and the LoRA can distort anatomy, texture, composition, or the base model's strengths. The right number depends on how the LoRA was trained and what checkpoint it expects.

The important habit is to test LoRAs one at a time. If three LoRAs are loaded and the output breaks, you have created a small mystery, not a diagnosis.

## The VAE Is Easy to Ignore Until It Is Wrong

The VAE decodes latent output into pixels. Some checkpoints include what they need. Others expect a separate VAE. Video and newer model families may use their own decoder files. When the VAE is wrong or missing, the output can look washed out, black, gray, flat, or oddly colored even when the sampler did its job.

If a workflow produces technically valid but visually broken images, check the VAE before rewriting the prompt. In ComfyUI, trace the `VAE` output from the loader into `VAEDecode`. In imported workflows, confirm the VAE file exists and belongs to the same model family.

## A Conservative Starter Stack

For image generation, start with one reliable checkpoint, one optional LoRA, and the VAE recommended by the model author. Save that as your baseline. Keep the baseline small enough that you can explain every piece of it.

| Layer | First Choice | When to Change It |
|---|---|---|
| Checkpoint | One known-good model for the target family | When the model cannot produce the desired style, subject, or workflow type. |
| LoRA | None, then one compatible LoRA | When you need a trained identity, style, product, or concept. |
| VAE / decoder | The model author's recommended file | When outputs look washed out, black, gray, or wrong-family. |
| Resolution | The model family's expected size | When composition is stable and VRAM allows a larger pass. |

## Family Matching Matters

The simplest rule is also the least glamorous: keep model families together. SDXL workflows want SDXL checkpoints and SDXL-size latents. Flux workflows need Flux-compatible loaders and guidance behavior. Video workflows often need a matched text encoder, VAE, transformer, scheduler assumptions, and frame settings.

When importing a workflow, replace missing models with the same family first. "This file exists in the dropdown" is not the same as "this file belongs in the graph."

## Next

Continue to [Core Generation Settings](core-generation-settings.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
