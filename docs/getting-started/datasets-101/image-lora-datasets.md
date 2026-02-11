# Image LoRA Datasets

Image LoRA datasets are specifically designed for training image generation models. This guide covers the unique requirements and best practices for creating effective image LoRA datasets.

## 🎯 Overview

### Image LoRA vs. Other Training Types

#### What Makes Image LoRA Different
- **Image Focus**: Trains on static images only
- **High Resolution**: Typically higher resolution requirements
- **Detail Emphasis**: Focus on visual details and composition
- **Style Learning**: Strong emphasis on artistic style

#### Training Goals
- **Character Consistency**: Same person across different images
- **Style Reproduction**: Consistent artistic style
- **Concept Learning**: Specific objects or concepts
- **Quality Enhancement**: Improve image quality

---

## 📸 Image Requirements

### Resolution Standards

#### Model-Specific Requirements
```
SD1.5 Image LoRA:
- Minimum: 512×512 pixels
- Recommended: 512×512 pixels
- Higher: 768×768 pixels (if model supports)
- Aspect Ratio: 1:1 (square) preferred

SDXL Image LoRA:
- Minimum: 1024×1024 pixels
- Recommended: 1024×1024 pixels
- Higher: 1280×1280 pixels (if VRAM allows)
- Aspect Ratio: 1:1 (square) preferred

FLUX.1 Image LoRA:
- Minimum: 1024×1024 pixels
- Recommended: 1024×1024 pixels
- Higher: 1280×1280 pixels (if VRAM allows)
- Aspect Ratio: 1:1 (square) preferred
```

#### Quality Standards
- **Sharp Focus**: Main subject clearly in focus
- **Good Lighting**: Even, natural lighting
- **Low Noise**: Minimal compression artifacts
- **Proper Exposure**: Well-balanced brightness and contrast

### File Format

#### Preferred Formats
- **PNG**: Lossless format, best quality
- **TIFF**: Professional format, maximum quality
- **WEBP**: Modern format, good balance
- **JPEG**: Use only when necessary

#### Format Considerations
- **Training Compatibility**: Ensure format works with training tools
- **Quality Preservation**: Use lossless formats when possible
- **Storage Efficiency**: Balance quality and storage needs

---

## 🎨 Character Image LoRA Datasets

### Character Dataset Requirements

#### Consistency Standards
- **Same Person**: All images show the same person
- **Consistent Appearance**: Same hair, clothing, accessories
- **Varied Poses**: Different angles and expressions
- **Good Lighting**: Consistent lighting quality

#### Essential Shots
```
Character Dataset Shot List:
- Front portrait (neutral expression): 3-5 images
- Side profiles (left and right): 2-3 images each
- 3/4 view: 1-2 images
- Action poses: 5-10 images
- Close-ups: 3-5 detailed shots
- Different expressions: 3-5 images
- Various contexts: 5-10 images
```

### Character Captioning

#### Caption Structure
```
"photo of [character_name], [age] [gender] with [appearance], wearing [clothing], [action] in [location], [lighting], [style], [quality]"
```

#### Character Caption Examples
```
"photo of sarah_character, 25-year-old woman with long brown hair and bright green eyes, wearing a navy blue business suit, sitting in a modern office with soft window lighting, professional photography, sharp focus"

"photo of aria_character, young elf woman with long silver hair and bright blue eyes, wearing white flowing dress, standing in an enchanted forest, soft natural lighting, fantasy art style"
```

### Character Dataset Size

#### Minimum Requirements
- **Absolute Minimum**: 15 images
- **Recommended**: 20-30 images
- **Optimal**: 50+ images with variety
- **Quality Over Quantity**: Better 20 excellent images than 100 mediocre ones

#### Quality Guidelines
- **All High Quality**: Every image should be high quality
- **Consistent Style**: Similar photography or artistic style
- **Varied Contexts**: Different settings and situations
- **Good Diversity**: Different poses, expressions, lighting

---

## 🎨 Style Image LoRA Datasets

### Style Dataset Requirements

#### Style Consistency
- **Same Artistic Style**: All images demonstrate same style
- **Varied Subjects**: Different subjects showing the style
- **Consistent Technique**: Same artistic techniques
- **Quality Examples**: Best examples of the style

#### Style Elements
```
Style Dataset Elements:
- Brush Strokes: Consistent texture and technique
- Color Palette: Similar color choices and relationships
- Composition: Similar framing and composition
- Medium: Consistent artistic medium
- Mood: Consistent emotional tone or atmosphere
```

### Style Captioning

#### Caption Structure
```
"[subject], [style_name] style, [description], [key features], [color palette], [composition style], [medium], [quality]"
```

#### Style Caption Examples
```
"landscape, watercolor_style, mountain range at sunset, impressionist style, vibrant colors, visible brushstrokes, soft edges, warm golden hour lighting, masterpiece"

"portrait, oil_painting_style, elderly woman with wrinkles, soft lighting, classical style, rich colors, visible brush texture, professional quality"

"cityscape, cyberpunk_style, neon lights, futuristic architecture, dramatic night scene, digital art, high contrast, vibrant colors"
```

### Style Dataset Size

#### Minimum Requirements
- **Absolute Minimum**: 20 images
- **Recommended**: 30-50 images
- **Optimal**: 100+ images showing style
- **Subject Variety**: Different subjects demonstrating style

#### Quality Guidelines
- **Style Consistency**: All images must show same style
- **Subject Diversity**: Different subjects to demonstrate style
- **Quality Examples**: Best possible examples of the style
- **Technical Quality**: High resolution, good lighting

---

## 🏷️ Concept Image LoRA Datasets

### Concept Dataset Requirements

#### Concept Clarity
- **Clear Definition**: Concept clearly visible in all images
- **Consistent Features**: Same characteristics across examples
- **Varied Contexts**: Concept shown in different situations
- **Clear Boundaries**: Clear definition of what concept includes

#### Concept Elements
```
Concept Dataset Elements:
- Clear Representation: Concept is clearly visible
- Varied Contexts: Different situations and uses
- Consistent Features: Same characteristics across examples
- Quality Examples: High-quality demonstrations
- Boundary Definition: Clear what is and isn't included
```

### Concept Captioning

#### Caption Structure
```
"[concept_name], [description], [key features], [magical properties], [material], [function], [context], [quality]"
```

#### Concept Caption Examples
```
"magical_sword, glowing blue crystal blade with ornate silver hilt, intricate engravings, magical energy swirling around the blade, high fantasy quality"

"steampunk_device, futuristic weapon with glowing blue energy trails, metallic body, advanced technology, sci-fi concept"

"fantasy_portal, glowing archway with mystical symbols, ancient stone architecture, magical atmosphere, portal effect, high fantasy quality"
```

### Concept Dataset Size

#### Minimum Requirements
- **Absolute Minimum**: 10 images
- **Recommended**: 15-25 images
- **Optimal**: 30+ images with context
- **Context Variety**: Different situations and uses

#### Quality Guidelines
- **Clarity First**: Concept must be clearly visible
- **Consistent Features**: Same characteristics across examples
- **Varied Contexts**: Different situations showing concept
- **High Quality**: Professional-level execution

---

## 🔧 Image Processing for LoRA

### Preprocessing Steps

#### Resolution Standardization
- **Target Resolution**: Match model requirements
- **Aspect Ratio**: Usually 1:1 for LoRA training
- **Quality Preservation**: Use high-quality resizing
- **Consistent Processing**: Same processing for all images

#### Color Space Standardization
- **sRGB Standard**: Use sRGB color space
- **Consistent Color**: Ensure color consistency
- **Profile Embedding**: Include color profile when possible
- **Quality Check**: Verify color accuracy

#### Quality Enhancement
- **Noise Reduction**: Remove digital noise
- **Sharpening**: Enhance image clarity
- **Contrast Adjustment**: Optimize contrast
- **Color Correction**: Fix color issues

### Processing Tools

#### Professional Tools
- **Adobe Lightroom**: Professional photo editing
- **Adobe Photoshop**: Professional image editing
- **Capture One**: Professional photo processing
- **Affinity Photo**: Professional alternative

#### Free Tools
- **GIMP**: Free professional image editor
- **RawTherapee**: Free RAW photo processor
- **XnView MP**: Free image management
- **ImageMagick**: Command-line processing

#### Batch Processing
- **Automation**: Process multiple images at once
- **Consistent Settings**: Use same settings for all images
- **Quality Control**: Monitor quality during processing
- **Progress Tracking**: Track processing progress

---

## 📊 Dataset Organization

### Folder Structure

#### Standard Structure
```
image_lora_dataset/
├── images/              # All image files
├── captions/            # All caption files
├── metadata/             # Dataset metadata
├── processed/            # Processed images
└── splits/               # Training/validation/test splits
```

#### Advanced Structure
```
image_lora_dataset/
├── raw/                  # Original, unprocessed images
│   ├── images/
│   └── captions/
├── processed/             # Processed images
│   ├── images/
│   └── captions/
├── metadata/
│   ├── dataset_info.json
│   ├── quality_assessment.json
│   └── processing_log.json
├── splits/
│   ├── train/
│   ├── validation/
│   └── test/
└── documentation/
    ├── README.md
    └── LICENSE
```

### File Naming

#### Naming Conventions
- **Sequential**: 001.jpg, 002.jpg, 003.jpg...
- **Descriptive**: character_name_pose_001.jpg
- **Date-Based**: 2025-02-11_001.jpg
- **Consistent**: Same pattern across all files

#### Matching Files
- **Image-Caption Pairs**: Each image has matching caption
- **Same Base Name**: 001.jpg ↔ 001.txt
- **Consistent Extension**: All images same format
- **Clear Separation**: Different types in separate folders

---

## 🎯 Quality Assurance

### Validation Checklist

#### Image Quality
- [ ] **Resolution**: All images meet minimum resolution
- [ ] **Focus**: Main subject is clearly in focus
- [ ] **Lighting**: Good lighting without harsh shadows
- [ ] **Noise**: Minimal compression artifacts
- [ ] **Format**: Consistent file format across dataset

#### Caption Quality
- [ ] **Accuracy**: Captions accurately describe images
- [ ] **Completeness**: All relevant information included
- [ ] **Consistency**: Consistent terminology and structure
- [ ] **Trigger Words**: Include trigger words consistently
- [ ] **Style**: Style information included when relevant

#### Organization Quality
- [ ] **Structure**: Proper folder organization
- [ ] **Naming**: Consistent file naming convention
- [ ] **Matching**: Images and captions properly matched
- [ ] **Metadata**: Dataset metadata documented
- [ ] **Validation**: Dataset has been validated

### Common Issues

#### Quality Issues
- **Blurry Images**: Out of focus or camera shake
- **Poor Lighting**: Harsh shadows or overexposure
- **Compression Artifacts**: JPEG blocking or ringing
- **Inconsistent Quality**: Mixed quality across dataset

#### Organization Issues
- **Missing Files**: Some images or captions missing
- **Mismatched Files**: Images and captions don't match
- **Inconsistent Naming**: Inconsistent file naming
- **Poor Structure**: Disorganized folder structure

---

## 💡 Best Practices

### Quality First
- **High Standards**: Maintain high quality standards
- **Consistent Quality**: Uniform quality across dataset
- **Quality Review**: Regular quality assessments
- **Continuous Improvement**: Improve quality over time

### Consistency
- **Style Consistency**: Consistent artistic or photographic style
- **Terminology**: Use consistent terminology in captions
- **Processing**: Consistent processing across all images
- **Organization**: Consistent organization structure

### Documentation
- **Comprehensive Documentation**: Document all aspects of dataset
- **Version Control**: Track changes and improvements
- **Quality Assessment**: Regular quality evaluations
- **Lessons Learned**: Document insights for future datasets

---

## 🚀 Practical Examples

### Character LoRA Dataset Example

#### Dataset Structure
```
sarah_character/
├── images/
│   ├── 001.jpg  # Front portrait
│   ├── 002.jpg  # Side profile
│   ├── 003.jpg  # 3/4 view
│   └── ...
├── captions/
│   ├── 001.txt
│   ├── 002.txt
│   ├── 003.txt
│   └── ...
└── metadata/
    ├── dataset_info.json
    └── quality_assessment.json
```

#### Sample Caption
```
"photo of sarah_character, 25-year-old woman with long brown hair and bright green eyes, wearing a navy blue business suit, sitting in a modern office with soft window lighting, professional photography, sharp focus"
```

### Style LoRA Dataset Example

#### Dataset Structure
```
watercolor_style/
├── images/
│   ├── 001.jpg  # Landscape
│   ├── 002.jpg  # Portrait
│   ├── 003.jpg  # Still life
│   └── ...
├── captions/
│   ├── 001.txt
│   ├── 002.txt
│   ├── 003.txt
│   └── ...
└── metadata/
    ├── dataset_info.json
    └── quality_assessment.json
```

#### Sample Caption
```
"landscape, watercolor_style, mountain range at sunset, impressionist style, vibrant colors, visible brushstrokes, soft edges, warm golden hour lighting, masterpiece"
```

---

## 🚀 What's Next?

Now that you understand image LoRA datasets, you're ready to:

1. **[Video LoRA Datasets](video-lora-datasets.md)** - Create video LoRA datasets
2. **[Dataset Validation and Testing](dataset-validation-and-testing.md)** - Ensure dataset quality
3. **[LoRA Training 101](../loRA-training-101/README.md)** - Start training your LoRA

---

*Last updated: 2025-02-11*
