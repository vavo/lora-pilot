# Model Management

Comprehensive guide to managing AI models in LoRA Pilot, including downloading, organizing, validating, and maintaining your model library.

## 🎯 Overview

LoRA Pilot provides a unified model management system that handles:
- **Model Downloads**: Automatic downloading from Hugging Face and other repositories
- **Organization**: Structured storage and categorization
- **Validation**: Integrity checking and compatibility verification
- **Version Control**: Track model versions and updates
- **Integration**: Seamless access across all components

## 📁 Model Storage Structure

### Directory Organization

```
/workspace/models/
├── stable-diffusion/          # Base checkpoint models
│   ├── sd15-base/
│   ├── sdxl-base/
│   ├── sd3-medium/
│   └── flux1-schnell/
├── lora/                      # LoRA models
│   ├── trained/               # Your trained LoRAs
│   ├── downloaded/            # Downloaded LoRAs
│   └── community/             # Community LoRAs
├── textual-inversion/         # Textual inversion models
├── hypernetworks/             # Hypernetwork models
├── controlnet/                # ControlNet models
├── vae/                       # VAE models
├── embeddings/                # Text embeddings
└── temp/                      # Temporary downloads
```

### Model Categories

#### Checkpoint Models
- **Base Models**: Primary generation models (SD1.5, SDXL, FLUX.1)
- **Refiner Models**: Enhancement models (SDXL Refiner)
- **Specialized Models**: Task-specific models (Inpainting, Depth)

#### Fine-Tuning Models
- **LoRA**: Low-Rank Adaptation models
- **Textual Inversion**: Text embedding models
- **Hypernetworks**: Network-based fine-tuning

#### Auxiliary Models
- **ControlNet**: Conditioning models
- **VAE**: Variational Autoencoder models
- **Embeddings**: Text embedding files

## 🚀 Model Downloads

### Using ControlPilot

#### Web Interface
1. Navigate to **Models** tab in ControlPilot
2. Browse available models by category
3. Click **Download** on desired models
4. Monitor download progress
5. Verify installation completion

#### Model Selection
```bash
# Available model categories:
- Base Models: SD1.5, SDXL, SD3, FLUX.1
- LoRA Models: Community and trained models
- Auxiliary Models: ControlNet, VAE, etc.
```

### Using CLI Commands

#### Basic Downloads
```bash
# Download specific models
docker exec lora-pilot models pull sdxl-base
docker exec lora-pilot models pull sd15-base
docker exec lora-pilot models pull flux1-schnell

# Download multiple models
docker exec lora-pilot models pull sdxl-base sd15-base flux1-schnell
```

#### Advanced Downloads
```bash
# Download with specific branch
docker exec lora-pilot models pull stabilityai/stable-diffusion-xl-base-1.0 --branch main

# Download to specific location
docker exec lora-pilot models pull sdxl-base --destination /workspace/models/custom/

# Force re-download
docker exec lora-pilot models pull sdxl-base --force
```

### Manual Downloads

#### Direct Download
```bash
# Access container shell
docker exec -it lora-pilot bash

# Download using wget
cd /workspace/models/stable-diffusion/
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors

# Download using git
git clone https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
```

#### Hugging Face CLI
```bash
# Login to Hugging Face
huggingface-cli login --token your_token_here

# Download repository
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 --local-dir /workspace/models/stable-diffusion/sdxl-base
```

## 📋 Model Configuration

### Models Manifest

#### Structure
```yaml
models:
  sdxl-base:
    name: "Stable Diffusion XL Base 1.0"
    description: "SDXL 1.0 base model for high-quality generation"
    type: "checkpoint"
    repo: "stabilityai/stable-diffusion-xl-base-1.0"
    files:
      - "sd_xl_base_1.0.safetensors"
      - "scheduler/scheduler_config.json"
      - "text_encoder/model.safetensors"
      - "tokenizer/tokenizer.json"
      - "vae/diffusion_pytorch_model.safetensors"
    tags: ["sdxl", "base", "official", "recommended"]
    size_gb: 6.9
    requirements:
      gpu_memory_gb: 8
      ram_gb: 16
      cuda_version: "12.1+"
    metadata:
      author: "Stability AI"
      license: "openrail-m"
      created_at: "2023-07-26"
```

#### Adding Custom Models
```yaml
# Add to config/models.manifest
my-custom-model:
  name: "My Custom Model"
  description: "Custom trained model for specific style"
  type: "checkpoint"
  repo: "my-username/my-custom-model"
  files:
    - "my_model.safetensors"
    - "config.json"
  tags: ["custom", "experimental", "artistic"]
  size_gb: 4.2
  requirements:
    gpu_memory_gb: 6
    ram_gb: 12
  local_path: "/workspace/models/custom/my_model.safetensors"
```

### Model Metadata

#### Automatic Detection
```bash
# Model information is automatically detected
# File size, format, compatibility
# Hardware requirements
# Model architecture
```

#### Manual Metadata
```yaml
# Add custom metadata for better organization
metadata:
  style: "photorealistic"
  subject: "portraits"
  training_data: "professional photographs"
  recommended_prompts: ["portrait photography", "professional headshot"]
  incompatible_with: ["sd15-base"]
```

## 🔍 Model Validation

### Integrity Checking

#### File Verification
```bash
# Validate model files
docker exec lora-pilot models validate sdxl-base

# Check all installed models
docker exec lora-pilot models validate --all

# Detailed validation
docker exec lora-pilot models validate sdxl-base --detailed
```

#### Compatibility Testing
```bash
# Test model loading
docker exec lora-pilot python -c "
import torch
from diffusers import StableDiffusionPipeline
pipe = StableDiffusionPipeline.from_pretrained('/workspace/models/stable-diffusion/sdxl-base')
print('✅ Model loads successfully')
print('VRAM required:', pipe.unet.config.sample_size * pipe.unet.config.cross_attention_dim)
"
```

### Performance Benchmarking

#### Loading Speed Test
```bash
# Benchmark model loading time
time docker exec lora-pilot python -c "
import torch
from diffusers import StableDiffusionPipeline
pipe = StableDiffusionPipeline.from_pretrained('/workspace/models/stable-diffusion/sdxl-base')
"
```

#### Generation Speed Test
```bash
# Benchmark generation speed
docker exec lora-pilot python -c "
import torch
from diffusers import StableDiffusionPipeline
pipe = StableDiffusionPipeline.from_pretrained('/workspace/models/stable-diffusion/sdxl-base')
pipe = pipe.to('cuda')
import time
start = time.time()
image = pipe('test prompt', num_inference_steps=20).images[0]
print('Generation time:', time.time() - start)
"
```

## 📊 Model Organization

### Tagging System

#### Standard Tags
```yaml
# Model type tags
tags: ["checkpoint", "lora", "textual-inversion", "controlnet", "vae"]

# Architecture tags
tags: ["sd15", "sdxl", "sd3", "flux", "custom"]

# Quality tags
tags: ["official", "community", "experimental", "featured"]

# Usage tags
tags: ["portrait", "landscape", "artistic", "anime", "photorealistic"]
```

#### Custom Tags
```yaml
# Add custom tags for specific workflows
tags: ["character-design", "style-transfer", "concept-art", "commercial"]
```

### Search and Filtering

#### By Type
```bash
# List specific model types
docker exec lora-pilot models list --type checkpoint
docker exec lora-pilot models list --type lora
docker exec lora-pilot models list --type controlnet
```

#### By Tags
```bash
# Filter by tags
docker exec lora-pilot models list --tag sdxl
docker exec lora-pilot models list --tag portrait
docker exec lora-pilot models list --tag official
```

#### By Requirements
```bash
# Filter by hardware requirements
docker exec lora-pilot models list --min-vram 8
docker exec lora-pilot models list --max-vram 12
```

### Version Management

#### Model Versions
```yaml
# Track different versions
sdxl-base-v1.0:
  name: "SDXL Base v1.0"
  version: "1.0.0"
  release_date: "2023-07-26"
  
sdxl-base-v1.1:
  name: "SDXL Base v1.1"
  version: "1.1.0"
  release_date: "2023-10-15"
  replaces: "sdxl-base-v1.0"
```

#### Update Management
```bash
# Check for model updates
docker exec lora-pilot models check-updates

# Update specific model
docker exec lora-pilot models update sdxl-base

# Update all models
docker exec lora-pilot models update --all
```

## 🔄 Integration with Components

### ComfyUI Integration

#### Model Discovery
```bash
# ComfyUI automatically discovers models
# Models appear in dropdown menus
# Custom models are included automatically
```

#### Model Loading
```python
# ComfyUI model loading
# CheckpointLoader node shows all available models
# LoRALoader node shows all LoRA models
# ControlNetLoader node shows ControlNet models
```

### Kohya SS Integration

#### Training Models
```bash
# Kohya SS uses models from /workspace/models/
# Base models for training
# VAE models for encoding/decoding
```

#### Model Selection
```yaml
# Kohya SS model configuration
pretrained_model_name_or_path: "/workspace/models/stable-diffusion/sdxl-base"
```

### AI Toolkit Integration

#### Model Configuration
```yaml
# AI Toolkit model configuration
model:
  name_or_path: "black-forest-labs/FLUX.1-schnell"
  # Automatically resolves to /workspace/models/
```

### InvokeAI Integration

#### Model Registry
```bash
# InvokeAI scans /workspace/models/ directory
# Models appear in InvokeAI interface
# Automatic model registration
```

## 🔧 Advanced Management

### Batch Operations

#### Batch Downloads
```bash
# Download model collections
docker exec lora-pilot models pull-collection "sdxl-starter-pack"
docker exec lora-pilot models pull-collection "flux-essentials"
```

#### Batch Validation
```bash
# Validate all models
docker exec lora-pilot models validate --all --fix-issues

# Validate specific categories
docker exec lora-pilot models validate --type lora
```

#### Batch Cleanup
```bash
# Remove unused models
docker exec lora-pilot models cleanup --unused-days 30

# Remove corrupted models
docker exec lora-pilot models cleanup --corrupted-only
```

### Storage Management

#### Disk Usage Analysis
```bash
# Analyze model storage usage
docker exec lora-pilot models usage --detailed

# Find large models
docker exec lora-pilot models usage --sort-by-size

# Usage by category
docker exec lora-pilot models usage --by-type
```

#### Storage Optimization
```bash
# Compress models (FP16)
docker exec lora-pilot models optimize --precision fp16 sdxl-base

# Remove duplicate models
docker exec lora-pilot models deduplicate

# Archive old models
docker exec lora-pilot models archive --older-than 90days
```

### Backup and Recovery

#### Model Backup
```bash
# Backup all models
docker exec lora-pilot models backup --destination /backup/models/

# Backup specific models
docker exec lora-pilot models backup --models sdxl-base,sd15-base --destination /backup/core-models/

# Incremental backup
docker exec lora-pilot models backup --incremental --destination /backup/models/
```

#### Model Recovery
```bash
# Restore from backup
docker exec lora-pilot models restore --source /backup/models/

# Restore specific models
docker exec lora-pilot models restore --models sdxl-base --source /backup/models/
```

## 🔍 Troubleshooting

### Common Issues

#### Model Not Loading
```bash
# Check model files
docker exec lora-pilot ls -la /workspace/models/stable-diffusion/sdxl-base/

# Check file integrity
docker exec lora-pilot models validate sdxl-base --detailed

# Check permissions
docker exec lora-pilot stat /workspace/models/stable-diffusion/sdxl-base/sd_xl_base_1.0.safetensors
```

#### Download Failures
```bash
# Check network connectivity
docker exec lora-pilot curl -I https://huggingface.co

# Check Hugging Face authentication
docker exec lora-pilot huggingface-cli whoami

# Retry download
docker exec lora-pilot models pull sdxl-base --retry
```

#### Out of Space
```bash
# Check disk usage
docker exec lora-pilot df -h /workspace/models/

# Clean up temporary files
docker exec lora-pilot models cleanup --temp-only

# Move models to external storage
docker exec lora-pilot models move --destination /external/models/
```

### Debug Commands

#### Model Information
```bash
# Get detailed model info
docker exec lora-pilot models info sdxl-base --json

# List all models with details
docker exec lora-pilot models list --detailed

# Check model dependencies
docker exec lora-pilot models dependencies sdxl-base
```

#### System Diagnostics
```bash
# Check model loading performance
docker exec lora-pilot models benchmark sdxl-base

# Test model compatibility
docker exec lora-pilot models test-compatibility sdxl-base

# Generate model report
docker exec lora-pilot models report --output /workspace/models-report.txt
```

## 🎯 Best Practices

### Model Selection
1. **Choose Appropriate Models**: Match model to use case
2. **Check Requirements**: Ensure hardware compatibility
3. **Read Documentation**: Understand model capabilities
4. **Test Before Use**: Validate model functionality

### Storage Management
1. **Plan Storage**: Allocate sufficient disk space
2. **Regular Cleanup**: Remove unused models
3. **Backup Important Models**: Save trained models externally
4. **Monitor Usage**: Track storage consumption

### Organization
1. **Use Consistent Naming**: Clear, descriptive names
2. **Add Metadata**: Include tags and descriptions
3. **Version Control**: Track model versions
4. **Document Sources**: Keep track of model origins

### Security
1. **Verify Sources**: Download from reputable sources
2. **Check Licenses**: Ensure appropriate usage rights
3. **Scan for Malware**: Validate model files
4. **Control Access**: Restrict model access if needed

---

*Last updated: 2025-02-11*
