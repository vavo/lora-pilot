# Supported Models

LoRA Pilot supports a comprehensive range of AI models for training and inference. This reference covers all supported model families, their requirements, and use cases.

##  Model Families Overview

| Family | Training | Inference | VRAM Required | Best For |
|--------|----------|-----------|---------------|-----------|
| **Stable Diffusion 1.5** | ✅ | ✅ | 4GB+ | Beginners, compatibility |
| **Stable Diffusion XL** | ✅ | ✅ | 8GB+ | High quality, standard |
| **Stable Diffusion 3** | ✅ | ✅ | 12GB+ | Latest features, quality |
| **FLUX.1** | ✅ | ✅ | 12GB+ | State-of-the-art |
| **Chroma** | ✅ | ✅ | 8GB+ | Artistic styles |
| **Lumina-Image 2.0** | ✅ | ✅ | 8GB+ | Photorealistic |
| **LTX/LTX2** | ✅ | ✅ | 8GB+ | Video generation |
| **HunyuanVideo** | ✅ | ✅ | 12GB+ | Video generation |
| **Wan2.1/Wan2.2** | ✅ | ✅ | 8GB+ | Multimodal |
| **Cosmos** | ✅ | ✅ | 12GB+ | Video generation |
| **HiDream** | ✅ | ✅ | 8GB+ | Dream-like images |
| **Qwen-Image** | ✅ | ✅ | 8GB+ | Text-to-image |
| **Z-Image** | ✅ | ✅ | 8GB+ | Experimental |

## 🖼️ Stable Diffusion Models

### Stable Diffusion 1.5

**Requirements:**
- **VRAM**: 4GB+ (training), 2GB+ (inference)
- **RAM**: 8GB+
- **Resolution**: 512x512

**Available Models:**
- `sd15-base` - RunwayML Stable Diffusion 1.5
- `sd15-inpainting` - Inpainting model
- `sd15-depth` - Depth-aware model
- `sd15-pix2pix` - Image-to-image

**Training Support:**
- ✅ LoRA training
- ✅ DreamBooth training
- ✅ Textual Inversion
- ✅ Hypernetworks

**Use Cases:**
- Beginner training
- Fast inference
- Community models
- Extensive ecosystem

### Stable Diffusion XL

**Requirements:**
- **VRAM**: 8GB+ (training), 4GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 1024x1024

**Available Models:**
- `sdxl-base` - Stability AI SDXL Base 1.0
- `sdxl-refiner` - SDXL Refiner
- `sdxl-turbo` - Fast inference model
- `sdxl-inpainting` - Inpainting model

**Training Support:**
- ✅ LoRA training
- ✅ DreamBooth training
- ✅ Textual Inversion
- ✅ ControlNet

**Use Cases:**
- High-quality generation
- Professional work
- Commercial applications
- Fine details

### Stable Diffusion 3

**Requirements:**
- **VRAM**: 12GB+ (training), 8GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 1024x1024

**Available Models:**
- `sd3-medium` - Stable Diffusion 3 Medium
- `sd3-large` - Stable Diffusion 3 Large (coming soon)

**Training Support:**
- ✅ LoRA training (experimental)
- ✅ DreamBooth training (experimental)
- ⚠️ Textual Inversion (limited)

**Use Cases:**
- Latest generation
- Better prompt following
- Improved quality
- Experimental features

## 🌊 FLUX.1 Models

### FLUX.1 Dev

**Requirements:**
- **VRAM**: 12GB+ (training), 8GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 1024x1024 (up to 2048x2048)

**Available Models:**
- `flux1-dev` - FLUX.1 Dev ( gated model)
- `flux1-dev-fp8` - FP8 quantized version

**Training Support:**
- ✅ LoRA training (AI Toolkit)
- ✅ DreamBooth training (experimental)
- ❌ Textual Inversion (not supported)

**Use Cases:**
- State-of-the-art quality
- Artistic generation
- Complex prompts
- High-resolution output

### FLUX.1 Schnell

**Requirements:**
- **VRAM**: 12GB+ (training), 8GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 1024x1024

**Available Models:**
- `flux1-schnell` - FLUX.1 Schnell ( gated model)
- `flux1-schnell-fp8` - FP8 quantized version

**Training Support:**
- ✅ LoRA training (AI Toolkit)
- ❌ DreamBooth training (limited)
- ❌ Textual Inversion (not supported)

**Use Cases:**
- Fast generation
- Iterative workflows
- Prototyping
- Real-time applications

##  Artistic Models

### Chroma

**Requirements:**
- **VRAM**: 8GB+ (training), 4GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 1024x1024

**Available Models:**
- `chroma-base` - Base Chroma model
- `chroma-xl` - XL version

**Training Support:**
- ✅ LoRA training
- ✅ DreamBooth training
- ⚠️ Textual Inversion (limited)

**Use Cases:**
- Artistic styles
- Creative applications
- Style transfer
- Experimental art

### Lumina-Image 2.0

**Requirements:**
- **VRAM**: 8GB+ (training), 4GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 1024x1024

**Available Models:**
- `lumina2-base` - Lumina-Image 2.0 Base
- `lumina2-xl` - XL version

**Training Support:**
- ✅ LoRA training (experimental)
- ⚠️ DreamBooth training (limited)

**Use Cases:**
- Photorealistic generation
- High-quality images
- Professional photography
- Commercial use

## 🎥 Video Models

### LTX/LTX2

**Requirements:**
- **VRAM**: 8GB+ (training), 6GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 768x512

**Available Models:**
- `ltx-base` - LTX Base model
- `ltx2-base` - LTX2 Base model

**Training Support:**
- ✅ LoRA training (experimental)
- ❌ DreamBooth training (not supported)

**Use Cases:**
- Video generation
- Animation
- Creative video
- Prototyping

### HunyuanVideo

**Requirements:**
- **VRAM**: 12GB+ (training), 8GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 720p, 1080p

**Available Models:**
- `hunyuanvideo-base` - Base video model
- `hunyuanvideo-t2v` - Text-to-video

**Training Support:**
- ✅ LoRA training (experimental)
- ❌ DreamBooth training (not supported)

**Use Cases:**
- High-quality video
- Chinese content
- Commercial video
- Professional applications

### Cosmos

**Requirements:**
- **VRAM**: 12GB+ (training), 8GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: Variable

**Available Models:**
- `cosmos-base` - Base Cosmos model
- `cosmos-t2v` - Text-to-video

**Training Support:**
- ✅ LoRA training (experimental)
- ❌ DreamBooth training (not supported)

**Use Cases:**
- NVIDIA ecosystem
- High-performance video
- Research applications
- Advanced workflows

##  Multimodal Models

### Wan2.1/Wan2.2

**Requirements:**
- **VRAM**: 8GB+ (training), 4GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 1024x1024

**Available Models:**
- `wan21-base` - Wan2.1 Base
- `wan22-base` - Wan2.2 Base
- `wan22-xl` - Wan2.2 XL

**Training Support:**
- ✅ LoRA training (experimental)
- ⚠️ DreamBooth training (limited)

**Use Cases:**
- Multimodal generation
- Text-to-image
- Image-to-image
- Research applications

### Qwen-Image

**Requirements:**
- **VRAM**: 8GB+ (training), 4GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 1024x1024

**Available Models:**
- `qwen-image-base` - Base model
- `qwen-image-xl` - XL version

**Training Support:**
- ✅ LoRA training (experimental)
- ⚠️ DreamBooth training (limited)

**Use Cases:**
- Chinese language support
- Multimodal understanding
- Text generation
- Image understanding

### Z-Image

**Requirements:**
- **VRAM**: 8GB+ (training), 4GB+ (inference)
- **RAM**: 16GB+
- **Resolution**: 1024x1024

**Available Models:**
- `z-image-base` - Base model
- `z-image-xl` - XL version

**Training Support:**
- ✅ LoRA training (experimental)
- ⚠️ DreamBooth training (limited)

**Use Cases:**
- Experimental models
- Research applications
- Cutting-edge features
- Prototyping

##  Model Requirements by GPU

### NVIDIA RTX 20xx Series (6-8GB VRAM)
**Recommended Models:**
- ✅ SD1.5 (training + inference)
- ✅ SDXL (inference only)
- ✅ FLUX.1 (inference only, FP8)
- ⚠️ SD3 (inference only)

### NVIDIA RTX 30xx Series (8-12GB VRAM)
**Recommended Models:**
- ✅ SD1.5 (training + inference)
- ✅ SDXL (training + inference)
- ✅ FLUX.1 (inference, limited training)
- ✅ SD3 (inference, limited training)

### NVIDIA RTX 40xx Series (12-24GB VRAM)
**Recommended Models:**
- ✅ All models (training + inference)
- ✅ High-resolution training
- ✅ Batch processing
- ✅ Experimental features

##  Training Compatibility Matrix

| Model | Kohya SS | AI Toolkit | Diffusion Pipe | DreamBooth | LoRA | Textual Inversion |
|-------|----------|------------|----------------|------------|------|-------------------|
| SD1.5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SDXL | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SD3 | ⚠️ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ |
| FLUX.1 | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Chroma | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ |
| Lumina | ⚠️ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ |
| Video Models | ❌ | ⚠️ | ✅ | ❌ | ⚠️ | ❌ |

**Legend:**
- ✅ Full support
- ⚠️ Limited/experimental support
- ❌ Not supported

## 📦 Model Download Commands

### Quick Downloads

```bash
# Essential models
models pull sd15-base
models pull sdxl-base
models pull flux1-schnell

# Specialized models
models pull chroma-base
models pull lumina2-base
models pull wan22-base

# Video models
models pull ltx-base
models pull hunyuanvideo-base
```

### Batch Downloads

```bash
# All SD models
models pull sd15-base sdxl-base sd3-medium

# All FLUX models
models pull flux1-dev flux1-schnell

# All video models
models pull ltx-base hunyuanvideo-base cosmos-base
```

### Model Information

```bash
# Check model requirements
models info sdxl-base --requirements

# List available models
models list --type checkpoint

# Check installed models
models list --installed
```

##  Model Selection Guide

### For Beginners
1. **Start with SD1.5** - Lower requirements, extensive community
2. **Move to SDXL** - Higher quality, moderate requirements
3. **Try FLUX.1 Schnell** - Latest features, fast inference

### For Professionals
1. **SDXL** - Standard for professional work
2. **FLUX.1 Dev** - State-of-the-art quality
3. **Custom models** - Train specialized models

### For Researchers
1. **SD3** - Latest architecture
2. **Experimental models** - Cutting-edge features
3. **Video models** - Video generation research

### For Commercial Use
1. **SDXL** - Commercial-friendly license
2. **FLUX.1** - Check license requirements
3. **Custom training** - Proprietary models

## ⚠️ License Considerations

### Commercial Use
- **SD1.5**: CreativeML OpenRAIL-M
- **SDXL**: CreativeML OpenRAIL-M
- **FLUX.1**: Check specific license terms
- **Custom models**: Depends on training data

### Research Use
- Most models allow research use
- Check specific model licenses
- Attribute appropriately

### Attribution Requirements
- Some models require attribution
- Check model documentation
- Include proper credits

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


