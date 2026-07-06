# Model Components Explained

_Last updated: 2026-07-06_

ComfyUI workflows look like boxes and noodles until you know what each component does. The good news: most image workflows use the same few parts. The bad news: the boxes have names like `CLIP`, `VAE`, and `latent`, because apparently "prompt brain" and "image compressor" were too friendly.

Think of a workflow like a small studio. The base model is the artist. The text encoder reads the brief. The sampler directs the work session. The VAE handles the translation between compressed working space and visible pixels. LoRAs sit beside the artist as style notes or character references. ControlNet acts like a pose director or layout board. The save node puts the finished image on disk.

## Where the Pieces Live in LoRA Pilot

Most model files live under `/workspace/models`, grouped by the type ComfyUI expects. Checkpoints usually belong in `/workspace/models/checkpoints`, LoRAs in `/workspace/models/loras`, VAEs in `/workspace/models/vae`, ControlNet models in `/workspace/models/controlnet`, and text encoders in the encoder folders required by the workflow. Video and newer-family models may use more specific folders because their graphs load several files instead of one checkpoint.

ControlPilot downloads models from `config/models.manifest` and places them where the bundled tools expect them. If a ComfyUI workflow says `Value not in list: ckpt_name`, the workflow is asking for a file that is missing, renamed, or stored in the wrong category. The fix is not better prompting. The fix is finding the file.

In the product, ControlPilot is the place to start, stop, and reach ComfyUI or download known models. ComfyUI is where you see the components as nodes. MediaPilot is where you compare generated outputs after the graph runs. TrainPilot creates LoRAs, which then return to the model folder for inference.

## Base Model or Checkpoint

The base model is the artist you hired. SD1.5, SDXL, Flux, Qwen Image, Wan, LTX, and other families all have different habits, tools, and hardware needs.

A checkpoint carries the model's general visual knowledge: what faces, cars, trees, lighting, camera angles, materials, and styles tend to look like. Community checkpoints can push that knowledge toward realism, anime, product photos, illustration, or another domain.

Use the model family that fits the job. A fast SD1.5 checkpoint is a good sketch artist. SDXL is a reliable generalist. Flux-style workflows often read natural prompts well but ask for more memory and stricter loader setup. Video families are their own studio, not a prettier image checkpoint.

## Text Encoder and CLIP

The text encoder reads your prompt and turns words into conditioning the model can use. In many ComfyUI graphs you see this as `CLIP Text Encode`. In a simple checkpoint workflow, `Load Checkpoint` outputs `MODEL`, `CLIP`, and `VAE` together.

If the model ignores prompts, do not only raise CFG. Check whether the workflow uses the right text encoder or CLIP path for the model family. Newer families may need specific encoders. Mixing encoders is like handing the artist a brief written in a dialect they half-understand.

## VAE

The VAE translates between latent space and pixels. Latent space is the compressed workbench where the sampler does most of the generation. `VAEDecode` turns that latent into an image you can see. `VAEEncode` pushes an input image into latent space for image-to-image and inpainting.

A wrong VAE can produce washed-out color, flat contrast, black images, odd artifacts, or soft output. Some checkpoints include a VAE. Others expect a separate file. SD1.5, SDXL, Flux, and video models do not share one universal VAE.

Use the VAE recommended by the model card or workflow. If images look strangely dull across many prompts, inspect the VAE before blaming your negative prompt.

## LoRA

A LoRA is a small adapter. It does not replace the base model. It nudges the base model toward a character, product, style, outfit, object, or visual habit.

Use the recipe analogy if it helps: the base model is the kitchen and chef, while the LoRA is a small card that says "cook this dish with this spice profile." A good LoRA can change the result a lot, but it still depends on the kitchen. A product LoRA trained for SDXL will not behave correctly in a Flux workflow unless it was trained for that family.

LoRAs live in `/workspace/models/loras` for ComfyUI-style use. In a graph, a LoRA loader usually receives the model and text encoder, then outputs modified versions for the sampler and prompt encoders. If the LoRA has no effect, check the file path, base family, trigger word, and strength.

## ControlNet

ControlNet gives the model structure. A prompt can say "person sitting," but a pose ControlNet can show the exact skeleton. Depth can guide foreground and background. Canny edges can preserve outlines. Line art can turn a sketch into a finished image.

Think of ControlNet as the director taping marks on the stage. The actor can still perform, but the pose, outline, or spatial layout has a stronger constraint.

ControlNet models live in the ControlNet model location expected by ComfyUI and the manifest. A typical graph sends a source image into a preprocessor, sends the processed map into ControlNet, and feeds that conditioning into the sampler.

## Refiner, Upscaler, and Detail Passes

Refiners and upscalers belong near the end of the process. The first generation chooses composition. Later passes add resolution, texture, or detail.

Do not upscale every draft. Pick the best composition, fix obvious problems, then spend compute on polish. Upscaling a bad image gives you a larger bad image, which is technically progress if your goal is storage pressure.

## Embeddings and Textual Inversion

Textual inversion and embeddings teach the text side a new token or shortcut. They are smaller than LoRAs and often appear as style, quality, or negative-prompt helpers. Older SD1.5 workflows use them more than many newer workflows.

Use embeddings only when the model family and UI support them. A negative embedding that improves one checkpoint may do nothing in another family.

## The Simple Text-to-Image Path

A beginner ComfyUI text-to-image graph usually follows this path:

```text
Load Checkpoint -> MODEL, CLIP, VAE
CLIP Text Encode -> positive and negative conditioning
Empty Latent Image -> width, height, batch size
KSampler -> denoised latent
VAE Decode -> visible image
Save Image -> output file and metadata
```

That graph is worth understanding before you import a 90-node workflow. Once you know this spine, LoRAs, ControlNet, inpainting, and upscaling become branches instead of chaos.

## When Components Do Not Match

ComfyUI tends to fail in practical ways. `Value not in list: ckpt_name` means the workflow references a checkpoint you do not have. Red nodes usually mean a custom node package is missing or failed to import. Black or flat images often point to VAE trouble. Weak prompt following can mean the text encoder path is wrong. A LoRA that does nothing often means wrong base family, missing trigger, low strength, or wrong file location.

The useful habit is to check components before tuning generation settings. Samplers and CFG cannot repair a missing model file.

## Next

Continue with [Complete Model Guide](complete-model-guide.md), [Generation Parameters](generation-parameters.md), or [Advanced Techniques](advanced-techniques.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
