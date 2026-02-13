# Video LoRA Datasets

Video LoRA datasets are specifically designed for training video generation models. This guide covers the unique requirements and best practices for creating effective video LoRA datasets.

##  Overview

### Video LoRA vs. Image LoRA

#### What Makes Video LoRA Different
- **Temporal Dimension**: Training on time-based sequences
- **Motion Learning**: Learning movement and dynamics
- **Frame Consistency**: Consistent subject across frames
- **Continuity**: Smooth transitions between frames

#### Training Goals
- **Character Animation**: Consistent character movement
- **Style Transfer**: Consistent video style
- **Motion Learning**: Specific movements or actions
- **Video Quality**: Enhanced video generation

---

## 🎥 Video Requirements

### Resolution Standards

#### Model-Specific Requirements
```
SD1.5 Video LoRA:
- Minimum: 512×512 pixels
- Recommended: 512×512 pixels
- Higher: 768×768 pixels (if model supports)
- Aspect Ratio: 16:9 or 1:1

SDXL Video LoRA:
- Minimum: 1024×576 pixels (16:9)
- Recommended: 1024×1024 pixels (1:1)
- Higher: 1280×720 pixels (16:9)
- Aspect Ratio: 16:9 or 1:1

FLUX.1 Video LoRA:
- Minimum: 1024×576 pixels (16:9)
- Recommended: 1024×1024 pixels (1:1)
- Higher: 1280×720 pixels (16:9)
- Aspect Ratio: 16:9 or 1:1
```

#### Quality Standards
- **Stable Camera**: Minimal camera shake
- **Good Lighting**: Consistent lighting throughout
- **Smooth Motion**: No stuttering or frame drops
- **Clear Subject**: Subject clearly visible in all frames

### Frame Rate Considerations

#### Common Frame Rates
- **24 FPS**: Standard cinema frame rate
- **30 FPS**: Standard video frame rate
- **60 FPS**: High-quality video
- **Variable**: Different frame rates for different purposes

#### Frame Rate Guidelines
- **Training**: Usually 24-30 FPS for efficiency
- **Generation**: Can vary based on needs
- **Consistency**: Same frame rate across dataset
- **Quality vs. Speed**: Higher FPS = better quality but more data

---

##  Character Video LoRA Datasets

### Character Video Requirements

#### Consistency Standards
- **Same Person**: All videos show the same person
- **Consistent Appearance**: Same hair, clothing, accessories
- **Varied Actions**: Different movements and expressions
- **Good Lighting**: Consistent lighting quality

#### Essential Video Types
```
Character Video Dataset Types:
- Idle Animation: 5-10 seconds of standing/breathing
- Walking Animation: 5-10 seconds of walking
- Facial Expressions: 3-5 seconds each expression
- Hand Gestures: 3-5 seconds each gesture
- Action Sequences: 5-10 seconds of various actions
- Close-up Shots: 3-5 seconds of detailed face shots
- Full Body Shots: 5-10 seconds of full body
```

### Character Captioning

#### Video Caption Structure
```
"video of [character_name], [age] [gender] with [appearance], wearing [clothing], [action] in [location], [lighting], [style], [quality], [duration]"
```

#### Character Caption Examples
```
"video of sarah_character, 25-year-old woman with long brown hair and bright green eyes, wearing a navy blue business suit, walking through a modern office with soft window lighting, professional video quality, 8 seconds duration"

"video of aria_character, young elf woman with long silver hair and bright blue eyes, wearing white flowing dress, casting a spell in an enchanted forest, soft natural lighting, fantasy video style, 6 seconds duration"
```

### Character Dataset Size

#### Minimum Requirements
- **Absolute Minimum**: 3-5 video clips
- **Recommended**: 5-10 video clips
- **Optimal**: 15+ video clips with variety
- **Quality Over Quantity**: Better 5 excellent clips than 20 mediocre ones

#### Quality Guidelines
- **All High Quality**: Every video should be high quality
- **Consistent Style**: Similar video style and quality
- **Varied Actions**: Different movements and expressions
- **Good Diversity**: Different contexts and situations

---

##  Style Video LoRA Datasets

### Style Video Requirements

#### Style Consistency
- **Same Video Style**: All videos demonstrate same style
- **Varied Subjects**: Different subjects showing the style
- **Consistent Technique**: Same video techniques
- **Quality Examples**: Best examples of the style

#### Style Elements
```
Video Style Dataset Elements:
- Color Grading: Consistent color palette and grading
- Motion Style: Similar motion characteristics
- Composition: Similar framing and composition
- Editing Style: Consistent editing techniques
- Mood: Consistent emotional tone or atmosphere
```

### Style Captioning

#### Video Caption Structure
```
"[subject], [style_name] video style, [description], [key features], [color palette], [motion style], [editing style], [quality], [duration]"
```

#### Style Caption Examples
```
"landscape, cinematic_style video, mountain range at sunset, cinematic color grading, smooth camera movement, professional editing, high quality, 10 seconds duration"

"portrait, documentary_style video, elderly woman telling story, natural lighting, handheld camera movement, authentic style, emotional, 15 seconds duration"

"cityscape, cyberpunk_style video, neon lights at night, futuristic atmosphere, dynamic camera movement, high contrast, vibrant colors, 8 seconds duration"
```

### Style Dataset Size

#### Minimum Requirements
- **Absolute Minimum**: 5 video clips
- **Recommended**: 10-15 video clips
- **Optimal**: 20+ video clips showing style
- **Subject Variety**: Different subjects demonstrating style

#### Quality Guidelines
- **Style Consistency**: All videos must show same style
- **Subject Diversity**: Different subjects to demonstrate style
- **Quality Examples**: Best possible examples of the style
- **Technical Quality**: High resolution, good lighting, stable camera

---

## 🏷️ Concept Video LoRA Datasets

### Concept Video Requirements

#### Concept Clarity
- **Clear Definition**: Concept clearly visible in all videos
- **Consistent Features**: Same characteristics across examples
- **Varied Contexts**: Concept shown in different situations
- **Clear Boundaries**: Clear definition of what concept includes

#### Concept Elements
```
Video Concept Dataset Elements:
- Clear Representation: Concept is clearly visible
- Varied Contexts: Different situations and uses
- Consistent Features: Same characteristics across examples
- Quality Examples: High-quality demonstrations
- Boundary Definition: Clear what is and isn't included
```

### Concept Captioning

#### Video Caption Structure
```
"[concept_name], [description], [key features], [magical properties], [material], [function], [context], [quality], [duration]"
```

#### Concept Caption Examples
```
"magical_sword_video, glowing blue crystal blade with ornate silver hilt, magical energy swirling around the blade, high fantasy video quality, 5 seconds duration"

"steampunk_device_video, futuristic weapon with glowing blue energy trails, metallic body, advanced technology, sci-fi concept, 6 seconds duration"

"fantasy_portal_video, glowing archway with mystical symbols, ancient stone architecture, magical atmosphere, portal effect, high fantasy quality, 8 seconds duration"
```

### Concept Dataset Size

#### Minimum Requirements
- **Absolute Minimum**: 3-5 video clips
- **Recommended**: 5-10 video clips
- **Optimal**: 15+ video clips with context
- **Context Variety**: Different situations and uses

#### Quality Guidelines
- **Clarity First**: Concept must be clearly visible
- **Consistent Features**: Same characteristics across examples
- **Varied Contexts**: Different situations showing concept
- **High Quality**: Professional-level execution

---

##  Video Processing for LoRA

### Preprocessing Steps

#### Resolution Standardization
- **Target Resolution**: Match model requirements
- **Aspect Ratio**: Usually 16:9 or 1:1 for video LoRA
- **Quality Preservation**: Use high-quality resizing
- **Consistent Processing**: Same processing for all videos

#### Frame Extraction
- **Frame Rate**: Consistent frame rate across dataset
- **Frame Selection**: Extract representative frames
- **Quality Preservation**: Maintain video quality
- **Consistent Timing**: Consistent frame intervals

#### Quality Enhancement
- **Stabilization**: Reduce camera shake
- **Noise Reduction**: Remove video noise
- **Color Correction**: Fix color issues
- **Contrast Adjustment**: Optimize contrast

### Processing Tools

#### Professional Tools
- **Adobe Premiere Pro**: Professional video editing
- **DaVinci Resolve**: Professional color grading
- **Final Cut Pro**: Professional video editing
- **Adobe After Effects**: Professional motion graphics

#### Free Tools
- **DaVinci Resolve**: Free professional video editing
- **Shotcut**: Free open-source video editor
- **Kdenlive**: Free open-source video editor
- **Olive**: Free open-source video editor

#### Batch Processing
- **Automation**: Process multiple videos at once
- **Consistent Settings**: Use same settings for all videos
- **Quality Control**: Monitor quality during processing
- **Progress Tracking**: Track processing progress

---

##  Dataset Organization

### Folder Structure

#### Standard Structure
```
video_lora_dataset/
├── videos/              # All video files
├── frames/               # Extracted frames (if needed)
├── captions/            # All caption files
├── metadata/             # Dataset metadata
├── processed/            # Processed videos
└── splits/               # Training/validation/test splits
```

#### Advanced Structure
```
video_lora_dataset/
├── raw/                  # Original, unprocessed videos
│   ├── videos/
│   └── captions/
├── processed/             # Processed videos
│   ├── videos/
│   └── captions/
├── frames/               # Extracted frames
│   ├── video_001/
│   ├── video_002/
│   └── ...
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
- **Sequential**: 001.mp4, 002.mp4, 003.mp4...
- **Descriptive**: character_name_action_001.mp4
- **Date-Based**: 2025-02-11_001.mp4
- **Consistent**: Same pattern across all files

#### Matching Files
- **Video-Caption Pairs**: Each video has matching caption
- **Same Base Name**: 001.mp4 ↔ 001.txt
- **Consistent Extension**: All videos same format
- **Clear Separation**: Different types in separate folders

---

##  Quality Assurance

### Validation Checklist

#### Video Quality
- [ ] **Resolution**: All videos meet minimum resolution
- [ ] **Frame Rate**: Consistent frame rate across dataset
- [ ] **Stability**: Stable camera with minimal shake
- [ ] **Lighting**: Good lighting throughout videos
- [ ] **Format**: Consistent file format across dataset

#### Content Quality
- [ ] **Subject Clarity**: Subject clearly visible in all frames
- [ ] **Consistency**: Consistent subject across videos
- [ ] **Variety**: Sufficient variety in actions and contexts
- [ ] **Duration**: Appropriate video lengths
- [ ] **Quality**: High technical quality

#### Caption Quality
- [ ] **Accuracy**: Captions accurately describe videos
- [ ] **Completeness**: All relevant information included
- [ ] **Consistency**: Consistent terminology and structure
- [ ] **Trigger Words**: Include trigger words consistently
- [ ] **Duration**: Include video duration information

#### Organization Quality
- [ ] **Structure**: Proper folder organization
- [ ] **Naming**: Consistent file naming convention
- [ ] **Matching**: Videos and captions properly matched
- [ ] **Metadata**: Dataset metadata documented
- [ ] **Validation**: Dataset has been validated

### Common Issues

#### Quality Issues
- **Camera Shake**: Unstable camera movement
- **Poor Lighting**: Inconsistent or poor lighting
- **Frame Drops**: Missing or corrupted frames
- **Audio Issues**: Poor audio quality (if included)

#### Organization Issues
- **Missing Files**: Some videos or captions missing
- **Mismatched Files**: Videos and captions don't match
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
- **Style Consistency**: Consistent video style
- **Terminology**: Use consistent terminology in captions
- **Processing**: Consistent processing across all videos
- **Organization**: Consistent organization structure

### Motion Considerations
- **Smooth Motion**: Ensure smooth, natural movement
- **Consistent Speed**: Consistent motion speed
- **Clear Actions**: Clear, understandable actions
- **Natural Movement**: Avoid unnatural or jerky motion

---

##  Practical Examples

### Character LoRA Dataset Example

#### Dataset Structure
```
sarah_character_video/
├── videos/
│   ├── 001.mp4  # Walking
│   ├── 002.mp4  # Sitting
│   ├── 003.mp4  # Facial expressions
│   └── ...
├── frames/
│   ├── video_001/
│   ├── video_002/
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
"video of sarah_character, 25-year-old woman with long brown hair and bright green eyes, wearing a navy blue business suit, walking through a modern office with soft window lighting, professional video quality, 8 seconds duration"
```

### Style LoRA Dataset Example

#### Dataset Structure
```
cinematic_style_video/
├── videos/
│   ├── 001.mp4  # Landscape
│   ├── 002.mp4  # Portrait
│   ├── 003.mp4  # Action
│   └── ...
├── frames/
│   ├── video_001/
│   ├── video_002/
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
"landscape, cinematic_style video, mountain range at sunset, cinematic color grading, smooth camera movement, professional editing, high quality, 10 seconds duration"
```

---

##  What's Next?

Now that you understand video LoRA datasets, you're ready to:

1. **[Dataset Validation and Testing](dataset-validation-and-testing.md)** - Ensure dataset quality
2. **[LoRA Training 101](../loRA-training-101/README.md)** - Start training your LoRA
3. **[Advanced Training Techniques](../loRA-training-101/advanced-training-techniques.md)** - Master professional methods

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


