# Dataset Validation and Testing

_Last updated: 2026-07-06_

Dataset validation asks one blunt question: should you spend GPU time on this folder yet?

Most bad training runs announce themselves before training starts. The clues are in the thumbnails, captions, filenames, rights notes, duplicate frames, wrong trigger words, and mismatched source images. You just have to look before the progress bar hypnotizes you.

## The Three-Pass Review

Use three passes before the first run. The visual pass looks at thumbnails, crops, blur, duplicates, and wrong images. The caption pass checks trigger words, visible details, and consistency. The training pass is a tiny run with saved samples and checkpoint comparison.

TagPilot handles the visual and caption passes well. TrainPilot or your chosen trainer handles the small run. MediaPilot helps compare outputs.

> **Why does this work?** You catch cheap mistakes while they are still cheap. Fixing a caption before training costs seconds. Discovering the same bad caption after a three-hour run costs patience and probably snacks.

## Visual Pass

Open the dataset as thumbnails. Do not start with full-size images. Thumbnail review shows whether the subject, style, or product is readable at a glance.

Cut blurry images, tiny subjects, repeated near-duplicates, watermarks, UI overlays, harsh compression artifacts, and crops that remove identity or product features. Cut the wrong person, wrong object, or wrong style. Cut images you cannot legally or ethically use. No model output is worth explaining that mess later.

For character datasets, scan for identity consistency. For style datasets, scan for subject variety. For product datasets, scan whether the product remains readable from each angle.

> **Try this variation:** Sort the images worst-to-best in TagPilot or Finder. Delete the bottom 20 percent. If that feels painful, move them to a `maybe/` folder and train without them first.

## Caption Pass

Search the captions for the trigger word. Every image containing the concept should have it. Every image without the concept should not.

Then check vocabulary. Use the same subject word across captions, keep the trigger spelling identical, match visible details to the image, remove cropped-out objects, delete auto-caption hallucinations, and stop repeated junk phrases from appearing in every file. Name details you want to control later.

For character LoRAs, caption outfit, pose, angle, expression, background, and lighting if you want those to vary later. For style LoRAs, caption the subject and scene so the style can detach from the content. For product LoRAs, caption view, context, and visible materials.

## File Pass

A simple image LoRA dataset should not require archaeology. Image and caption filenames should match. Extensions should follow the trainer's expectations. Critical paths should avoid spaces and strange shell-hostile characters. Raw sources should live outside the processed training images. External assets should have a `SOURCES.md` or `sources.csv`. TagPilot should load the folder without drama.

If a trainer cannot find images or captions, assume the path or naming convention is wrong before assuming the trainer is haunted.

## Pilot Run

Before a serious run, train a tiny test with a small step count, batch size `1`, the same base model you plan to use later, and sample prompts that include the trigger word. Include at least one prompt outside the dataset context. If a character only works in the exact training outfit and background, you have learned something useful before spending the evening on a doomed run.

The goal is not final quality. The goal is to confirm that the dataset activates, the trigger works, and the LoRA starts learning the right idea.

Stop and fix the dataset if samples ignore the trigger, copy one pose or background immediately, change identity between samples, contradict the captions, or learn artifacts faster than the concept.

## Reading the Pilot Result

The pilot result should answer a plain question: did the dataset teach the intended concept without copying the folder back at you? If thumbnail clarity fails, crop tighter or cut weak images. If variation fails, add useful angles, poses, contexts, or subjects. If trigger coverage fails, edit captions in TagPilot. If caption accuracy fails, remove hallucinated details. If rights notes are missing, add them or cut the images. If pilot samples copy instead of generalize, adjust the dataset before touching advanced settings.

## When More Data Is the Wrong Fix

Adding images helps when the dataset lacks coverage. It hurts when you add more weak images with the same problems.

Add data when a character lacks angles or expressions, a product lacks views or contexts, a style lacks subject variety, or the concept appears in too few situations. Cut data when images repeat the same pose, quality varies wildly, captions need excuses, source rights are unclear, or an image teaches a thing you do not want.

## Next

Continue with [Image LoRA Datasets](image-lora-datasets.md), [Video LoRA Datasets](video-lora-datasets.md), or [LoRA Training 101](../loRA-training-101/README.md).

---

## Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
