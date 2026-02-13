# Performance Optimization

Goal: faster iteration without turning outputs into mush.

## Fast Wins

- Keep resolution moderate during exploration
- Use smaller preview batches first
- Avoid overstepping steps if quality has plateaued
- Keep the same model setup while testing; do not switch everything every run

## VRAM Stability Tips

- VRAM is your GPU memory.
- Reduce resolution before reducing model quality
- Lower batch size before changing everything else
- Close unrelated heavy services when testing

## Two-Phase Strategy

- Discovery phase: speed first, lower-cost settings
- Final phase: quality pass on selected prompts/seeds

## Sanity Rule

If you cannot reproduce a result, it is not optimized yet.

## Next

Continue to [Troubleshooting Inference](troubleshooting-inference.md).

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)

