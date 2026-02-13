# Inference Workflows

A repeatable process beats random trial-and-error every time.

## 6-Step Workflow

1. Pick your baseline checkpoint and preset
2. Generate a small batch with fixed seed(s)
3. Adjust one variable (prompt, LoRA weight, CFG, or steps)
4. Re-run and compare side by side
5. Lock winning settings into a named preset
6. Save final metadata with outputs

## Save Rules

- Save settings with clear names
- Keep the winning prompt and seed
- Keep one "known-good" starter setup untouched

## Quality Control Loop

- If results drift: go back to your starter setup
- If identity/style weak: adjust LoRA weight slightly
- If output overcooked: reduce CFG or steps

## Next

Continue to [Performance Optimization](performance-optimization.md).

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)

