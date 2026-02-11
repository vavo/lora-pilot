# Dataset Organization

Proper dataset organization makes your data manageable, shareable, and professional. This guide covers best practices for structuring and managing AI training datasets.

## 🎯 Overview

### Why Organization Matters

Think of dataset organization like a library system:
- **Organized Library**: Easy to find and use books
- **Chaotic Library**: Impossible to find what you need
- **Good Cataloging**: Know exactly what you have
- **Professional Standards**: Professional approach to data management

### The Organization Formula

```
Clear Structure + Consistent Naming + Good Documentation = Professional Dataset
     ↓                    ↓                     ↓                    ↓
Folder Structure + File Naming + Metadata + Version Control = Professional Dataset
```

---

## 📁 Folder Structure Standards

### Basic Dataset Structure

#### Standard Layout
```
dataset/
├── images/              # All image files
├── captions/            # All caption files
├── metadata/             # Dataset metadata and documentation
├── splits/               # Training/validation/test splits
├── processed/            # Processed images (optional)
└── backups/              # Dataset backups (optional)
```

#### Purpose of Each Folder
- **images/**: Raw or processed image files
- **captions/**: Text caption files matching images
- **metadata/**: Dataset information, licenses, documentation
- **splits/**: Data divisions for training
- **processed/**: Processed versions of images
- **backups/**: Backup copies of important files

### Advanced Dataset Structure

#### Professional Layout
```
dataset/
├── raw/                  # Original, unprocessed images
│   ├── images/
│   └── captions/
├── processed/             # Processed images
│   ├── images/
│   └── captions/
├── metadata/
│   ├── dataset_info.json
│   ├── license.txt
│   ├── README.md
│   └── changelog.md
├── splits/
│   ├── train/
│   ├── validation/
│   └── test/
├── tools/                 # Custom tools and scripts
└── documentation/         # Additional documentation
```

---

## 🏷️ File Naming Conventions

### Naming Principles

#### Consistency Rules
- **Same Pattern**: Use same naming pattern for all files
- **No Spaces**: Use underscores or hyphens
- **Lowercase**: Use lowercase for consistency
- **Descriptive**: Names should be descriptive

#### Matching Files
- **Image-Caption Pairs**: Each image has matching caption
- **Same Base Name**: 001.jpg ↔ 001.txt
- **Consistent Extension**: All images same format
- **Sequential Order**: Maintain logical order

### Naming Conventions

#### Sequential Naming
```
Images: 001.jpg, 002.jpg, 003.jpg...
Captions: 001.txt, 002.txt, 003.txt...
```

#### Descriptive Naming
```
Character Training:
- character_name_front_001.jpg
- character_name_side_001.jpg
- character_name_action_001.jpg

Style Training:
- style_name_landscape_001.jpg
- style_name_portrait_001.jpg
- style_name_abstract_001.jpg
```

#### Date-Based Naming
```
2025-02-11_001.jpg
2025-02-11_002.jpg
2025-02-11_003.jpg
```

#### Content-Based Naming
```
portrait_001.jpg
landscape_001.jpg
action_001.jpg
closeup_001.jpg
```

---

## 📊 Metadata Management

### Dataset Metadata

#### Essential Metadata Files

#### dataset_info.json
```json
{
  "name": "my_character_dataset",
  "version": "1.0.0",
  "description": "Training dataset for character 'Sarah'",
  "type": "character",
  "trigger_word": "sarah_character",
  "base_model": "sdxl_base",
  "image_count": 25,
  "resolution": "1024x1024",
  "created_date": "2025-02-11",
  "last_modified": "2025-02-11",
  "author": "Your Name",
  "license": "CC-BY-4.0",
  "tags": ["character", "woman", "professional"],
  "quality_standards": {
    "min_resolution": "1024x1024",
    "file_format": "PNG",
    "color_space": "sRGB"
  }
}
```

#### README.md
```markdown
# My Character Dataset

## Description
Training dataset for character 'Sarah' - a 25-year-old professional woman.

## Contents
- 25 high-quality images
- Matching captions for each image
- Professional photography style
- Varied poses and expressions

## Usage
- Trigger word: `sarah_character`
- Base model: SDXL
- Recommended training steps: 1500
- Learning rate: 1e-4

## License
CC-BY-4.0 - Please credit the original creator.

## Contact
For questions or collaboration, contact: your@email.com
```

### Quality Metadata

#### quality_assessment.json
```json
{
  "overall_quality": "high",
  "resolution_consistency": "consistent",
  "caption_accuracy": "high",
  "style_consistency": "consistent",
  "diversity_score": "medium",
  "issues_found": [],
  "validation_date": "2025-02-11",
  "validator": "manual_review"
}
```

#### processing_log.json
```json
{
  "processing_steps": [
    {
      "step": "resize",
      "parameters": {"size": "1024x1024", "method": "lanczos"},
      "timestamp": "2025-02-11T10:00:00Z"
    },
    {
      "step": "color_correction",
      "parameters": {"white_balance": "auto", "exposure": "+0.1"},
      "timestamp": "2025-02-11T10:05:00Z"
    }
  ],
  "software": "Adobe Lightroom 6.0",
  "operator": "Your Name"
}
```

---

## 🔄 Version Control

### Git Integration

#### Repository Structure
```
dataset/
├── .git/
├── .gitignore
├── images/
├── captions/
├── metadata/
└── README.md
```

#### .gitignore
```
# Ignore large binary files
*.jpg
*.png
*.tiff
*.mp4
*.avi

# Ignore temporary files
*.tmp
*.temp
.DS_Store
Thumbs.db

# Ignore processed files
processed/
backups/
```

#### Branch Strategy
- **main**: Stable, production-ready dataset
- **develop**: Development and testing
- **feature/***: Specific features or improvements
- **hotfix/***: Quick fixes and corrections

### Version Tagging

#### Semantic Versioning
- **Major**: Breaking changes (2.0.0)
- **Minor**: New features (1.1.0)
- **Patch**: Bug fixes (1.0.1)

#### Tag Examples
```bash
git tag -a v1.0.0 -m "Initial release"
git tag -a v1.1.0 -m "Added 5 new images"
git tag -a v1.0.1 -m "Fixed caption errors"
```

---

## 📂 Split Management

### Training Splits

#### Standard Split Ratios
- **Training**: 80% of data
- **Validation**: 10% of data
- **Test**: 10% of data

#### Split Structure
```
splits/
├── train/
│   ├── images/
│   └── captions/
├── validation/
│   ├── images/
│   └── captions/
└── test/
    ├── images/
    └── captions/
```

#### Split Generation Script
```python
import os
import random
import shutil
from pathlib import Path

def create_splits(image_dir, caption_dir, output_dir, train_ratio=0.8, val_ratio=0.1):
    # Get all image files
    images = list(Path(image_dir).glob("*.jpg"))
    random.shuffle(images)
    
    # Calculate split sizes
    n_total = len(images)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)
    n_test = n_total - n_train - n_val
    
    # Create splits
    train_images = images[:n_train]
    val_images = images[n_train:n_train+n_val]
    test_images = images[n_train+n_val:]
    
    # Copy files to splits
    for split_name, split_images in [
        ("train", train_images),
        ("validation", val_images),
        ("test", test_images)
    ]:
        split_dir = Path(output_dir) / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        
        for img_path in split_images:
            # Copy image
            shutil.copy2(img_path, split_dir / "images" / img_path.name)
            
            # Copy matching caption
            caption_path = Path(caption_dir) / f"{img_path.stem}.txt"
            if caption_path.exists():
                shutil.copy2(caption_path, split_dir / "captions" / caption_path.name)

# Usage
create_splits("images", "captions", "splits")
```

---

## 🔧 Automation Tools

### Dataset Management Scripts

#### Validation Script
```python
import os
import json
from pathlib import Path

def validate_dataset(dataset_path):
    """Validate dataset structure and completeness"""
    dataset_path = Path(dataset_path)
    issues = []
    
    # Check required folders
    required_folders = ["images", "captions", "metadata"]
    for folder in required_folders:
        if not (dataset_path / folder).exists():
            issues.append(f"Missing required folder: {folder}")
    
    # Check image-caption pairs
    images = list((dataset_path / "images").glob("*.jpg"))
    for img_path in images:
        caption_path = dataset_path / "captions" / f"{img_path.stem}.txt"
        if not caption_path.exists():
            issues.append(f"Missing caption for: {img_path.name}")
    
    # Check metadata
    metadata_file = dataset_path / "metadata" / "dataset_info.json"
    if not metadata_file.exists():
        issues.append("Missing dataset_info.json")
    
    return issues

# Usage
issues = validate_dataset("my_dataset")
if issues:
    print("Dataset validation issues:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("Dataset validation passed!")
```

#### Dataset Statistics Script
```python
import os
import json
from pathlib import Path
from PIL import Image

def dataset_statistics(dataset_path):
    """Generate dataset statistics"""
    dataset_path = Path(dataset_path)
    stats = {}
    
    # Count images
    images = list((dataset_path / "images").glob("*.jpg"))
    stats["image_count"] = len(images)
    
    # Resolution statistics
    resolutions = []
    for img_path in images:
        with Image.open(img_path) as img:
            resolutions.append(img.size)
    
    if resolutions:
        widths, heights = zip(*resolutions)
        stats["resolution_stats"] = {
            "min_width": min(widths),
            "max_width": max(widths),
            "avg_width": sum(widths) / len(widths),
            "min_height": min(heights),
            "max_height": max(heights),
            "avg_height": sum(heights) / len(heights)
        }
    
    # File size statistics
    file_sizes = [img_path.stat().st_size for img_path in images]
    if file_sizes:
        stats["file_size_stats"] = {
            "min_size": min(file_sizes),
            "max_size": max(file_sizes),
            "avg_size": sum(file_sizes) / len(file_sizes),
            "total_size": sum(file_sizes)
        }
    
    return stats

# Usage
stats = dataset_statistics("my_dataset")
print(json.dumps(stats, indent=2))
```

---

## 📊 Documentation Standards

### Documentation Structure

#### Required Documentation
- **README.md**: Dataset overview and usage
- **LICENSE**: Usage terms and conditions
- **CHANGELOG.md**: Version history and changes
- **dataset_info.json**: Technical metadata
- **quality_assessment.json**: Quality evaluation

#### Optional Documentation
- **collection_notes.md**: Notes about collection process
- **processing_notes.md**: Details about processing steps
- **known_issues.md**: Known issues and limitations
- **examples.md**: Example usage and results

### README Template
```markdown
# Dataset Name

## Overview
Brief description of the dataset.

## Contents
- Number of images: [count]
- Resolution: [resolution]
- File format: [format]
- License: [license]

## Usage
### Prerequisites
- Base model: [model]
- Training tool: [tool]
- Hardware requirements: [requirements]

### Training Parameters
- Learning rate: [rate]
- Steps: [steps]
- Batch size: [size]

### Trigger Words
- Primary: [trigger_word]
- Alternative: [alternatives]

## Quality Standards
- Minimum resolution: [resolution]
- Quality requirements: [requirements]
- Validation results: [results]

## License
[License information]

## Contact
[Contact information]

## Acknowledgments
[Acknowledgments and credits]
```

---

## 🔄 Backup and Recovery

### Backup Strategy

#### Multiple Locations
- **Local Backup**: External hard drive
- **Cloud Backup**: Cloud storage service
- **Offsite Backup**: Different physical location
- **Version Control**: Git repository

#### Backup Schedule
- **Daily**: Incremental backups
- **Weekly**: Full backups
- **Monthly**: Archive old backups
- **Before Changes**: Backup before major changes

### Recovery Procedures

#### Data Recovery
- **Identify Loss**: Determine what was lost
- **Restore from Backup**: Use most recent backup
- **Verify Integrity**: Check restored data
- **Update Version Control**: Commit restored data

#### Version Control Recovery
- **Check Git History**: Find last good commit
- **Reset to Good State**: Reset to working version
- **Review Changes**: Review what was lost
- **Recreate if Needed**: Recreate lost work

---

## 💡 Best Practices

### Organization Standards

#### Consistency
- **Same Structure**: Use same structure for all datasets
- **Same Naming**: Use consistent naming conventions
- **Same Metadata**: Use consistent metadata formats
- **Same Documentation**: Use consistent documentation

#### Professional Standards
- **Clear Documentation**: Comprehensive documentation
- **Version Control**: Proper version management
- **Quality Assurance**: Regular quality checks
- **Backup Systems**: Robust backup procedures

### Collaboration

#### Team Organization
- **Shared Standards**: Agree on organization standards
- **Clear Responsibilities**: Define team member roles
- **Communication**: Regular communication about changes
- **Documentation**: Document all decisions and changes

#### Sharing
- **Clear Licensing**: Clear usage terms
- **Good Documentation**: Comprehensive documentation
- **Version Control**: Proper version management
- **Quality Assurance**: Ensure shared data quality

---

## 🚀 What's Next?

Now that you understand dataset organization, you're ready to:

1. **[Image LoRA Datasets](image-lora-datasets.md)** - Create image LoRA datasets
2. **[Video LoRA Datasets](video-lora-datasets.md)** - Create video LoRA datasets
3. **[Dataset Validation and Testing](dataset-validation-and-testing.md)** - Ensure dataset quality

---

*Last updated: 2025-02-11*
