# Character Consistency with LoRA

_Last updated: 2026-07-06_

A prompt can describe a character. A LoRA can make the model remember one.

That memory comes with responsibility. Do not train a LoRA of a real person unless you have clear consent and a legitimate use. Do not publish face LoRAs, datasets, or generated examples without permission. A model that can reproduce someone's likeness can also put that likeness into scenes they never agreed to. If the sentence feels heavy, good. It should.

## Why Characters Drift

Without training or a reference workflow, the model treats each generation as a new attempt. "Woman with red hair" describes a category, not a person. Change the seed, pose, camera angle, clothing, or lighting, and the model may choose a new face that still satisfies the words.

LoRA training gives the model a trigger word tied to a specific character design or identity. Before training, a prompt like `woman with red hair` may produce anyone. After training, `mychar_anna` can point to the same character across new scenes.

## When Not to Train

Do not train a character LoRA when prompt consistency is good enough for a one-off image set. Use fixed seeds, reference images, image-to-image, or ControlNet first if you only need a few related frames.

Do not train when you lack rights to the character or consent from the person. Do not train when the dataset is weak, full of screenshots, watermarks, cropped faces, or mixed identities. Do not train when the project needs exact product or costume continuity more than face identity; a reference workflow or ControlNet may solve that with less risk.

Training makes sense when you need the same approved character across many prompts, outfits, poses, environments, or sessions. A comic character, brand mascot, original game character, licensed product mascot, or consented model can justify the extra work.

## Building the Dataset

Use 15 to 30 strong images for a first character LoRA. The face should be readable in most images, with a mix of front, three-quarter, side, close-up, wider crop, expression, and lighting. Include outfit variety if the character should change clothes later. Keep the same person or character design throughout.

Cut images where the face is hidden, the subject is tiny, the crop removes identity features, another person looks too similar, or the lighting changes the face beyond recognition. The trainer will learn the folder you give it, not the character you imagined while making the folder.

Caption with a rare trigger word:

```text
photo of mychar_anna, woman with short red hair, black jacket, standing in a city street, evening light
```

Name details you want to control later, such as clothing, pose, background, expression, and lighting. Leave some stable identity traits bound to the trigger if you want the character to keep them. Captioning is a steering wheel, not a confession booth.

## Training the First Version

Start with a normal LoRA run in TrainPilot, Kohya, or the trainer that matches your model family. Use the same base family you plan to generate with. SDXL LoRAs belong to SDXL workflows. Flux LoRAs belong to Flux workflows. This is the part where many problems pretend to be mysterious.

Use conservative first settings: batch size `1`, rank around `32`, a modest step count, and saved checkpoints. Generate samples during training with fixed prompts that include the trigger word.

Your first useful checkpoint may not be the final one. Character LoRAs often look good before they become rigid. Keep the checkpoint that preserves identity while still allowing new poses, clothing, and backgrounds.

## Using LoRA Strength

LoRA strength controls how hard the trained adapter pushes during generation. It is not a moral ranking of how much you believe in the character.

At `0.4`, you may get a faint resemblance while the base model keeps more freedom. At `0.7`, many character LoRAs start to feel balanced: recognizable identity, less stiffness. At `1.0`, identity pressure is stronger, but dataset habits may show up. At `1.2` or higher, some LoRAs become artificial, over-sharpened, same-faced, or stuck in training poses.

Make a small strength grid before judging the LoRA:

| 0.4 | 0.7 | 1.0 | 1.2 |
|---|---|---|---|
| subtle resemblance | balanced test | strong identity | overfit warning |

Use the same prompt and seed for the grid. If identity only appears at high strength, the LoRA may be undertrained, badly captioned, or trained against the wrong base family. If high strength copies the dataset, test an earlier checkpoint or improve dataset variety.

## Testing Consistency

Test the character with prompts that leave the dataset. A portrait prompt proves little if every training image was a portrait. Ask for a different outfit, a new environment, a side view, a full-body shot, and a lighting setup the dataset did not overrepresent.

Example test set:

```text
photo of mychar_anna, studio portrait, soft window light
photo of mychar_anna, hiking jacket, standing on a mountain trail
photo of mychar_anna, side view, reading in a cafe
photo of mychar_anna, full body, simple white background
photo of mychar_anna, cinematic night street, neon signs
```

Keep the seed fixed for one pass and varied for another. Fixed seed shows how prompts change one composition. Varied seeds show whether identity survives normal generation.

## Common Failure Patterns

If the character is not recognizable, check trigger spelling, base model family, LoRA file path, and whether the dataset had enough clear identity signal. If the character copies training images, test earlier checkpoints, reduce steps, remove duplicates, and add pose or outfit variety. If features drift between prompts, improve captions and add more angles. If outputs look distorted, inspect the source images before blaming the sampler.

For close-up face artifacts, test lower LoRA strength before retraining. A strong face LoRA can overpower the base model's normal anatomy. For outfit lock-in, caption clothing more clearly and add outfit variety. For background lock-in, cut repeated backgrounds or caption them as background.

## Combining Character Controls

A character LoRA handles identity. ControlNet can handle pose. Inpainting can fix a face or hand. A reference adapter can borrow a specific look for one session. You do not need one LoRA to solve every problem.

For a story sequence, build the scene in layers. Use the character LoRA at a moderate strength, ControlNet for pose, and inpainting for repair. Save the workflow and metadata for each approved frame. Consistency comes from repeatable process, not one heroic prompt.

## Next

Continue with [Practical Examples](practical-examples.md), [Advanced Techniques](advanced-techniques.md), or [Practical Training Projects](../loRA-training-101/practical-training-projects.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
