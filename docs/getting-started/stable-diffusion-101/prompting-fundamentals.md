# Prompting Fundamentals

Think of prompting like talking to a very talented but very literal artist. The more clearly and specifically you describe what you want, the better the results. This guide teaches you to speak AI's language fluently.

##  The Prompting Mindset

### Think Like a Director
Instead of just describing an image, imagine you're directing a photoshoot:
- **Who/What**: Main subject
- **Where**: Location and setting
- **How**: Style and mood
- **Details**: Specific elements to include

### Be Specific, Not Vague
```
Vague: "a person"
Specific: "a young woman with long brown hair, wearing a blue dress"

Vague: "a landscape"
Specific: "a mountain landscape at sunset, with pine trees and a lake"
```

---

##  Basic Prompt Structure

### The Formula
```
[Subject] [Action/Pose] [Setting/Background] [Style] [Quality Details]
```

### Breakdown of Components

#### Subject
- **Who/What**: Main focus of your image
- **Descriptors**: Age, appearance, clothing
- **Characteristics**: Unique features, personality

#### Action/Pose
- **What They're Doing**: Sitting, running, jumping
- **Pose Details**: How they're positioned
- **Interaction**: With objects or other subjects

#### Setting/Background
- **Location**: Where the scene takes place
- **Time/Weather**: Time of day, weather conditions
- **Environment**: Indoor/outdoor, specific place

#### Style
- **Art Style**: Photo, painting, cartoon, 3D
- **Artist Style**: Like famous artist's work
- **Mood**: Happy, dramatic, peaceful, mysterious

#### Quality Details
- **Technical**: Resolution, lighting, detail level
- **Artistic**: Composition, color scheme
- **Professional**: Commercial quality, masterpiece

---

##  Prompt Examples by Category

### Portrait Photography

#### Basic Portrait
```
photo of a woman, professional portrait, soft lighting, detailed eyes
```

#### Detailed Portrait
```
professional portrait of a 30-year-old woman with long auburn hair, wearing a navy blue business suit, sitting in a modern office with soft window lighting, sharp focus on eyes, high resolution, detailed skin texture
```

#### Environmental Portrait
```
environmental portrait of an elderly fisherman, weathered face, white beard, wearing a yellow raincoat, standing on a rocky coast during sunset, dramatic lighting, sea spray in air, professional photography
```

### Landscape Photography

#### Simple Landscape
```
beautiful landscape, mountains, lake, sunset
```

#### Detailed Landscape
```
epic mountain landscape, Swiss Alps, snow-covered peaks, crystal clear alpine lake reflecting mountains, golden hour lighting, dramatic clouds, ultra detailed, 8k resolution, professional photography
```

#### Atmospheric Landscape
```
misty forest at dawn, ancient oak trees, fog rolling between trees, sunbeams breaking through fog, mossy ground, peaceful atmosphere, fantasy style, detailed
```

### Artistic Styles

#### Oil Painting
```
oil painting of a ballerina, impressionist style, soft brushstrokes, pastel colors, elegant pose, detailed tutu, masterpiece
```

#### Anime/Manga
```
anime girl with silver hair, big blue eyes, wearing school uniform, cherry blossoms falling, studio ghibli style, detailed background, vibrant colors
```

#### Digital Art
```
digital art of a cyberpunk city, neon lights, flying cars, rainy streets, futuristic architecture, highly detailed, concept art style
```

### Fantasy and Sci-Fi

#### Fantasy Character
```
fantasy warrior woman, elven features, silver armor, glowing sword, enchanted forest, magical atmosphere, epic fantasy art, detailed
```

#### Sci-Fi Scene
```
spaceship interior, futuristic design, holographic displays, crew members working, blue ambient lighting, sci-fi movie style, cinematic
```

---

## ⚖️ Prompt Weighting

### What Is Prompt Weighting?

Prompt weighting tells the AI which parts of your prompt are more important. Think of it as emphasizing certain words.

### Weighting Syntax

#### Basic Emphasis
```
(word) = 1.1x weight
((word)) = 1.21x weight
(((word))) = 1.33x weight
```

#### De-emphasis
```
[word] = 0.9x weight
((word)) = 0.81x weight
```

#### Numerical Weighting
```
(word:1.5) = 1.5x weight
(word:0.5) = 0.5x weight
```

### Practical Weighting Examples

#### Emphasizing Subject
```
photo of ((beautiful woman)), detailed face, soft lighting
Result: Focus on "beautiful woman" aspect
```

#### Emphasizing Style
```
landscape, ((oil painting style)), vibrant colors
Result: Strong oil painting influence
```

#### De-emphasizing Elements
```
photo of a person, [blurry background], sharp focus
Result: Background less important than person
```

#### Complex Weighting
```
(((masterpiece))), photo of ((beautiful woman)) with ((long flowing hair)), [simple background], professional lighting
Result: Emphasis on quality, woman, and hair; less on background
```

---

## 🚫 Negative Prompts

### What Are Negative Prompts?

Negative prompts tell the AI what to AVOID. They're crucial for quality control and fixing common issues.

### Common Negative Prompt Elements

#### Quality Issues
```
blurry, low quality, distorted, deformed, ugly, bad anatomy, extra limbs, missing limbs, poorly drawn hands, poorly drawn feet
```

#### Style Issues
```
photo, realistic, 3d, render (if you want artistic style)
painting, drawing, cartoon (if you want photorealistic)
```

#### Content Issues
```
text, watermark, signature, username, logo, copyright, words, letters
jpeg artifacts, compression artifacts, noise, grain
```

#### Composition Issues
```
cropped, out of frame, cut off, bad composition, poorly framed, awkward angle
```

### Negative Prompt Examples

#### For Photorealism
```
Negative: cartoon, anime, painting, drawing, illustration, 3d, render, cgi
```

#### For Artistic Style
```
Negative: photo, realistic, photorealistic, detailed, sharp focus
```

#### For Quality
```
Negative: blurry, low quality, distorted, deformed, ugly, bad anatomy, extra fingers, missing limbs, poorly drawn hands, poorly drawn feet, jpeg artifacts, compression artifacts, noise, grain
```

#### For Clean Results
```
Negative: text, watermark, signature, username, logo, copyright, words, letters, border, frame
```

---

##  Advanced Prompting Techniques

### Step-by-Step Prompting

#### Start Simple, Add Complexity
```
Step 1: "photo of a woman"
Step 2: "photo of a woman, sitting"
Step 3: "photo of a woman, sitting in a cafe"
Step 4: "photo of a woman, sitting in a cafe, reading a book"
Step 5: "photo of a woman, sitting in a cafe, reading a book, soft lighting"
```

#### Benefits
- **See Progress**: Understand how each addition affects result
- **Debug Issues**: Identify which part causes problems
- **Learn Effects**: Understand how AI interprets elements
- **Build Confidence**: Start simple and gradually increase complexity

### Prompt Chaining

#### Sequential Generation
```
Image 1: "photo of a woman in a red dress"
Image 2: Use Image 1, prompt: "same woman, now in a blue dress"
Image 3: Use Image 2, prompt: "same woman, now in a green dress"
```

#### Benefits
- **Consistency**: Maintain character across changes
- **Iteration**: Build upon previous results
- **Control**: Make specific changes while keeping other elements

### Multi-Prompt Generation

#### Aspect Ratio Prompts
```
Portrait: "photo of a woman, portrait orientation, vertical composition"
Landscape: "photo of a woman, landscape orientation, horizontal composition"
Square: "photo of a woman, square composition, centered subject"
```

#### Style Variations
```
Same subject, different styles:
"photo of a woman, realistic style"
"painting of a woman, impressionist style"
"drawing of a woman, anime style"
"3d render of a woman, pixar style"
```

---

##  Model-Specific Prompting

### SD1.5 Prompting

#### Characteristics
- **Simple Prompts Work**: Less complex prompts needed
- **Keyword Focused**: Individual keywords have strong effect
- **Emphasis Important**: Weighting works well
- **Style Keywords**: Strong style word influence

#### SD1.5 Tips
```
Good: "photo of beautiful woman, detailed, high quality"
Better: "photo of ((beautiful woman)), ((detailed)), ((high quality))"

Good: "anime girl, colorful hair"
Better: "anime girl, ((vibrant colorful hair)), ((detailed eyes))"
```

### SDXL Prompting

#### Characteristics
- **Natural Language**: More sentence-like prompts work better
- **Complex Understanding**: Handles complex descriptions well
- **Less Emphasis Needed**: Natural weighting works well
- **Style Integration**: Better at blending styles

#### SDXL Tips
```
Good: "A professional portrait photograph of a woman with long brown hair, wearing a blue business suit, sitting in a modern office with soft window lighting"
Better: "A professional portrait photograph of a woman with long flowing brown hair, wearing a tailored navy blue business suit, sitting in a modern minimalist office with large windows casting soft natural light"
```

### FLUX.1 Prompting

#### Characteristics
- **Natural Language**: Most like human communication
- **Complex Sentences**: Handles long, detailed descriptions
- **Minimal Weighting**: Natural emphasis works best
- **Context Understanding**: Understands relationships between elements

#### FLUX.1 Tips
```
Good: "photo of a woman"
Better: "A photograph capturing a moment of a woman with a gentle smile, her hair catching the light as she stands in a sunlit garden"

Good: "fantasy landscape"
Better: "A breathtaking fantasy landscape where ancient stone towers rise from misty valleys, with waterfalls cascading down moss-covered cliffs under a dramatic sky filled with two moons"
```

---

##  Prompting Troubleshooting

### Common Issues and Solutions

#### AI Ignores Part of Prompt
```
Problem: "photo of woman with red hair" generates woman with brown hair
Solutions:
1. Use emphasis: "photo of woman with ((red hair))"
2. Separate: "photo of woman, red hair"
3. Be more specific: "photo of woman, vibrant red hair, clearly visible"
```

#### Results Look Blurry
```
Problem: Images consistently blurry or low quality
Solutions:
1. Add quality terms: "high quality, detailed, sharp focus"
2. Add negative: "blurry, low quality, out of focus"
3. Increase steps: Use 30-40 steps instead of 20
4. Check sampler: Try DPM++ instead of Euler
```

#### Wrong Style Generated
```
Problem: Want painting but get photo
Solutions:
1. Add style keywords: "oil painting, brushstrokes, artistic"
2. Add negative: "photo, realistic, photorealistic"
3. Emphasize style: "((oil painting style))"
4. Use style reference: Include style-specific terms
```

#### Extra Limbs or Deformations
```
Problem: People have extra fingers, missing limbs
Solutions:
1. Add negative: "extra limbs, missing limbs, deformed, bad anatomy"
2. Lower CFG: Try 7-10 instead of 15+
3. Use better model: SDXL or FLUX.1 handle anatomy better
4. Increase steps: More refinement helps fix anatomy
```

### Quality Improvement Checklist

#### Before Generating
- [ ] **Clear Subject**: Is your main subject clear?
- [ ] **Specific Details**: Have you included important details?
- [ ] **Style Words**: Have you specified desired style?
- [ ] **Quality Terms**: Have you included quality keywords?
- [ ] **Negative Prompt**: Have you specified what to avoid?

#### After Generating
- [ ] **Subject Correct**: Is main subject as expected?
- [ ] **Style Right**: Does it match desired style?
- [ ] **Details Present**: Are specific details included?
- [ ] **Quality Good**: Is image sharp and clear?
- [ ] **No Unwanted**: Are negative prompt elements avoided?

---

##  Prompting Practice Exercises

### Exercise 1: Subject Focus
```
Goal: Generate consistent subject across different styles
Steps:
1. Choose simple subject: "a cat"
2. Generate with different styles:
   - "photo of a cat"
   - "painting of a cat"
   - "cartoon of a cat"
   - "3d render of a cat"
3. Compare results and note differences
```

### Exercise 2: Detail Building
```
Goal: Build complex prompt step by step
Steps:
1. Start: "photo of a person"
2. Add: "photo of a person, sitting"
3. Add: "photo of a person, sitting in a park"
4. Add: "photo of a person, sitting in a park, reading"
5. Add: "photo of a person, sitting in a park, reading a book, soft lighting"
6. Compare each step's result
```

### Exercise 3: Style Mastery
```
Goal: Master one specific style
Steps:
1. Choose style: "cyberpunk"
2. Generate different subjects:
   - "cyberpunk street"
   - "cyberpunk character"
   - "cyberpunk vehicle"
   - "cyberpunk building"
3. Identify common elements that make it look cyberpunk
4. Create template for future cyberpunk prompts
```

### Exercise 4: Negative Prompt Practice
```
Goal: Learn to fix common issues with negative prompts
Steps:
1. Generate image with known issue (like extra fingers)
2. Add negative prompt targeting that issue
3. Regenerate and compare
4. Try different negative prompt combinations
5. Document what works best for each issue
```

---

##  What's Next?

Now that you understand prompting fundamentals, you're ready to:

1. **[Practical Examples](practical-examples.md)** - Try real-world projects
2. **[Character Consistency](character-consistency.md)** - Create consistent characters
3. **[Advanced Techniques](advanced-techniques.md)** - Master inpainting and more

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)


