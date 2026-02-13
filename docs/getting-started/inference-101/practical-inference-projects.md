# Practical Inference Projects

Three short projects to build inference intuition fast.

## Project 1: Controlled Portrait Iteration

- Goal: keep composition stable while improving quality
- Use fixed seed, one checkpoint, one LoRA
- Change only CFG and steps

Success criteria:
- Subject remains consistent
- Detail improves without heavy distortions

## Project 2: Style Transfer with One LoRA

- Goal: apply style without destroying structure
- Start with LoRA weight 0.7-0.8
- Adjust in small increments

Success criteria:
- Style is obvious
- Subject readability remains high

## Project 3: Prompt Robustness Test

- Goal: keep quality across 5 prompt variations
- Keep the same model setup for all runs
- Change prompt wording only

Success criteria:
- Quality is consistent across variations
- Failure cases are documented with settings

## Where to Go Next

- [Component Docs](../../components/README.md)
- [ComfyUI](../../components/comfyui.md)
- [InvokeAI](../../components/invokeai.md)
- [Troubleshooting](../troubleshooting.md)

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)

