# Image Collection Strategies

_Last updated: 2026-07-06_

Collecting images for a LoRA is not hoarding. It is casting. Every image you keep teaches the model what the subject, style, product, or concept is allowed to become.

The beginner instinct is to gather a huge folder and let training "figure it out." Training will figure something out. You may not like what it chooses.

## Start With the Job

Write one sentence before collecting:

> I want this LoRA to generate `____` across `____`.

For a character LoRA, that might mean: "I want this LoRA to generate the same woman across new outfits, poses, and lighting." For a product LoRA, it might be the same backpack across studio shots and outdoor scenes. A style LoRA needs the same ink-and-watercolor treatment across many subjects. A video LoRA may need a motion pattern to survive across short clips.

That sentence tells you what to vary and what to protect. For a character, identity stays stable while pose, crop, expression, outfit, and background vary. For a style, the style stays stable while subject matter varies. For a product, the product stays readable while angle, context, and lighting vary.

> **Why does this work?** The trainer learns from repeated patterns. If the repeated pattern is "same face in many contexts", you get identity. If the repeated pattern is "same background in every shot", you may train a background by accident. The dataset votes; the model counts votes without understanding your intention.

## Build a Candidate Pile, Then Cut It

Start with more images than you need, then remove the weak ones before captioning. For a first run, collect 30 to 60 candidates and open them in TagPilot or a file browser with large thumbnails. Sort them into `strong`, `usable`, and `cut`. Delete the obvious `cut` group before you write captions, then train the first small run from the strongest set.

Twenty sharp, varied images often beat a hundred mediocre ones. The mediocre images are not harmless. Blur, bad crops, harsh lighting, watermarks, odd hands, wrong objects, duplicate poses, and compression artifacts all become part of the lesson.

> **Try this variation:** In TagPilot, review only thumbnails first. If you cannot recognize the subject or style at thumbnail size, the trainer will also get a weak signal. Fix the crop, replace the image, or cut it.

## Character Datasets

For a character or real person, collect images that prove identity from several angles. Use front, three-quarter, side, closer crop, wider crop, different expressions, and different lighting. Avoid ten near-identical selfies unless you want a LoRA that knows one camera angle and panics outside it.

Good character datasets keep the face visible in most images, vary crops and poses, use clean lighting, and show a few backgrounds. Add outfit variety if clothing should change later. Keep identity consistent across the whole set, because the trainer will not know that two similar-looking people are not supposed to merge into one cursed average.

Cut images where the face is obscured, the subject is tiny, the crop removes important identity features, or another person looks too similar. If you train on photos of real people, read [Data Rights and Consent](data-rights-and-consent.md) before you start. Consent is not an optional metadata field.

## Style Datasets

For a style, the subject should vary. If every training image is a portrait, the model may learn "portrait" as part of the style. If every image has the same color palette, the model may refuse other colors later.

Good style datasets include multiple subjects, compositions, and lighting setups that share the same visual treatment. The repeated signal should be brushwork, line quality, color handling, materials, lens behavior, or composition rhythm.

Use captions to name the subject matter so the trainer can separate "what is depicted" from "how it is depicted." Style LoRAs go sideways when captions hide the subject and the model treats a repeated object as part of the style.

## Product and Object Datasets

Products and objects need clarity. Show the object from multiple angles, scales, and contexts. Include clean reference-like images and real-world scenes if you want both catalog and lifestyle prompts later.

Watch logos, trademark use, and client restrictions. If you are training on a real product, keep source notes and usage rights with the dataset. Your future self will not remember which batch came from a client folder and which batch came from a moodboard at 1:12 a.m.

## Video Datasets

Video LoRAs add time as a training signal. You are collecting frames, but the important lesson may be motion: a head turn, fabric movement, camera push, product spin, walk cycle, or style of transition.

Choose clips with stable framing and readable motion. Cut clips with heavy motion blur, hard scene cuts, random camera shake, or inconsistent subjects. Extract frames in a way that preserves the motion story without filling the dataset with duplicates.

For first experiments, train image LoRAs before video LoRAs unless the concept only makes sense in motion. Video training is not a gentle place to learn basic dataset hygiene.

## Rights and Sources

Use your own images, commissioned work with training rights, generated images you can reuse, public domain media, or licensed sources that allow your planned use. Google Images is a search engine, not a permission slip.

Keep a `SOURCES.md` or `sources.csv` next to the dataset. Record source URL, creator, license, download date, and restrictions. For Creative Commons and public domain media, tools such as [Creative Commons Search](https://search.creativecommons.org/) and [Openverse](https://openverse.org/) can help. Unsplash has its own [license terms](https://unsplash.com/license); read them instead of assuming "free" means "no constraints."

Read [Data Rights and Consent](data-rights-and-consent.md) for the longer version.

## Before Captioning

Before captioning, look at the folder once more and ask whether every image earns its place. The repeated pattern should match the thing you want to train, and the variation should match the prompts you want later. Remove duplicates and near-duplicates. Record rights and sources. Make sure TagPilot can load the folder cleanly.

If any of that sounds shaky, fix the folder before training. GPU time is a bad place to discover a lazy dataset.

## Next

Continue with [Captioning and Tagging](captioning-and-tagging.md), then [Image Processing and Preparation](image-processing-preparation.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
