# Practical Examples

_Last updated: 2026-07-06_

Examples teach best when you can compare the result before and after one change. A gallery of perfect prompts looks impressive and teaches almost nothing. A small grid that shows how lighting, denoise, seed, or LoRA strength changes an image teaches fast.

This page gives you mini-labs for common Stable Diffusion work. Each one has a prompt path and a suggested screenshot grid. The screenshots are not in the repo yet; the notes mark good places to add them later.

## Mini-Lab 1: Portrait Lighting

Start with a plain portrait prompt:

```text
photo portrait of a woman, neutral background, sharp focus
```

Use one model and keep the seed fixed. Generate the prompt once with soft window light, once with dramatic side light, once with overcast outdoor light, and once with studio rim light. Do not change hair, clothing, camera lens, or style words yet. You want the grid to show lighting, not a soup of unrelated changes.

Suggested screenshot grid:

| Soft Window | Side Light | Overcast | Rim Light |
|---|---|---|---|
| image slot | image slot | image slot | image slot |

After you make the grid, look at shadows around the nose, cheekbones, eyes, and neck. The model may change face shape while trying to obey lighting. That is a useful warning for character work: lighting words can move identity.

Then add a negative prompt only if the first grid shows a specific problem:

```text
blurry, low quality, jpeg artifacts, distorted hands
```

Negative prompts work best as cleanup notes. When they become a giant legal contract against ugliness, they often waste space and hide the real issue.

## Mini-Lab 2: Landscape Atmosphere

Use a simple landscape prompt:

```text
mountain lake at sunset, pine forest, calm water, wide angle landscape photo
```

Generate a baseline, then change only the atmosphere. Try misty dawn, storm clouds, clear noon, and golden hour. Keep the same seed if your tool allows it.

Suggested screenshot grid:

| Baseline | Mist | Storm | Golden Hour |
|---|---|---|---|
| image slot | image slot | image slot | image slot |

This lab shows how much the model packs into one atmosphere phrase. "Storm clouds" can change color, contrast, composition, and camera exposure. "Misty dawn" can soften edges and hide detail. If you are building a series, atmospheric consistency may matter as much as the subject.

## Mini-Lab 3: Style Without Losing the Subject

Pick one subject and run it through several styles:

```text
small red bicycle leaning against a brick wall
```

Try photorealistic product photo, watercolor sketch, oil painting, anime background art, and cyberpunk concept art. Keep the subject phrase identical.

Suggested screenshot grid:

| Photo | Watercolor | Oil | Anime | Cyberpunk |
|---|---|---|---|---|
| image slot | image slot | image slot | image slot | image slot |

A good style change preserves the bicycle. A bad one turns the bicycle into a decorative rumor. If the subject keeps mutating, reduce style pressure, choose a stronger base model for the subject, or use image-to-image with lower denoise.

## Mini-Lab 4: Character Consistency Without Training

Before training a character LoRA, test what you can get from prompt discipline and seeds. Create a short character brief:

```text
Aria, young elf woman, long silver hair, bright blue eyes, leather armor, calm expression
```

Use that brief in three prompts: a portrait, a forest scene, and a campfire scene. Keep the seed fixed for the first pass, then vary the seed for the second pass.

Suggested screenshot grid:

| Prompt | Fixed Seed | New Seed |
|---|---|---|
| portrait | image slot | image slot |
| forest | image slot | image slot |
| campfire | image slot | image slot |

This grid tells you whether a LoRA is worth training. If the character collapses as soon as the scene changes, training or a reference workflow may help. If prompt-only consistency is good enough for the project, skip training and spend the time on better art direction. Heroic restraint, rare in this industry.

## Mini-Lab 5: Product Angles

Use one product phrase:

```text
studio product photo of a black smartwatch with metal frame and glass display
```

Generate front view, side view, three-quarter view, on wrist, and on desk. Keep lighting and background stable.

Suggested screenshot grid:

| Front | Side | Three-Quarter | On Wrist | On Desk |
|---|---|---|---|---|
| image slot | image slot | image slot | image slot | image slot |

If the watch shape changes across views, a plain prompt is not enough. Use a reference image, ControlNet, image-to-image, or a product LoRA depending on how repeatable the product needs to be.

## Mini-Lab 6: Denoise in Image-to-Image

Take one generated image or sketch into image-to-image. Use the same prompt and seed, then render at denoise values around `0.25`, `0.45`, `0.65`, and `0.85`.

Suggested screenshot grid:

| Source | 0.25 | 0.45 | 0.65 | 0.85 |
|---|---|---|---|---|
| image slot | image slot | image slot | image slot | image slot |

Low denoise preserves structure and changes surface details. High denoise lets the model rebuild the image. This one grid explains why image-to-image feels either stubborn or chaotic depending on the slider.

## Saving Example Results

When you add screenshots later, save the prompt, seed, model, sampler, steps, CFG, dimensions, LoRA names, and denoise value beside the image. MediaPilot can help compare outputs, but the docs should show enough metadata that a reader understands the difference between examples.

Use small, labeled grids. A beginner should see the relationship in one glance: same prompt, one changed variable, visible result.

## Next

Continue with [Generation Parameters](generation-parameters.md), [Character Consistency](character-consistency.md), or [Advanced Techniques](advanced-techniques.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
