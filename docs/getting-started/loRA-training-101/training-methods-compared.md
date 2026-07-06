# Training Methods Compared

_Last updated: 2026-07-06_

Most LoRA Pilot users should start with LoRA training. That is the boring answer, and it saves a lot of time.

DreamBooth, LyCORIS, full fine-tuning, diffusion-pipe experiments, and model-family-specific trainers all have a place. They are not equal starting points. The right method depends on what you need to reuse, how much hardware you have, and whether you want one small adapter or a whole changed model.

## The Short Decision

Use **LoRA** when you want a small reusable file for a character, style, product, outfit, object, or concept. Train it with TrainPilot, Kohya, or AI Toolkit depending on the model family.

Use **DreamBooth-style training** when you need stronger single-subject personalization and accept larger outputs and less flexibility.

Use **LyCORIS or LoKr-style variants** after a normal LoRA fails to hold the concept well enough. They can help, but they add complexity and can become rigid.

Use **full fine-tuning** only when you want to change the base model itself and have the data, hardware, time, and reason to justify it.

> **Why does this work?** Most custom visual tasks are narrow. You do not need to rewrite the base model's knowledge of the world to teach one face, jacket, product, or drawing style. A small adapter is enough when the base model already understands the surrounding visual language.

## Method Comparison

| Method | Output | Best For | Avoid When |
|---|---|---|---|
| LoRA | Small adapter | First training runs, reusable subjects, styles, products | You need to change the whole base model |
| DreamBooth-style | Larger personalized model or heavier adapter | One subject with high identity pressure | You need many mixable concepts |
| LyCORIS / LoKr | Advanced adapter | Concepts normal LoRA cannot hold | You are still learning basics |
| Full fine-tuning | Modified model | Broad domain shift | You have a small dataset or limited VRAM |

## LoRA: The Default Workhorse

LoRA keeps the base model intact and trains a compact adjustment. You can load it, unload it, combine it with another LoRA, change its strength, or share it as a small file.

Use LoRA for:

- character consistency
- product identity
- clothing or accessory reuse
- style transfer
- small concept training
- first experiments in TrainPilot or Kohya
- Flux/SDXL model-family adapters when the trainer supports them

The tradeoff is that LoRA depends on the base model. If the base model cannot draw the broader scene, your LoRA will not rescue it. A great character LoRA on a weak checkpoint still lives inside a weak checkpoint.

> **Try this variation:** Train one quick LoRA with a tiny dataset and fixed sample prompts. Then test the same LoRA at strengths `0.5`, `0.7`, `0.9`, and `1.0`. This teaches more than reading five method comparisons in a row.

## DreamBooth-Style Training

DreamBooth-style training pushes harder on personalization. It can work well for one subject, especially when identity matters more than mix-and-match flexibility.

Use it when:

- one person or subject must dominate the result
- file size matters less than identity pressure
- you do not need to stack several trained concepts
- your workflow or trainer recommends it for the model family

Avoid it when you want a library of small mixable assets. Three DreamBooth-style subjects are not as convenient as three LoRAs. The storage and workflow overhead becomes a hobby you did not request.

## LyCORIS, LoKr, and Related Variants

LyCORIS and LoKr-style methods are adapter variants that can capture some concepts differently from standard LoRA. AI Toolkit and other trainers may expose these choices for specific model families.

Try them only after you have a baseline LoRA on the same dataset. Otherwise you cannot tell whether the method helped or whether you changed five things and got lucky.

Use them when:

- standard LoRA underfits a complex concept
- character consistency remains weak after dataset cleanup
- the model family supports the method well
- you can compare outputs with the same prompts and seeds

Avoid them for your first run. A more advanced method does not fix a vague dataset.

## Full Fine-Tuning

Full fine-tuning changes more of the model. That gives you more power and more ways to waste compute.

Use it when:

- you have a large curated dataset
- the whole visual domain should change
- LoRAs are too narrow for the goal
- you can afford longer runs and larger artifacts
- you understand licensing and distribution consequences

For most LoRA Pilot users, full fine-tuning belongs later. It is a production choice, not a beginner rite of passage.

## Which Tool in LoRA Pilot?

**TrainPilot** is the easiest starting point for guided Kohya-based runs. Use it when you want a curated path and fewer exposed settings.

**Kohya SS** exposes the classic training controls. Use it when you need detailed parameter control or want to follow Kohya-specific guides.

**AI Toolkit** is useful for newer model families and Flux-style training workflows. Use it when the target model family expects that stack.

**Diffusion Pipe** is the experimental heavy-duty path. Use it when you know why you need it.

Prepare the dataset in **TagPilot** first. Review outputs in **MediaPilot** after training. That loop matters more than picking the fanciest training method.

## A Simple Rule

Run one normal LoRA first. Save samples and checkpoints. Test it with [Is My LoRA Good?](is-my-lora-good.md). Only switch methods after you know what failed:

- **Underfit**: train longer, improve captions, or adjust rank/learning rate.
- **Overfit**: test earlier checkpoints, reduce steps, improve dataset variety.
- **Wrong base model**: train against the model family you plan to use.
- **Weak method fit**: then consider DreamBooth-style, LyCORIS, LoKr, or full fine-tuning.

## Next

Continue with [Training Parameters Explained](training-parameters-explained.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
