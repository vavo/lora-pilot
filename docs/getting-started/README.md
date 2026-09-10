# Getting Started

_Last updated: 2026-09-10_

You can begin making images before you know how to train a model. A downloaded base model gives you something to experiment with, and a small generation session gives you a reason to learn the controls. LoRA Pilot keeps the next stages nearby: preparing your own examples, training an adaptation, and comparing what it changes.

Start with the project you want to make. A character portrait, an illustration style, or a product scene gives you something concrete to judge. You can learn the underlying ideas as you work toward that result.

## Get a workspace you can return to

Read [system requirements](system-requirements.md) to understand the hardware and storage your deployment needs, then use the [installation guide](installation.md) for setup. The [first-run guide](first-run.md) takes you from opening ControlPilot to finding your first saved image.

If you use Docker Compose on a configured NVIDIA host, run the following from the directory where you want to keep the checkout. The final command starts the stack; it does not establish that each application has finished initializing.

```bash
git clone https://github.com/vavo/lora-pilot.git
cd lora-pilot
test -f .env || cp .env.example .env
docker compose -f docker-compose.yml up -d
```

If you already have a checkout and a configured environment, continue from that directory and preserve its settings. For an existing RunPod deployment, open the pod's ControlPilot connection instead of launching another container inside it. Check the storage attached to `/workspace` before you add files you intend to keep.

The repository also includes development and CPU Compose configurations. Use the [configuration guide](../configuration/README.md) to choose a mode that fits your task. CPU mode supports useful interface and debugging work, but it does not substitute for the GPU requirements of a training project.

## Learn through an image you can compare

Begin with [Stable Diffusion 101](stable-diffusion-101/README.md) for the relationship between a model, a prompt, and an image. Then open [What is Inference?](inference-101/what-is-inference.md) and try a basic workflow that your installed model supports.

Save one result with its settings. Change a single detail in the prompt and generate another version with the same seed where your workflow allows it. Compare the images at full size. You now have a specific observation to investigate, such as a changed background or a subject that no longer holds the same pose.

The [Inference 101 course](inference-101/README.md) explains the generation controls behind those experiments. Its [workflow types guide](inference-101/workflow-types.md) helps you decide whether to begin from text, use a reference image, or edit part of an existing result.

## Bring something of your own into the model

After a few generation sessions, you may want a subject or style that the base model does not produce consistently. That is a useful point to explore LoRA training. Read [What is LoRA Training?](loRA-training-101/what-is-loRA-training.md) to understand what an adaptation adds and how it relates to the base model.

Before running a trainer, work through [Datasets 101](datasets-101/README.md), starting with [what makes a good dataset](datasets-101/what-makes-a-good-dataset.md). You will choose examples, inspect their differences, and describe them with text that suits your training approach. Keep that first collection focused enough that you can review the images yourself.

Use [LoRA Training 101](loRA-training-101/README.md) to connect the prepared collection to a training run. The [practical training projects](loRA-training-101/practical-training-projects.md) give you a way to apply the concepts. Compare the resulting adaptation with the base model on prompts relevant to your project, then decide what to revise.

## Follow the question your project raises

Use the [user guide](../user-guide/README.md) for day-to-day work and the [component guides](../components/README.md) when you need to understand a particular tool. Keep [troubleshooting](troubleshooting.md) nearby for setup failures. If you need help from the community, describe what you attempted and include the relevant error in [GitHub Discussions](https://github.com/vavo/lora-pilot/discussions) or a reproducible report in [GitHub Issues](https://github.com/vavo/lora-pilot/issues).

You have a useful first milestone when you can make an image, find the saved file, and explain one change you made to improve the next version. From there, each new technique has a result to build on.
