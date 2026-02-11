# Practical Examples

Time to put your knowledge into practice! These real-world projects will help you master Stable Diffusion through hands-on experience.

## 🎯 Project-Based Learning

Each project teaches specific skills:
- **Beginner Projects**: Build confidence with simple creations
- **Intermediate Projects**: Combine techniques for complex results
- **Advanced Projects**: Professional-level workflows
- **Portfolio Projects**: Create work you can showcase

---

## 🌅 Beginner Projects

### Project 1: Portrait Photography

#### Goal
Create professional-looking portraits with consistent quality

#### What You'll Learn
- Basic prompting structure
- Portrait-specific techniques
- Quality control with negative prompts
- Parameter optimization for portraits

#### Step-by-Step Guide

##### Step 1: Model Selection
```
Recommended Models:
- SD1.5: Fast, good for learning
- SDXL: Higher quality, more realistic
- FLUX.1 Schnell: Best quality with reasonable speed
```

##### Step 2: Basic Portrait
```
Prompt: "photo of a woman, professional portrait, soft lighting"
Negative: "blurry, low quality, distorted"
Settings:
- Model: SDXL Base
- Sampler: DPM++ 2M
- Steps: 25
- CFG: 8
- Seed: Random
```

##### Step 3: Add Specific Details
```
Prompt: "photo of a 30-year-old woman with long brown hair, professional portrait, soft window lighting, detailed eyes, sharp focus"
Negative: "blurry, low quality, distorted, bad anatomy, extra limbs"
Settings: Same as above
```

##### Step 4: Style Variation
```
Try different styles:
1. "photo of woman, black and white portrait, dramatic lighting"
2. "photo of woman, vintage style, 1940s look"
3. "photo of woman, environmental portrait, outdoor setting"
```

##### Step 5: Quality Refinement
```
Improve results with:
1. Better negative prompts: "jpeg artifacts, compression artifacts, noise"
2. Quality terms: "high resolution, detailed skin texture, professional photography"
3. Parameter tuning: Adjust CFG (7-12) and steps (20-40)
```

#### Expected Results
- Professional-looking portraits
- Consistent quality across variations
- Understanding of how different elements affect results

#### Troubleshooting Tips
- **Blurry results**: Increase steps, add "sharp focus"
- **Unrealistic skin**: Add "detailed skin texture"
- **Poor lighting**: Specify lighting direction and quality

---

### Project 2: Landscape Creation

#### Goal
Create beautiful, detailed landscape images

#### What You'll Learn
- Landscape composition
- Atmospheric effects
- Color and lighting control
- Different landscape styles

#### Step-by-Step Guide

##### Step 1: Basic Landscape
```
Prompt: "beautiful landscape, mountains, lake, sunset"
Negative: "blurry, low quality, oversaturated"
Settings:
- Model: SDXL Base
- Sampler: DPM++ 2M Karras
- Steps: 30
- CFG: 9
```

##### Step 2: Add Specific Elements
```
Prompt: "epic mountain landscape, Swiss Alps, snow-covered peaks, crystal clear alpine lake, golden hour lighting, dramatic clouds"
Negative: "blurry, low quality, oversaturated, cartoon"
```

##### Step 3: Atmospheric Effects
```
Add atmosphere:
1. "misty forest at dawn, fog rolling between trees"
2. "dramatic storm clouds over ocean, lightning in distance"
3. "autumn forest, golden leaves falling, soft sunlight"
```

##### Step 4: Style Variations
```
Try different artistic styles:
1. "landscape, oil painting style, impressionist, vibrant colors"
2. "landscape, fantasy style, magical atmosphere"
3. "landscape, photorealistic, national geographic style"
```

#### Expected Results
- Various landscape styles
- Understanding of atmospheric elements
- Composition and color control

---

### Project 3: Art Style Exploration

#### Goal
Create images in different artistic styles

#### What You'll Learn
- Style-specific prompting
- Art history terminology
- Style blending techniques
- Quality vs style balance

#### Step-by-Step Guide

##### Step 1: Oil Painting Style
```
Prompt: "oil painting of flowers in vase, impressionist style, soft brushstrokes, vibrant colors"
Negative: "photo, realistic, sharp, detailed"
Settings:
- Model: SD1.5 (good for artistic styles)
- Sampler: Euler a (good for artistic results)
- Steps: 30
- CFG: 7-8 (lower for creativity)
```

##### Step 2: Watercolor Style
```
Prompt: "watercolor painting of landscape, soft edges, flowing colors, paper texture"
Negative: "oil painting, thick brushstrokes, sharp edges"
```

##### Step 3: Anime/Manga Style
```
Prompt: "anime girl with silver hair, big blue eyes, school uniform, cherry blossoms, studio ghibli style"
Negative: "realistic, photo, 3d, detailed"
```

##### Step 4: Digital Art Style
```
Prompt: "digital art of cyberpunk city, neon lights, concept art style, highly detailed"
Negative: "painting, drawing, traditional art"
```

#### Expected Results
- Understanding of different artistic styles
- Style-specific vocabulary
- Ability to achieve desired artistic effects

---

## 🎨 Intermediate Projects

### Project 4: Character Design Series

#### Goal
Create consistent character across multiple images and situations

#### What You'll Learn
- Character consistency techniques
- Multi-pose generation
- Character + environment integration
- Storytelling through images

#### Step-by-Step Guide

##### Step 1: Character Concept
```
Character Brief:
- Name: "Aria"
- Age: 25
- Appearance: Silver hair, blue eyes, elven features
- Style: Fantasy adventurer
- Clothing: Leather armor, enchanted sword
```

##### Step 2: Base Character Portrait
```
Prompt: "fantasy portrait of Aria, young elf woman with long silver hair, bright blue eyes, wearing leather armor, detailed fantasy art, masterpiece"
Negative: "blurry, low quality, deformed, bad anatomy"
Settings:
- Model: SDXL Base
- Sampler: DPM++ 2M
- Steps: 40
- CFG: 10
- Seed: Fixed (for consistency)
```

##### Step 3: Character in Different Poses
```
Keep same seed, change pose descriptions:
1. "Aria standing in forest, hand on sword hilt"
2. "Aria sitting by campfire, sharpening sword"
3. "Aria in battle stance, sword drawn"
4. "Aria looking at ancient map, thoughtful expression"
```

##### Step 4: Character + Environment
```
Integrate character into environments:
1. "Aria in enchanted forest, magical atmosphere"
2. "Aria in ancient ruins, dramatic lighting"
3. "Aria on mountain peak, epic fantasy landscape"
```

##### Step 5: Action Scenes
```
Dynamic action poses:
1. "Aria casting spell, magical energy around hands"
2. "Aria fighting dragon, epic battle scene"
3. "Aria discovering ancient artifact, magical glow"
```

#### Expected Results
- Consistent character across all images
- Character integration with different environments
- Dynamic action and expression variety

---

### Project 5: Product Visualization

#### Goal
Create professional product images for commercial use

#### What You'll Learn
- Product photography techniques
- Lighting and material description
- Background and context integration
- Commercial quality standards

#### Step-by-Step Guide

##### Step 1: Product Selection
```
Example Product: "Smart watch"
Key Features:
- Sleek design
- Metal and glass materials
- Digital display
- Modern technology
```

##### Step 2: Studio Product Shot
```
Prompt: "product photography of smart watch, studio lighting, white background, professional commercial photography, sharp focus, detailed materials"
Negative: "blurry, low quality, shadows, reflections, distracting elements"
Settings:
- Model: SDXL Base
- Sampler: DPM++ 2M Karras
- Steps: 35
- CFG: 8
```

##### Step 3: Lifestyle Product Shot
```
Prompt: "product photography of smart watch, on person's wrist, outdoor setting, lifestyle photography, natural lighting, professional quality"
Negative: "blurry, low quality, distracting background, poor lighting"
```

##### Step 4: Multiple Angles
```
Create product from different angles:
1. "smart watch, front view, studio lighting"
2. "smart watch, side view, showing profile"
3. "smart watch, back view, showing buttons"
4. "smart watch, angled view, 45 degrees"
```

##### Step 5: Context Product Use
```
Show product in use scenarios:
1. "smart watch on athlete's wrist, during workout"
2. "smart watch in office setting, professional use"
3. "smart watch during evening activity, elegant lighting"
```

#### Expected Results
- Professional product photography
- Multiple angles and contexts
- Commercial-quality images

---

### Project 6: Story Illustration

#### Goal
Create a series of images that tell a story

#### What You'll Learn
- Narrative sequencing
- Mood and atmosphere control
- Character development across images
- Visual storytelling techniques

#### Step-by-Step Guide

##### Step 1: Story Concept
```
Story: "The Last Library"
Plot: Young woman discovers magical library in abandoned building
Characters:
- Protagonist: "Elena", curious scholar
- Setting: Ancient, magical library
- Mood: Mysterious, wonderous
```

##### Step 2: Scene 1 - Discovery
```
Prompt: "fantasy illustration, young woman discovering hidden library, ancient books floating, magical glow, mysterious atmosphere, detailed fantasy art"
Negative: "bright, cheerful, modern, cartoon"
Settings:
- Model: SDXL Base
- Sampler: DPM++ SDE (more creative)
- Steps: 40
- CFG: 9
```

##### Step 3: Scene 2 - First Magic
```
Prompt: "fantasy illustration, Elena reading glowing book, magical energy swirling around her, ancient library, warm lighting, detailed fantasy art"
```

##### Step 4: Scene 3 - Revelation
```
Prompt: "fantasy illustration, Elena looking up in awe, massive magical portal opening in library, ancient symbols floating, dramatic lighting, epic fantasy art"
```

##### Step 5: Scene 4 - Transformation
```
Prompt: "fantasy illustration, Elena being transformed by magic, glowing energy surrounding her, books flying around, portal swirling, magical transformation scene, detailed fantasy art"
```

#### Expected Results
- Narrative sequence
- Consistent character and setting
- Progressive story development
- Atmospheric consistency

---

## 🚀 Advanced Projects

### Project 7: Professional Character Creation

#### Goal
Create professional-grade character with LoRA training

#### What You'll Learn
- LoRA training process
- Character consistency at professional level
- Advanced prompting techniques
- Professional workflow optimization

#### Step-by-Step Guide

##### Step 1: Character Design
```
Professional Character Brief:
- Name: "Zara"
- Role: Sci-fi protagonist
- Appearance: Distinctive features, memorable design
- Style: Consistent visual identity
- Usage: Multiple media formats
```

##### Step 2: Reference Collection
```
Gather 20-30 reference images:
- Front views (5 images)
- Side views (3 images each)
- Back views (2 images)
- Expressions (5 images)
- Poses (5-10 images)
- Different lighting (3-5 images)
```

##### Step 3: LoRA Training
```
Training Setup:
- Base Model: SDXL Base
- Training Images: 25 high-quality images
- Trigger Word: "Zara_character"
- Training Steps: 1500
- Learning Rate: 1e-4
- Network Dim: 64
```

##### Step 4: Testing and Refinement
```
Test trained LoRA:
1. "photo of Zara_character, professional portrait"
2. "Zara_character in cyberpunk city, neon lighting"
3. "Zara_character as action hero, dynamic pose"
4. "Zara_character in different outfits"
```

##### Step 5: Professional Portfolio
```
Create portfolio pieces:
1. Character sheet (multiple poses)
2. Action scenes
3. Environmental portraits
4. Style variations
```

#### Expected Results
- Professional character consistency
- Custom LoRA for repeated use
- Portfolio-ready character images

---

### Project 8: Complex Scene Composition

#### Goal
Create complex, multi-element scenes with precise control

#### What You'll Learn
- ControlNet usage
- Multi-element composition
- Advanced lighting techniques
- Professional scene staging

#### Step-by-Step Guide

##### Step 1: Scene Planning
```
Complex Scene: "Futuristic Market Place"
Elements:
- Multiple characters (3-4)
- Architecture and environment
- Lighting and atmosphere
- Multiple focal points
```

##### Step 2: Base Composition
```
Use ControlNet for layout:
1. Sketch basic composition
2. Use ControlNet pose for main characters
3. Use ControlNet depth for spatial relationships
4. Use ControlNet edges for architectural elements
```

##### Step 3: Layered Generation
```
Generate scene in layers:
1. Background layer (architecture)
2. Middle ground (secondary elements)
3. Foreground (main characters)
4. Atmospheric effects (lighting, weather)
```

##### Step 4: Integration and Refinement
```
Combine and refine:
1. Use inpainting to blend layers
2. Adjust lighting consistency
3. Add fine details and textures
4. Final color correction
```

#### Expected Results
- Professional complex scene
- Multiple elements working together
- Advanced composition control

---

## 🎯 Portfolio Development

### Project 9: Themed Portfolio

#### Goal
Create a cohesive portfolio showcasing your skills

#### What You'll Learn
- Portfolio curation
- Style consistency
- Presentation skills
- Professional workflow

#### Step-by-Step Guide

##### Step 1: Theme Selection
```
Portfolio Theme Options:
1. "Fantasy Characters and Worlds"
2. "Sci-Fi Concepts and Designs"
3. "Portrait Photography Mastery"
4. "Landscape and Atmosphere"
```

##### Step 2: Portfolio Planning
```
Plan portfolio structure:
1. Cover piece (most impressive)
2. Character studies (3-5 images)
3. Environment scenes (2-3 images)
4. Technical demonstrations (2-3 images)
5. Style variations (2-3 images)
```

##### Step 3: Creation Pipeline
```
Systematic creation:
1. Create all base images
2. Ensure consistent quality
3. Apply post-processing if needed
4. Organize and label files
```

##### Step 4: Presentation
```
Professional presentation:
1. Consistent naming convention
2. Portfolio website/mockup
3. Artist statement and descriptions
4. Technical details and settings
```

#### Expected Results
- Professional portfolio
- Demonstrated skill range
- Consistent quality and style

---

## 💡 Project Tips and Best Practices

### General Project Management

#### Planning Phase
- **Clear Goals**: Know what you want to achieve
- **Reference Collection**: Gather inspiration and references
- **Technical Planning**: Choose appropriate models and settings
- **Time Management**: Allow adequate time for each phase

#### Execution Phase
- **Iterative Approach**: Build complexity gradually
- **Documentation**: Record successful settings and prompts
- **Quality Control**: Regularly check results against goals
- **Backup Important**: Save successful generations

#### Refinement Phase
- **Critical Evaluation**: Honestly assess results
- **Iterative Improvement**: Make incremental changes
- **Peer Feedback**: Get opinions from others
- **Final Polish**: Ensure professional presentation

### Technical Best Practices

#### Model Selection
- **Match Model to Project**: Use appropriate model for each task
- **Consistency**: Use same model across related images
- **Quality vs Speed**: Balance based on project needs
- **Experimentation**: Try different models to find best fit

#### Parameter Optimization
- **Start with Defaults**: Use recommended settings as baseline
- **Systematic Testing**: Change one parameter at a time
- **Documentation**: Record what works for each situation
- **Quality Monitoring**: Regularly check output quality

#### Workflow Efficiency
- **Batch Processing**: Generate multiple variations when possible
- **Template Creation**: Save successful prompt structures
- **Resource Management**: Monitor GPU memory and generation time
- **Backup Strategies**: Save important models and settings

---

## 🚀 What's Next?

After completing these projects, you'll have:

1. **Solid Foundation**: Understanding of all basic techniques
2. **Practical Experience**: Real-world project completion
3. **Portfolio Material**: Professional-quality images
4. **Advanced Skills**: Ready for complex projects

You're now ready to:

1. **[Model Management](../../user-guide/model-management.md)** - Organize your growing collection
2. **[Training Workflows](../../user-guide/training-workflows.md)** - Create custom models
3. **[Advanced Techniques](advanced-techniques.md)** - Master professional workflows

---

*Last updated: 2025-02-11*
