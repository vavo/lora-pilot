# Practical Training Projects

_Last updated: 2026-07-06_

Training stops feeling mysterious after you run a few small projects and keep notes. The trick is to make each project teach one lesson. If you try to train a perfect character, style, product, and portfolio asset in the same first run, the failure report will read: "many things happened."

Use these walkthroughs as practice runs. They are not specs to complete for a grade. They are small loops: prepare a dataset, train, look at samples, change one thing, and learn what moved.

## Walkthrough 1: Your First Character LoRA

Start with a character only if you have permission to train that person or own the character design. For real people, use explicit consent and keep the dataset private unless the license or release allows sharing. This is not paperwork theater. A face LoRA can create images that look personal, plausible, and easy to misuse.

Choose 15 to 25 clear images of one character. You want the same identity across different crops, angles, expressions, and lighting. Avoid filling the folder with twenty versions of the same selfie. The trainer will treat repetition as importance, and it has no taste.

Open the set in TagPilot and review it as thumbnails. Cut blurry images, tiny faces, duplicate poses, watermarks, and anything that looks like a different person. Then caption the remaining images with one trigger word, such as `mychar_anna`, plus visible details you want to control later.

Example caption:

```text
photo of mychar_anna, woman with short red hair, black jacket, sitting at a cafe, warm indoor light
```

For the first run, use the boring settings from TrainPilot or Kohya. Batch size `1`, rank around `32`, and a modest step count are enough to learn the workflow. Save checkpoints and sample images during training. Your goal is not the final LoRA. Your goal is to find the first checkpoint where the trigger works without copying the dataset.

Test the same five prompts against several checkpoints. Include one close prompt, one new outfit, one new background, one new camera angle, and one prompt that should fail if the LoRA memorized too much. If the character only appears in the training jacket, you trained the jacket too.

Save the best checkpoint with a plain name:

```text
mychar_anna_sdxl_r32_step1200.safetensors
```

Write down the dataset version, base model, trigger, rank, learning rate, best checkpoint, and one sentence about the failure. That note matters more than the nice sample. It tells you what to change next time.

## Walkthrough 2: A Style LoRA That Escapes Its Subject

Style LoRAs fail in a different way. A character LoRA can overfit one face. A style LoRA can accidentally learn "portraits of women in blue light" when you meant "loose ink-and-watercolor."

Build a style dataset from 25 to 40 images that share the visual treatment but vary the subject. Use landscapes, objects, people, interiors, and close-ups if the style supports them. If every image is the same subject, the model may bind the subject to the style.

Caption the subject matter directly. The style should come from repetition across the set, while captions tell the trainer what each image depicts. A useful style caption sounds plain:

```text
inkwash_style illustration of a mountain village, loose brushwork, muted colors, paper texture
```

Train a normal LoRA first. Resist the urge to increase rank because the word "style" sounds artistic and therefore expensive. Rank `16` or `32` can teach plenty if the dataset is clean.

Test with subjects that were not in the dataset. If you trained on buildings and portraits, ask for a bicycle, a market stall, a bowl of fruit, and a spaceship. A good style LoRA carries brushwork, palette, texture, and composition habits into new subjects. A weak one drags the old subjects along.

When the style looks inconsistent, inspect the dataset before touching settings. You may have mixed two styles, overprocessed half the images, or captioned the style words differently across files. Settings can tune a signal. They cannot make a confused folder wise.

## Walkthrough 3: A Product LoRA for Reusable Marketing Images

Product training is less forgiving than style training because buyers notice shape errors. A backpack with the wrong zipper placement or a watch with impossible buttons stops being the product.

Collect 20 to 35 images that show the object from front, side, back, three-quarter, close-up, and in-use views. Include clean studio shots if you have them, then add a few real scenes so the object learns how it sits in the world. Keep the product readable in every image.

Caption view and context. Bind the product identity to a trigger such as `brandpack_v1`, but name details you may want to change later:

```text
studio photo of brandpack_v1 backpack, front view, black nylon, orange zipper pulls, white background
```

After training, test the LoRA in three groups. First, generate catalog prompts on plain backgrounds. Then generate lifestyle prompts in real settings. Finally, test prompts that stress the shape: side view, open pocket, hand holding product, product on table, product worn by person.

If the product identity breaks in lifestyle scenes, add more context images or lower LoRA strength during generation. If the product looks correct but the scene looks dull, your LoRA may be fine and your base prompt needs work. Do not retrain a model because one prompt had the charisma of wet cardboard.

## How to Review a Training Project

Judge a project from samples, not from optimism. Put the best checkpoint beside the previous checkpoint and use the same prompts. Look for identity, flexibility, artifacts, and prompt obedience.

A useful review note is short:

```text
Run: mychar_anna_sdxl_r32_v02
Best checkpoint: step 1200
Works: face identity, cafe/outdoor prompts, side view
Fails: black jacket repeats too often, teeth artifacts in close-ups
Next change: add 5 outfit-varied images, remove two blurry close-ups
```

That note gives the next run a reason. Without it, you are rerolling with extra steps and calling it research.

## Next

Use [Training Parameters Explained](training-parameters-explained.md) when a project underfits or overfits. Use [Troubleshooting Training](troubleshooting-training.md) when a run crashes or behaves strangely. Use [Is My LoRA Good?](is-my-lora-good.md) when you need a more systematic evaluation loop.

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
