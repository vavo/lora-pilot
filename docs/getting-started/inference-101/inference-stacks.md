# Inference Stacks

_Last updated: 2026-07-05_

LoRA Pilot gives you two main inference surfaces: ComfyUI and InvokeAI. They overlap on purpose. Both can generate images, but they are built around different working styles.

InvokeAI is the cleaner place to iterate when you want a guided interface, quick prompt changes, boards, and fewer moving parts. ComfyUI is the place to go when the workflow itself matters: branching graphs, ControlNet chains, LoRA experiments, upscale passes, model-specific video pipelines, or any setup where you need to see each operation as a connected node.

## ComfyUI: The Workshop Bench

ComfyUI exposes the generation graph. Loaders, prompt encoders, samplers, VAE nodes, image processors, ControlNet branches, upscalers, and save nodes are all visible. That visibility makes it powerful and occasionally impolite.

Use ComfyUI when you need custom workflows, when you want to import community graphs, when you are testing model families with special loaders, or when you need to preserve an exact visual pipeline. Its canvas also makes debugging more concrete: when a workflow fails, you can trace the broken node, check the missing model, inspect the socket type, and see where the data stopped flowing.

The tradeoff is screen noise. A beginner can easily mistake a big graph for a good graph. Start with a small text-to-image chain, learn the node anatomy, then add branches one at a time.

## InvokeAI: The Focused Generator

InvokeAI is better when the job is mostly generation and selection. You prompt, adjust settings, compare results, save boards, and iterate quickly. It is a good starting point when you are learning seed, steps, guidance, sampler, resolution, and prompt structure without also learning a node editor.

The tradeoff is flexibility. Once you need unusual multi-stage image logic, complex ControlNet routing, or community workflows built for ComfyUI, InvokeAI stops being the natural fit.

## The Practical Rule

Start in the surface with the least ceremony that still solves the job. If you are learning basic generation, start in InvokeAI. If the workflow shape is part of the result, use ComfyUI. If you are debugging a model-specific community workflow, use ComfyUI and keep a small known-good graph nearby so you can separate workflow errors from model errors.

| Use Case | Better First Choice |
|---|---|
| Prompt exploration, boards, quick image selection | InvokeAI |
| Learning seed, CFG, sampler, and resolution | InvokeAI or a tiny ComfyUI graph |
| Custom node workflows | ComfyUI |
| ControlNet, inpainting branches, upscales, detailers | ComfyUI |
| Text-to-video or image-to-video model pipelines | Usually ComfyUI |
| Debugging missing nodes or model loaders from a shared graph | ComfyUI |

Neither surface is the "real" one. The real one is the one that lets you finish the job and reproduce the result.

## Next

Continue to [Model Selection for Inference](model-selection-for-inference.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
