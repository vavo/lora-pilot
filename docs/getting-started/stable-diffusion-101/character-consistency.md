# Character Consistency with LoRA

Creating consistent characters across multiple images is one of the biggest challenges in AI art. LoRA (Low-Rank Adaptation) is the perfect solution - let's learn how to use it effectively.

##  The Character Consistency Problem

### Why Characters Change

Without special training, AI treats each prompt as completely new:
- Same prompt = different person each time
- Different poses = completely different character
- No memory of previous images
- Random variations in features

### What We Want
- Same character in different poses
- Consistent facial features
- Same clothing and accessories
- Recognizable personality across images

##  LoRA Solution

### How LoRA Solves Consistency

LoRA teaches the AI about your specific character:

```
Before LoRA:
"woman with red hair" → Random woman with red hair

After LoRA:
"photo of my_character" → YOUR specific character with red hair
```

### The Magic Process

1. **Collect Reference Images**: 15-30 photos of your character
2. **Train LoRA**: AI learns your character's features
3. **Use Trigger Word**: Special word activates your character
4. **Generate Consistently**: Same character in any situation

##  Creating Character LoRA

### Step 1: Collect Reference Images

#### Image Requirements
- **Quantity**: 15-30 images minimum
- **Quality**: Clear, well-lit photos
- **Variety**: Different poses, angles, expressions
- **Consistency**: Same person throughout

#### Ideal Image Collection
```
Your Character Reference Set:
├── Front view (3-5 images)
├── Side views (2-3 images each side)
├── Different expressions (3-5 images)
├── Various poses (5-8 images)
├── Different lighting (2-3 images)
└── Full body + close-ups (mixed)
```

#### Photo Tips
- **Good Lighting**: Even, natural lighting works best
- **Clear Background**: Simple backgrounds help AI focus
- **High Resolution**: 512x512 or higher
- **Consistent Appearance**: Same hair, clothes, makeup

### Step 2: Prepare Dataset

#### Image Processing
- **Crop to Square**: 512x512 for SD1.5, 1024x1024 for SDXL
- **Consistent Size**: All images same resolution
- **Quality Check**: Remove blurry or poor images
- **File Naming**: Sequential names help organization

#### Caption Writing
- **Simple Descriptions**: "photo of person", "portrait"
- **Character Name**: Use consistent trigger word
- **Avoid Complex Details**: Let AI focus on character features

### Step 3: Train LoRA

#### Training Settings
```
Beginner Settings:
- Steps: 1000-1500
- Learning Rate: 1e-4
- Batch Size: 1
- Network Dim: 32-64

Advanced Settings:
- Steps: 2000-3000
- Learning Rate: 5e-5
- Network Dim: 64-128
- Regularization: Add diverse images
```

#### Training Process
1. **Use TagPilot**: Upload and tag your images
2. **Select Training Profile**: Choose character training
3. **Set Trigger Word**: Unique word like "my_character"
4. **Start Training**: Monitor progress
5. **Test Results**: Check sample images during training

##  Using Character LoRA

### Basic Usage

#### Trigger Word System
```
Standard Prompt: "photo of a woman"
Character Prompt: "photo of my_character"

With Style: "photo of my_character, anime style"
With Pose: "photo of my_character sitting on bench"
```

#### LoRA Weight Control
```
Weight 0.3: Subtle character influence
Weight 0.7: Balanced character presence
Weight 1.0: Strong character identity
Weight 1.5: Very strong character (can look artificial)
```

### Advanced Techniques

#### Multiple Character LoRA
```
Two Characters:
"photo of character_A and character_B together"

Character + Style:
"photo of my_character, oil painting style"

Character + Concept:
"photo of my_character as a superhero"
```

#### Consistency Tips
- **Same Seed**: Use same seed for similar poses
- **Consistent Prompts**: Similar structure across images
- **Weight Experimentation**: Find optimal LoRA weight
- **Style LoRA**: Combine with style LoRA for consistent look

##  Practical Examples

### Example 1: Portrait Series
```
Goal: Professional portrait series
Base Model: SDXL
Character LoRA: "professional_model" (weight: 0.8)
Prompts:
- "professional portrait of professional_model, studio lighting"
- "professional_model in business attire, office setting"
- "professional_model casual, outdoor lighting"
```

### Example 2: Story Character
```
Goal: Character for visual story
Base Model: SD1.5
Character LoRA: "story_protagonist" (weight: 1.0)
Prompts:
- "story_protagonist in fantasy forest, adventurous"
- "story_protagonist reading book, cozy library"
- "story_protagonist facing dragon, brave expression"
```

### Example 3: Brand Character
```
Goal: Consistent brand mascot
Base Model: FLUX.1 Schnell
Character LoRA: "brand_mascot" (weight: 0.7)
Prompts:
- "brand_mascot with product, happy expression"
- "brand_mascot in different seasonal settings"
- "brand_mascot interacting with customers"
```

##  Troubleshooting Character LoRA

### Common Issues

#### Character Not Recognizable
- **Problem**: Generated images don't look like your character
- **Solutions**:
  - Check training images quality
  - Increase training steps
  - Adjust LoRA weight
  - Verify trigger word spelling

#### Overfitting
- **Problem**: AI only reproduces training images
- **Solutions**:
  - Add more diverse training images
  - Reduce learning rate
  - Add regularization images
  - Use lower LoRA weight

#### Inconsistent Features
- **Problem**: Some features change between images
- **Solutions**:
  - Ensure consistent appearance in training images
  - Use same seed for similar poses
  - Adjust CFG scale (try 7-10)
  - Check image resolution consistency

#### Artifacts or Distortion
- **Problem**: Strange artifacts or distorted features
- **Solutions**:
  - Reduce training steps if overtrained
  - Check image preprocessing
  - Try different sampler
  - Lower CFG scale

### Quality Improvement Tips

#### Better Training Data
- **High Quality Images**: Use clear, well-lit photos
- **Variety**: Different poses, expressions, lighting
- **Consistency**: Same person throughout
- **Background**: Simple backgrounds help AI focus

#### Training Optimization
- **Right Steps**: 1000-2000 steps usually optimal
- **Learning Rate**: Start with 1e-4, adjust if needed
- **Network Dim**: 32-64 for most cases
- **Regularization**: Add diverse images to prevent overfitting

#### Generation Techniques
- **Optimal Weight**: Usually 0.7-1.0 for characters
- **CFG Scale**: 7-10 works well for character consistency
- **Sampler Choice**: DPM++ or DDIM for consistency
- **Seed Control**: Use same seed for similar compositions

##  Advanced Character Techniques

### Multi-Character Scenes
```
Technique: Multiple Character LoRAs
Setup:
- Character A LoRA: "hero_character" (weight: 0.8)
- Character B LoRA: "villain_character" (weight: 0.8)
- Prompt: "hero_character and villain_character facing each other"

Benefits:
- Consistent character appearances
- Interactive scenes
- Story progression possible
```

### Character + Environment
```
Technique: Character with specific environments
Setup:
- Character LoRA: "sci_fi_character" (weight: 0.9)
- Environment LoRA: "space_station" (weight: 0.6)
- Prompt: "sci_fi_character in space_station, futuristic"

Benefits:
- Character stays consistent
- Environment adds context
- Professional-looking results
```

### Character Evolution
```
Technique: Show character development
Setup:
- Young version: "young_character" (weight: 0.8)
- Current version: "character" (weight: 0.8)
- Older version: "old_character" (weight: 0.8)
- Prompts: Show character at different life stages

Benefits:
- Character development storytelling
- Consistent aging progression
- Emotional narrative possible
```

##  Best Practices

### Training Best Practices
- **Start Simple**: 15-20 good images better than 50 poor ones
- **Quality Over Quantity**: Clear, well-lit images essential
- **Consistent Appearance**: Same hair, clothes, features
- **Varied Poses**: Different angles and expressions

### Usage Best Practices
- **Test Weights**: Find optimal LoRA weight (usually 0.7-1.0)
- **Consistent Prompts**: Similar structure across images
- **Document Settings**: Save successful prompt combinations
- **Experiment**: Try different styles and situations

### Organization Best Practices
- **Clear Naming**: Use descriptive LoRA names
- **Version Control**: Keep different training versions
- **Backup Models**: Save successful LoRA files
- **Documentation**: Record training settings and results

##  What's Next?

Now that you can create consistent characters, you're ready to:

1. **[Advanced Techniques](advanced-techniques.md)** - Learn inpainting and outpainting
2. **[Practical Examples](practical-examples.md)** - Try real-world projects
3. **[Prompting Fundamentals](prompting-fundamentals.md)** - Master prompt writing

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)


