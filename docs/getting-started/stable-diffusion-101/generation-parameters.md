# Generation Parameters

Think of generation parameters like camera settings on a professional camera. Just as a photographer adjusts aperture, shutter speed, and ISO, you'll adjust AI parameters to get the perfect image. This guide explains each parameter in simple terms.

## Beginner Terms (Before You Start)

- **Steps**: how many refinement passes the model runs
- **CFG**: how strongly the model follows your prompt
- **Sampler**: the method used to build the image
- **Scheduler**: timing strategy used by some samplers
- **Seed**: randomness number (same seed = similar result)

##  The Big Picture

Generation parameters control **how** the AI creates your image, not **what** it creates. Your prompt determines the content, but parameters determine the style, quality, and characteristics.

---

## 🎲 Seed (Randomness Control)

### What Is a Seed?

A seed is like a starting number for the AI's randomness. Same seed = same result (if everything else is identical).

### How Seeds Work

```
Seed 12345: Always creates the same cat image
Seed 67890: Always creates the same dog image
Seed -1 (Random): Creates different image each time
```

### When to Use Seeds

#### Use Fixed Seeds When:
- **Testing Changes**: You want to see how parameter changes affect the same image
- **Consistency**: Need the same image multiple times
- **Debugging**: Troubleshooting why something looks wrong
- **Iterative Improvement**: Gradually improving an image

#### Use Random Seeds When:
- **Exploring**: Want to see different possibilities
- **Creative Work**: Don't want to be constrained
- **Batch Generation**: Creating many different images
- **Inspiration**: Looking for unexpected results

### Practical Examples

#### Testing Parameters
```
Prompt: "beautiful landscape"
Seed: 12345
CFG: 7
Result: Landscape A

Now change CFG to 12, keep seed 12345:
Result: Landscape A with stronger prompt adherence
```

#### Creative Exploration
```
Prompt: "fantasy castle"
Seed: Random
Generate 10 different castles
Pick the best one and use its seed for variations
```

---

## 🎚️ CFG Scale (Prompt Adherence)

### What Is CFG Scale?

CFG (Classifier-Free Guidance) scale controls how strictly the AI follows your prompt. Think of it as "how much should I listen to the instructions?"

### How CFG Works

```
Low CFG (1-5): AI is creative, might ignore parts of your prompt
Medium CFG (7-12): Balanced creativity and prompt following
High CFG (13-20): AI strictly follows prompt, less creative
```

### CFG Scale Effects

#### Low CFG (1-5)
- **More Creative**: AI adds its own ideas
- **Less Predictable**: Results vary more
- **Artistic**: Good for creative exploration
- **Risk**: Might not follow your prompt exactly

**Good For:**
- Artistic experimentation
- When you want surprises
- Creative writing prompts
- Abstract art

#### Medium CFG (7-12)
- **Balanced**: Good mix of creativity and control
- **Reliable**: Follows prompt but adds creativity
- **Versatile**: Works for most situations
- **Recommended**: Starting point for most users

**Good For:**
- General use
- Most prompts
- Balanced results
- Everyday generation

#### High CFG (13-20)
- **Strict Control**: AI follows prompt very closely
- **Less Creative**: Less artistic interpretation
- **Predictable**: Similar results each time
- **Risk**: Can look artificial or over-processed

**Good For:**
- Technical illustrations
- Specific requirements
- When you need exact results
- Product visualization

### Practical Examples

#### Portrait Photography
```
Prompt: "professional portrait of a woman, soft lighting"
CFG 7: Natural, artistic portrait
CFG 12: Professional, follows all instructions
CFG 18: Very literal, might look stiff
```

#### Creative Art
```
Prompt: "dreamlike forest, magical atmosphere"
CFG 5: Very creative, might add unexpected elements
CFG 10: Balanced magic and forest
CFG 15: Strictly dreamlike forest, less creative
```

---

##  Samplers (Image-Building Methods)

### What Are Samplers?

Samplers are different methods the AI uses to turn random noise into an image. Think of them as different routes to the same destination.

### How Samplers Work

```
All samplers start with: Random noise
All samplers end with: Clean image
But they take different paths to get there
```

### Popular Samplers

#### DPM++ Family
- **DPM++ 2M**: Great balance of speed and quality
- **DPM++ SDE**: More creative, slightly slower
- **DPM++ 2M Karras**: Improved version, better quality

**Best For:**
- General use
- Balanced results
- Most situations
- Recommended starting point

#### Euler Family
- **Euler a**: Fast, good for quick previews
- **Euler**: Deterministic, consistent results
- **Euler ancestral**: More creative than regular Euler

**Best For:**
- Speed testing
- Quick iterations
- Consistent results
- When you need fast generation

#### DDIM (Denoising Diffusion Implicit Models)
- **Characteristics**: Deterministic, reliable
- **Speed**: Medium
- **Quality**: Good, consistent
- **Use Case**: When you want reproducible results

**Best For:**
- Testing and debugging
- Consistent series
- Reproducible work
- Technical applications

#### UniPC (Unified Predictor-Corrector)
- **Characteristics**: Fast, good quality
- **Speed**: Fast
- **Quality**: Very good for speed
- **Use Case**: When you want speed without sacrificing too much quality

**Best For:**
- Quick generation
- Balancing speed and quality
- Iterative work
- When time matters

#### LCM (Latent Consistency Models)
- **Characteristics**: Extremely fast
- **Speed**: Very fast (5-10x faster)
- **Quality**: Good for speed
- **Use Case**: Real-time or near real-time generation

**Best For:**
- Interactive applications
- Real-time generation
- Quick previews
- When speed is critical

### Sampler Recommendations

#### For Beginners
- **Start with DPM++ 2M**: Best all-around choice
- **Try Euler a**: For faster generation
- **Experiment**: Try different ones to see what you like

#### For Quality
- **DPM++ 2M Karras**: Excellent quality
- **DDIM**: Very consistent
- **DPM++ SDE**: More creative quality

#### For Speed
- **Euler a**: Fast and reliable
- **UniPC**: Fast with good quality
- **LCM**: Fastest possible

---

## ⏱️ Steps (Generation Detail)

### What Are Steps?

Steps control how many times the AI refines the image. More steps = more refinement, but with diminishing returns.

### How Steps Work

```
Step 1: Very blurry, basic shapes
Step 10: Getting clearer, main forms visible
Step 20: Clear image, most details present
Step 50: Slightly more detail than step 20
Step 100: Almost identical to step 50
```

### Step Count Guidelines

#### Low Steps (10-20)
- **Speed**: Very fast
- **Quality**: Basic, good enough for previews
- **Use Case**: Quick testing, iterations
- **Result**: Good but not detailed

**Good For:**
- Quick previews
- Testing ideas
- Batch generation
- When speed matters

#### Medium Steps (20-40)
- **Speed**: Medium
- **Quality**: Good, most details present
- **Use Case**: General use, balanced approach
- **Result**: Sweet spot for most models

**Good For:**
- Most situations
- Balanced quality and speed
- Everyday generation
- Recommended starting point

#### High Steps (40-100)
- **Speed**: Slow
- **Quality**: Maximum detail
- **Use Case**: Final images, when quality matters most
- **Result**: Best possible quality

**Good For:**
- Final artwork
- Print images
- Professional work
- When quality is priority

### Diminishing Returns

After about 30-40 steps, additional steps provide minimal improvement:
- **20 to 30 steps**: Noticeable improvement
- **30 to 50 steps**: Small improvement
- **50 to 100 steps**: Very minimal improvement

### Step Recommendations by Model

#### SD1.5
- **Recommended**: 20-30 steps
- **Maximum**: 50 steps (after that, minimal improvement)

#### SDXL
- **Recommended**: 25-40 steps
- **Maximum**: 60 steps

#### FLUX.1
- **Recommended**: 30-50 steps
- **Maximum**: 100 steps

---

##  Scheduler (Timing Control)

### What Are Schedulers?

Schedulers control the timing and pace of the denoising process. Think of them as different rhythms for the same dance.

### Popular Schedulers

#### DPMSolverMultistep
- **Characteristics**: Standard, reliable
- **Best For**: General use
- **Compatibility**: Works with most samplers
- **Recommendation**: Default choice for most users

#### EulerAncestralDiscrete
- **Characteristics**: More creative, stochastic
- **Best For**: Artistic work
- **Variation**: Creates more variety
- **Use Case**: When you want creative results

#### Karras
- **Characteristics**: Better for fine details
- **Best For**: High-detail work
- **Quality**: Excellent detail preservation
- **Use Case**: When fine details matter

#### DDIM
- **Characteristics**: Deterministic, reproducible
- **Best For**: Consistent results
- **Use Case**: When you need the same result multiple times

---

## 🌡️ Temperature (Randomness Control)

### What Is Temperature?

Temperature controls the randomness in the AI's decisions. Higher temperature = more random and creative, lower = more predictable.

### Temperature Effects

#### Low Temperature (0.5-0.8)
- **Predictable**: Follows patterns it knows
- **Conservative**: Safer, less surprising results
- **Reliable**: Similar results each time
- **Risk**: Can be boring or repetitive

#### Medium Temperature (0.8-1.2)
- **Balanced**: Good mix of predictability and creativity
- **Versatile**: Works for most situations
- **Recommended**: Starting point for most users

#### High Temperature (1.2-2.0)
- **Creative**: More unexpected and novel results
- **Surprising**: Can create unique combinations
- **Risk**: Can be unpredictable or chaotic
- **Use Case**: Creative exploration

---

##  Parameter Combinations

### Beginner-Friendly Combinations

#### Safe Starting Point
```
Model: SD1.5
Sampler: DPM++ 2M
Steps: 25
CFG: 7
Seed: Random
Result: Reliable, good quality images
```

#### Quality Focus
```
Model: SDXL
Sampler: DPM++ 2M Karras
Steps: 40
CFG: 10
Seed: Random
Result: High quality, professional images
```

#### Speed Focus
```
Model: SD1.5
Sampler: Euler a
Steps: 15
CFG: 7
Seed: Random
Result: Fast generation, decent quality
```

### Advanced Combinations

#### Artistic Exploration
```
Model: SDXL
Sampler: DPM++ SDE
Scheduler: EulerAncestralDiscrete
Steps: 50
CFG: 5
Temperature: 1.2
Result: Very creative, artistic images
```

#### Technical Precision
```
Model: FLUX.1 Schnell
Sampler: DPM++ 2M Karras
Scheduler: Karras
Steps: 30
CFG: 15
Temperature: 0.8
Result: Precise, detailed technical images
```

#### Consistency Testing
```
Model: Any
Sampler: DDIM
Scheduler: DDIM
Steps: 30
CFG: 10
Seed: Fixed (same each time)
Result: Identical images for testing
```

---

## 💡 Practical Tips

### Start Simple
- **Use Defaults**: Most models have good default parameters
- **Change One Thing**: Adjust one parameter at a time
- **Learn Effects**: Understand what each parameter does

### Test Systematically
- **Parameter Grids**: Test different combinations
- **Keep Notes**: Remember what works for your style
- **Save Good Settings**: Reuse successful combinations

### Understand Trade-offs
- **Speed vs Quality**: Faster usually means lower quality
- **Control vs Creativity**: More control = less creativity
- **Consistency vs Variety**: Fixed seeds = consistency

### Model-Specific Optimization
- **SD1.5**: Works well with lower steps (20-25)
- **SDXL**: Benefits from more steps (30-40)
- **FLUX.1**: Needs more steps for best quality (30-50)

##  Troubleshooting Parameters

### Common Issues

#### Images Look Blurry
- **Increase Steps**: Try 30-40 steps instead of 20
- **Check Sampler**: Some samplers produce blurrier results
- **Adjust CFG**: Too high or too low can cause blur

#### Images Look Over-Processed
- **Lower CFG**: Try 7-10 instead of 15+
- **Reduce Steps**: 50+ steps can over-process
- **Change Sampler**: Some samplers are more aggressive

#### Results Are Too Random
- **Use Fixed Seed**: Test with same seed
- **Lower Temperature**: Reduce randomness
- **Lower CFG**: More prompt adherence

#### Results Are Too Boring
- **Increase Temperature**: Add more randomness
- **Use Creative Sampler**: Try DPM++ SDE
- **Lower CFG**: Allow more creativity

##  What's Next?

Now that you understand parameters, you're ready to:

1. **[Prompting Fundamentals](prompting-fundamentals.md)** - Learn to write better prompts
2. **[Advanced Techniques](advanced-techniques.md)** - Master inpainting and more
3. **[Practical Examples](practical-examples.md)** - Try real-world projects

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)

