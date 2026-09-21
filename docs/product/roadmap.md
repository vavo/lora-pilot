# Product roadmap

_Last updated: 2026-09-21_

LoRA Pilot should help you take a training experiment from prepared images to a result you can inspect, keep, and use again. This roadmap separates implemented source features from proposed work. It sets no release dates. The [ideas document](ideas.md) holds directions that need more investigation before they become implementation tasks.

## Implemented in source

You can prepare SDXL or FLUX.1 dev training in ControlPilot, retain an unfinished setup in your browser, and submit runs to a persistent serial queue. Each run keeps its configuration, logs, and output location. The global activity control follows managed training and model downloads across pages, while build diagnostics identify the source revision and provide a sanitized support summary.

The September 21 batch completes Q1, Q2, Q3, Q5, and V5 from the most recent quick-win and value-improvement selection. Those labels apply to that batch; earlier proposals reused the same labels for different features.

Q1 adds individual checkpoint downloads after a guided run finishes, including files saved before a failure or stop. Q2 adds explanations and next actions for recognized failures while keeping technical details accessible. Q3 shows elapsed time and preparation stages, with an approximate remaining time only when the trainer supplies enough recent progress. Q5 adds search, model-family and status filters, and pagination across saved training history.

V5 adds Storage under Manage. You can inspect category usage and review selected checkpoints, private dataset snapshots, or training caches from finished guided runs before permanent removal. Workload and file-change checks protect the operation. Original datasets, shared models, linked files, and run records remain outside this cleanup flow. General application caches and outputs from other tools appear in the overview but are not cleanup candidates.

Successful runs also support copying checkpoints into the shared LoRA library and generating a paired comparison in ComfyUI. The same prompt and seed help you inspect what the chosen LoRA changes. See [TrainPilot](../components/trainpilot.md) and [ControlPilot](../user-guide/control-pilot.md) for the current user flows.

## Verify the new image on target hardware

The September 21 implementation reached source commit `e70a86b`. Its local checks passed 229 Python tests and 8 frontend tests, with browser checks for downloads, history filters, timing, cleanup review, mobile layout, and both themes. Cleanup testing used disposable files. The local Docker build check could not connect to a running Docker daemon, and that implementation task did not publish a new image or validate training on a live GPU.

The next delivery milestone is a GitHub Actions image build followed by a rehearsal on a target pod. Record the registry digest and embedded commit, run a short training job, download its checkpoint, generate a comparison, and check restart recovery and cleanup with disposable data. A published image and a successful GPU workflow need separate evidence before marking this milestone complete.

## Finish control over model downloads

Download cancellation, the unselected Q4 from the September 21 batch, remains proposed. You should be able to stop waiting work or an active transfer, understand what partial data remains, and retry without damaging installed files. Completion should require tests for cancellation during queueing and transfer, shared download jobs, and service restart behavior.

## Review dataset quality before spending GPU time

Caption coverage already helps you find missing text files. A proposed dataset review would also identify unreadable images, exact duplicates, unusually small images, and caption mismatches before queueing. Start with a read-only report that takes you to the affected files. Define any repair actions separately so the first version cannot silently change a training dataset.

## Prove workflow readiness before launch

Model installation review checks required files and access. A proposed readiness check would bring those results together with the running ComfyUI node registry and relevant service versions for a selected bundled workflow. It should explain each missing requirement and offer a specific next step. A passing check would establish known prerequisites; a successful generation would still require a real GPU run.

## Keep the roadmap useful

Move a proposal into implementation only after selecting its scope. Record the resulting behavior, tests, and remaining limits when the work lands. Keep user instructions in the guides, completed change history in the [changelog](../reference/changelog.md), and exploratory directions in [ideas](ideas.md). This keeps an attractive proposal from turning into an accidental product promise.
