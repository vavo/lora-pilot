# CUDA environments and bundled video workflows

Verified against upstream releases and Linux/Python 3.11 package metadata on
2026-09-05. Build with `make build CUDA_PROFILE=cu130` (default) or
`make build CUDA_PROFILE=cu128`. The Makefile selects matching NVIDIA base,
NVCC package and PyTorch wheel index. Passing only `CUDA_PROFILE` to a raw
`docker build` does not select the other arguments; mismatches fail the build.

| App | Pinned version | Environment | GPU stack |
| --- | --- | --- | --- |
| ComfyUI | 0.34.0 | core | Torch 2.11.0 / vision 0.26.0 / audio 2.11.0 / xFormers 0.0.35, selected CUDA profile |
| Kohya | 26.0.0 | kohya | Same GPU versions, independently installed |
| AI Toolkit | b36bb3998ae596a566d85513299696a3a78f0dcb | ai-toolkit | Same GPU versions, independently installed |
| InvokeAI | 6.14.0 | invoke | Torch 2.7.1 / vision 0.22.1 / xFormers 0.0.31.post1, CUDA 12.8 on both profiles |

[ComfyUI](https://github.com/Comfy-Org/ComfyUI/releases/tag/v0.34.0),
[InvokeAI](https://pypi.org/project/InvokeAI/6.14.0/), Manager 4.2.2 and
[Downloader](https://github.com/romandev-codex/ComfyUI-Downloader/commit/03146df738191004a8aad8264dca5c3530907f56)
already matched upstream and retain their pins. Updated
[Kohya](https://github.com/bmaltais/kohya_ss/releases/tag/v26.0.0) and
[AI Toolkit](https://github.com/ostris/ai-toolkit/commit/b36bb3998ae596a566d85513299696a3a78f0dcb).

Kohya preserves upstream Diffusers 0.32.2, Transformers 4.54.1 and Hub 0.34.3;
Gradio stays in the supported 5.x family. Its startup no longer installs
Transformers into core. TrainPilot launches the Kohya interpreter.

AI Toolkit preserves its upstream Git-pinned Diffusers, Transformers 5.5.3,
PEFT 0.18.1 and Hub 1.23.0. Two upstream ABI pins are adjusted for Torch 2.11:
[TorchAO 0.17.0](https://github.com/pytorch/ao/releases/tag/v0.17.0) and
[TorchCodec 0.11.1](https://github.com/meta-pytorch/torchcodec/releases/tag/v0.11.1).
Both come from the selected CUDA index. Native builds also probe the TorchAO
APIs used by Toolkit and the TorchCodec decoder import.

InvokeAI and AI Toolkit no longer inherit core site-packages. This increases
image size but isolates their CUDA libraries and conflicting Python packages.
Each service runs `pip check` after installation; core is checked after all
app installers have finished.

## Pre-installed ComfyUI workflows

Open **Workflows → LoRA Pilot** after starting ComfyUI:

- `video_ltx2_5_t2v.json`
- `video_ltx2_5_i2v.json`
- `video_minimax_h3_t2v.json`
- `video_minimax_h3_i2v.json`

These are the unmodified official local-generation editor workflows from
[Comfy-Org/workflow_templates](https://github.com/Comfy-Org/workflow_templates/tree/785127914ff0f5bddb38c5fbe20c96912e564d9b/templates).
All required node classes are native to ComfyUI 0.34.0; no additional video
custom-node repositories are needed. The bundled frontend supports their
subgraphs. Source revision, file hashes and upstream license live alongside
the JSON in `config/comfy-workflows`.

The first launch seeds `/workspace/apps/comfy/user/default/workflows/LoRA Pilot`.
Existing files are preserved, including user edits. Model weights are not baked
into the image: use each workflow's model download metadata and setup notes,
and supply your own image for I2V. These are local model workflows, not paid
partner/API nodes. Existing user-installed custom nodes remain user-managed;
the image bundles the latest Downloader and Manager pins listed above.

## Validation and remaining runtime check

Linux dependency resolution passed for ComfyUI/core (including Diffusion Pipe), Kohya and AI Toolkit on
both CUDA indexes, and InvokeAI on its CUDA 12.8 index. Workflow hashes,
subgraph links and native node coverage were checked against the pinned
ComfyUI source. These checks do not prove a Docker build or GPU generation.

The development host's Docker daemon was unavailable during this update.
After building on an NVIDIA host, run `/opt/pilot/gpu-smoke-test.sh` inside
each profile's image. It requires a real GPU and checks every installed venv,
CUDA matmul, cuDNN Conv3d and xFormers attention, plus service-specific imports.
Then load and run each workflow with its downloaded models. Full image build,
service UI startup and end-to-end video output remain to be verified there.
