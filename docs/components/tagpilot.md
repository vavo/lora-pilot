# Caption images with TagPilot

_Last updated: 2026-09-23_

A training image tells the model what something looks like. Its caption helps explain what it is looking at. TagPilot brings those two parts together, so you can move from a folder of photos to a dataset you understand and trust.

Open **Caption images** under Prepare in ControlPilot. The workspace follows ControlPilot’s light or dark theme and keeps dataset actions, individual image tools, and export controls in one place. You can also open `/tagpilot/` directly on your ControlPilot address.

## Start with the images you already have

Choose **Add photos** to select PNG, JPEG, or WebP images. You can include matching `.txt` files in the same selection; `portrait.jpg` and `portrait.txt` belong together. **Import dataset ZIP** adds an existing collection with its text files. Both actions add to the current session and skip images whose contents are already present.

Opening a dataset from ControlPilot’s Datasets page loads its saved images and annotations. The direct equivalent is `/tagpilot/?dataset=1_my_dataset`. Files remain in the browser while you edit, and changes reach your workspace only when you choose **Save to workspace**.

The editor displays **50 images per page**. Page controls show the visible range and total image count. Moving between pages preserves your edits. Tag all, Caption all, trigger-word changes, the dataset tag viewer, saving, and exporting always operate on the complete collection.

## Give each image the right description

Every image has explicit **Tags** and **Caption** controls. These are two ways to edit the same annotation, rather than separate text files. Tags work well for concise descriptions such as clothing, lighting, or background. Caption mode gives you room for complete sentences.

Type a tag and press Enter or comma to add it. Remove a chip to delete that tag from the image. The **Dataset tag viewer** counts tags across images in tag mode; removing a tag there removes it from every tagged image after confirmation. Caption prose is not included in that frequency list.

The **Trigger word** field applies the chosen phrase across the dataset. Changing it replaces the previous trigger while keeping the remaining text. Use a distinctive phrase that you can later include in your generation prompt.

Choose **Preview image** for a larger view. Previous and Next buttons, or the left and right arrow keys, move through the entire dataset, including across page boundaries. Navigation stops at the first and last image. Escape closes the preview. **Crop** works from either the image row or the preview and uses the aspect ratio and output width chosen in TagPilot settings.

**Remove image** removes an image from the editing session. **Clear tags/captions** clears annotations while preserving the current trigger word. **Reset all** discards the session’s images, annotations, dataset name, and trigger after confirmation. These actions do not immediately delete saved workspace files; saving the edited dataset replaces the saved collection.

## Let a model make the first pass

**Tag image** and **Caption image** process a single image. **Tag all** and **Caption all** open a dialog showing the selected model, image count, text limit, and trigger word before work begins.

Choose **Skip existing** to process only images with no text or just the trigger word. **Append** adds generated text to existing annotations. **Overwrite** replaces them. During processing, the dialog shows progress and a Stop control. Stopping prevents subsequent images from starting; an in-flight provider request can still finish.

TagPilot supports Gemini, Grok, OpenAI, Claude, and OpenAI-compatible vLLM endpoints for tags and captions. DeepDanbooru and WD1.4 provide additional tagging options. WD1.4 uses a Replicate API key, while DeepDanbooru does not require a key.

## Set defaults once, then concentrate on the dataset

**TagPilot settings** opens a dedicated settings screen inside Caption images. Tagging and captioning have independent provider choices, limits, and system prompts. Crop settings control aspect ratio and width. The same screen exposes DeepDanbooru and WD1.4 thresholds, provider credentials, and the vLLM connection.

For vLLM or another OpenAI-compatible endpoint, enter the server URL and the exact model identifier it serves. Base URLs, `/v1`, and `/v1/chat/completions` URLs are accepted. Model presets fill the identifier field, which remains editable.

Choose **Save settings** to apply changes. Cancel, Close, or Back to Caption images discards unsaved settings changes without losing your dataset edits. Non-secret preferences persist in this browser. API keys entered in TagPilot remain only in the current page’s memory and are not written to browser storage; reloading the page clears them. Gemini, Grok, and OpenAI can also use credentials configured through ControlPilot’s server-side settings.

## Save a dataset you can train with

The **Dataset name** determines the ZIP filename and workspace save destination. **Export ZIP** downloads the complete collection with matching text files. **Save to workspace** writes the dataset beneath `/workspace/datasets`, using the existing `1_<name>` convention, and produces a ZIP copy under `/workspace/datasets/ZIPs`.

Changing the name before saving creates or updates that destination. It does not rename or remove a previously saved folder. Use the Datasets page when you need to manage the saved folder itself.

Edits are not automatically saved. Save or export before refreshing, leaving Caption images, or closing the browser. Once saved, the dataset is available to Guided training and the other training tools sharing your workspace.

## Integration and troubleshooting

ControlPilot serves TagPilot through its existing port, normally 7878. Loading uses `GET /api/tagpilot/load`; workspace saving streams files through `POST /api/tagpilot/save-item`. Gemini, Grok, and OpenAI generation uses `POST /api/tagpilot/generate`, which returns provider failures as structured API errors.

If loading or saving fails, check the ControlPilot service log and available workspace storage. If generation fails, check the selected provider, its credentials and quota, and the model’s availability to that account. For vLLM, also check that the endpoint is reachable and the model identifier matches the running server.

A provider smoke test is available inside the image as `/opt/pilot/tagpilot-provider-smoke.py --require-all`. It sends a tiny test image to configured OpenAI, Gemini, and Grok providers. Run it directly inside a RunPod pod. For a local checkout, the equivalent script is `scripts/tagpilot-provider-smoke.py`.

Continue with [Datasets 101](../getting-started/datasets-101/README.md), [training workflows](../user-guide/training-workflows.md), or [TrainPilot](trainpilot.md).
