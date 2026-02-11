# Dataset Preparation

Your training dataset is the foundation of your LoRA model's quality. Garbage in, garbage out - this guide shows you how to prepare high-quality datasets that train well.

## 🎯 The Big Picture

### Why Dataset Quality Matters

Think of your dataset like teaching materials:
- **Good Materials**: Clear examples = student learns well
- **Poor Materials**: Confusing examples = student learns wrong
- **Consistent Examples**: Clear patterns = student understands concepts

### The Dataset Formula

```
High-Quality Dataset + Proper Preparation = Excellent Trained Model
     ↓                    ↓                    ↓
Good Photos + Right Format + Good Captions = Model that works perfectly
```

---

## 📸 Image Collection Guidelines

### Image Quality Standards

#### Resolution Requirements
- **SD1.5**: 512x512 pixels (minimum)
- **SDXL**: 1024x1024 pixels (minimum)
- **FLUX.1**: 1024x1024 pixels (minimum)
- **Higher is Better**: 2x minimum resolution is ideal

#### Image Clarity
- **In Focus**: Sharp, clear subjects
- **Good Lighting**: Even, natural lighting
- **No Blur**: Avoid motion blur or camera shake
- **High Quality**: Avoid compression artifacts

#### Composition Guidelines
- **Subject Focus**: Main subject clearly visible
- **Simple Backgrounds**: Less distracting elements
- **Consistent Framing**: Similar composition across images
- **Good Angles**: Variety of poses and angles

### Subject Consistency

#### Character Training
- **Same Person**: All images should be the same person
- **Consistent Appearance**: Same hair, clothing, accessories
- **Varied Poses**: Different angles, expressions, situations
- **Lighting Variety**: Different lighting conditions

#### Style Training
- **Consistent Style**: All images in same artistic style
- **Varied Subjects**: Different subjects showing the style
- **Style Elements**: Consistent use of colors, techniques
- **Quality Examples**: Best examples of the style

#### Concept Training
- **Clear Examples**: Clear examples of the concept
- **Varied Contexts**: Concept in different situations
- **Consistent Features**: Same characteristics across examples
- **Good Diversity**: Different angles and lighting

---

## 📝 Captioning Guidelines

### What Are Captions

Text descriptions that tell the AI what's in each image. Good captions are crucial for training quality.

### Caption Writing Principles

#### Be Descriptive
- **Subject**: "a woman with long brown hair"
- **Clothing**: "wearing a blue summer dress"
- **Setting**: "in a garden with flowers"
- **Lighting**: "soft natural lighting"
- **Quality**: "sharp focus, detailed"

#### Be Consistent
- **Same Terminology**: Use same words for same features
- **Similar Structure**: Follow similar caption pattern
- **Trigger Words**: Include consistent trigger words
- **Quality Terms**: Add quality descriptors

#### Be Specific
```
Vague: "person"
Better: "young woman with shoulder-length brown hair"
Best: "25-year-old woman with shoulder-length brown hair, green eyes, wearing a navy blue business suit"
```

### Caption Examples

#### Character Training
```
Good: "photo of a woman with long silver hair, blue eyes, wearing a white dress, standing in a forest"
Better: "photo of aria_character, young elf woman with long silver hair, bright blue eyes, wearing white flowing dress, standing in an enchanted forest, soft lighting"
```

#### Style Training
```
Good: "oil painting of a landscape"
Better: "oil painting of a mountain landscape, impressionist style, vibrant colors, visible brushstrokes"
```

#### Concept Training
```
Good: "magical sword"
Better: "fantasy sword, glowing blue crystal blade, ornate silver hilt, magical energy, detailed"
```

### Caption Formatting

#### File Naming
- **One Caption Per Image**: .txt file with same name as image
- **UTF-8 Encoding**: Use UTF-8 for special characters
- **No Extra Spaces**: Clean, simple text
- **Consistent Extension**: .txt files

#### Caption Content
- **Simple Text**: Plain text, no special formatting
- **One Line**: Single line per caption
- **No Quotes**: Avoid quotes unless part of description
- **Trigger Words**: Include your trigger word consistently

---

## 🔧 Dataset Organization

### Folder Structure

#### Basic Structure
```
dataset/
├── images/
│   ├── 001.jpg
│   ├── 001.txt
│   ├── 002.jpg
│   ├── 002.txt
│   └── ...
└── metadata/
    ├── dataset_info.json
    └── training_config.json
```

#### Advanced Structure
```
dataset/
├── train/
│   ├── images/
│   └── captions/
├── validation/
│   ├── images/
│   └── captions/
├── test/
│   ├── images/
│   └── captions/
└── metadata/
    ├── classes.txt
    └── splits.json
```

### File Naming

#### Sequential Naming
- **Numbers**: 001.jpg, 002.jpg, 003.jpg...
- **Zero Padding**: Use leading zeros for proper sorting
- **Consistent Extension**: All images same format
- **Matching Captions**: 001.txt, 002.txt, 003.txt...

#### Descriptive Naming
- **Content-Based**: woman_park_001.jpg
- **Pose-Based**: standing_front_001.jpg
- **Lighting-Based**: natural_light_001.jpg
- **Consistent Pattern**: Same naming scheme throughout

### Metadata Files

#### Dataset Information
```json
{
  "name": "my_character_dataset",
  "type": "character",
  "trigger_word": "my_character",
  "base_model": "sdxl_base",
  "image_count": 25,
  "resolution": "1024x1024",
  "created_date": "2025-02-11",
  "description": "Training dataset for my character"
}
```

#### Training Configuration
```json
{
  "training_type": "lora",
  "rank": 32,
  "alpha": 32,
  "steps": 1500,
  "learning_rate": 1e-4,
  "batch_size": 1,
  "resolution": 1024,
  "caption_prefix": "photo of my_character"
}
```

---

## 🎨 Image Processing

### Resolution Standardization

#### Why Standardize
- **Consistent Training**: All images same size
- **Better Learning**: Model learns from consistent input
- **Avoid Artifacts**: Prevents resizing issues
- **Memory Efficiency**: Predictable memory usage

#### Resizing Methods
- **High Quality**: Use Lanczos or bicubic for downscaling
- **Aspect Ratio**: Maintain original aspect ratio
- **Center Crop**: Focus on most important part
- **Avoid Stretching**: Don't distort image proportions

#### Resolution Guidelines
```
SD1.5 Training:
- Minimum: 512x512
- Recommended: 512x512
- Higher: 768x768 (if base model supports)

SDXL Training:
- Minimum: 1024x1024
- Recommended: 1024x1024
- Higher: 1280x1280 (if VRAM allows)

FLUX.1 Training:
- Minimum: 1024x1024
- Recommended: 1024x1024
- Higher: 1280x1280 (if VRAM allows)
```

### Quality Enhancement

#### Noise Reduction
- **Clean Images**: Remove noise and artifacts
- **Sharpening**: Light sharpening if needed
- **Color Correction**: Adjust brightness and contrast
- **Compression Removal**: Remove JPEG artifacts

#### Format Optimization
- **Lossless Format**: Use PNG or TIFF for best quality
- **Consistent Format**: All images same format
- **Color Space**: sRGB for most training
- **Bit Depth**: 8-bit per channel is sufficient

---

## 📊 Dataset Size Guidelines

### Minimum Requirements

#### Character Training
- **Minimum**: 15 images
- **Recommended**: 20-30 images
- **Optimal**: 50+ images with variety
- **Quality over Quantity**: Better 20 great images than 100 poor ones

#### Style Training
- **Minimum**: 20 images
- **Recommended**: 30-50 images
- **Optimal**: 100+ images showing style
- **Subject Variety**: Different subjects in same style

#### Concept Training
- **Minimum**: 10 images
- **Recommended**: 15-25 images
- **Optimal**: 30+ images with context
- **Context Variety**: Concept in different situations

### Quality vs Quantity

#### Quality Priority
- **15 Excellent Images**: Better than 50 average images
- **Consistent Quality**: All images should be similar quality
- **Clear Examples**: Each image should clearly show the concept
- **Varied Examples**: Different angles, lighting, contexts

#### Quantity Considerations
- **Overfitting Risk**: Too few images = model memorizes
- **Generalization**: More images = better generalization
- **Training Time**: More images = longer training
- **Diminishing Returns**: After 50-100 images, benefits decrease

---

## 🔍 Quality Assurance

### Image Quality Check

#### Visual Inspection
- **All Images**: Review every image individually
- **Consistency Check**: Ensure subject consistency
- **Quality Standards**: Remove poor quality images
- **Technical Issues**: Check for blur, noise, artifacts

#### Technical Validation
- **Resolution Check**: Ensure minimum resolution met
- **File Integrity**: Check for corruption
- **Format Compliance**: Ensure correct format
- **Caption Matching**: Verify captions match images

### Dataset Validation

#### Automated Checks
- **File Count**: Ensure images and captions match
- **Resolution Verification**: Check all images meet requirements
- **Format Validation**: Verify file formats are correct
- **Duplicate Detection**: Remove duplicate images

#### Manual Review
- **Content Review**: Ensure all images show intended concept
- **Caption Accuracy**: Verify captions describe images correctly
- **Consistency Check**: Ensure consistent terminology
- **Quality Assessment**: Overall dataset quality evaluation

---

## 💡 Common Mistakes to Avoid

### Image Collection Mistakes

#### Inconsistent Subject
- **Problem**: Different people in character training
- **Solution**: Ensure all images show same person
- **Prevention**: Carefully review all images before training

#### Poor Image Quality
- **Problem**: Blurry, low resolution, or noisy images
- **Solution**: Use only high-quality, clear images
- **Prevention**: Set quality standards and stick to them

#### Insufficient Variety
- **Problem**: All images from same angle/lighting
- **Solution**: Include variety of poses and lighting
- **Prevention**: Plan variety before collecting images

### Captioning Mistakes

#### Vague Descriptions
- **Problem**: "person" instead of detailed description
- **Solution**: Be specific and descriptive
- **Prevention**: Use captioning guidelines consistently

#### Inconsistent Terminology
- **Problem**: "brown hair" in one caption, "dark hair" in another
- **Solution**: Use consistent terminology throughout
- **Prevention**: Create terminology guide for your dataset

### Organization Mistakes

#### File Naming Issues
- **Problem**: Inconsistent naming or missing files
- **Solution**: Use systematic naming convention
- **Prevention**: Plan naming before organizing

#### Metadata Errors
- **Problem**: Incorrect or missing metadata files
- **Solution**: Double-check all metadata files
- **Prevention**: Use templates and validation

---

## 🚀 Practical Tips

### Collection Strategy

#### Start Small
- **Pilot Dataset**: Start with 10-15 images
- **Test Training**: See how well it works
- **Expand Gradually**: Add more images if needed
- **Quality Focus**: Prioritize quality over quantity

#### Use References
- **Style References**: Collect examples of desired style
- **Character Sheets**: Create character reference sheets
- **Concept Boards**: Visual concept collections
- **Inspiration**: Gather inspirational examples

#### Quality Control
- **Set Standards**: Define quality requirements
- **Review Process**: Systematic quality review
- **Rejection Criteria**: Clear guidelines for what to exclude
- **Continuous Improvement**: Learn from each dataset

### Documentation

#### Track Everything
- **Collection Notes**: Document sources and methods
- **Processing Steps**: Record all processing done
- **Training Results**: Document training outcomes
- **Lessons Learned**: Note what worked and what didn't

#### Version Control
- **Dataset Versions**: Track different dataset versions
- **Experiment Tracking**: Record different dataset configurations
- **Results Comparison**: Compare results across versions
- **Backup Strategy**: Keep backups of good datasets

---

## 🔧 Tools and Resources

### Image Processing Tools

#### Free Tools
- **GIMP**: Free image editor with batch processing
- **ImageMagick**: Command-line image processing
- **FastStone**: Batch image converter and optimizer
- **XnView MP**: Image viewer and organizer

#### Professional Tools
- **Adobe Lightroom**: Professional photo management
- **Capture One**: Professional photo editing
- **Bridge**: Photo management with Adobe integration
- **Photo Mechanic**: Professional metadata editing

### Dataset Management

#### Organization Tools
- **Adobe Bridge**: Visual file organization
- **XnView MP**: Image management and tagging
- **DigiKam**: Professional photo management
- **Adobe Lightroom**: Photo organization and editing

#### Validation Tools
- **Custom Scripts**: Python scripts for validation
- **Dataset Validators**: Specialized dataset tools
- **Quality Checkers**: Automated quality assessment
- **Metadata Editors**: JSON/YAML editors for metadata

---

## 🚀 What's Next?

Now that you know how to prepare datasets, you're ready to:

1. **[Training Workflows](training-workflows.md)** - Learn step-by-step training processes
2. **[Practical Training Projects](practical-training-projects.md)** - Start your first training project
3. **[Advanced Training Techniques](advanced-training-techniques.md)** - Master professional methods
4. **[Troubleshooting Training](troubleshooting-training.md)** - Handle common training issues

---

*Last updated: 2025-02-11*
