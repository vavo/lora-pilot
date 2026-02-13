# Complete Model Guide

LoRA Pilot supports an incredible variety of AI models - from classic Stable Diffusion to cutting-edge experimental models. This guide covers every model available, helping you choose the perfect one for your needs.

##  Model Categories

### 🖼️ Image Generation Models
Create images from text prompts

### 🎥 Video Generation Models  
Create videos from text or images

###  Specialized Models
Focused on specific styles or tasks

---

## 🖼️ Image Generation Models

### Stable Diffusion 1.5 Family

#### SD1.5 Base
- **What It Is**: The original Stable Diffusion model that started it all
- **Resolution**: 512×512 pixels (can go higher with upscaling)
- **VRAM Needed**: 4GB minimum, 8GB recommended
- **Speed**: Very fast (2-6 images/second on modern GPUs)
- **Best For**: Beginners, quick experiments, learning the basics

**Why Choose SD1.5:**
- **Fastest Generation**: Great for trying many ideas quickly
- **Low Requirements**: Works on older/cheaper GPUs
- **Huge Community**: Tons of tutorials and resources
- **Compatible**: Works with almost all LoRA and tools

**Perfect For:**
- Learning AI image generation
- Quick concept testing
- Creating simple images
- Older computers with limited VRAM

#### SD1.5 Variants
- **Realistic Vision**: Better at photorealism
- **DreamShaper**: Enhanced artistic capabilities
- **Anything V3**: Popular for anime/manga style

---

### Stable Diffusion XL Family

#### SDXL Base 1.0
- **What It Is**: High-resolution successor to SD1.5
- **Resolution**: 1024×1024 pixels (native)
- **VRAM Needed**: 8GB minimum, 12GB recommended
- **Speed**: Medium (1-3 images/second)
- **Best For**: Professional work, high-quality images

**Why Choose SDXL:**
- **Much Higher Quality**: Significantly better than SD1.5
- **Better Prompt Following**: Understands complex prompts better
- **Professional Results**: Commercial-quality images
- **Standard Today**: Industry standard for quality work

**Perfect For:**
- Professional art and design
- Print-quality images
- Complex scenes and compositions
- Users with good GPUs

#### SDXL Refiner
- **What It Is**: Enhancement model for SDXL
- **How It Works**: Takes SDXL output and adds detail
- **VRAM Needed**: 8GB+ (used with SDXL)
- **Speed**: Slower but worth it for quality
- **Best For**: Final polish on important images

**Why Use Refiner:**
- **Extra Detail**: Adds fine details SDXL might miss
- **Better Textures**: Improves surface quality
- **Professional Polish**: Final touch for client work

**Perfect For:**
- Portfolio pieces
- Client presentations
- Print work
- When quality matters most

#### SDXL Turbo
- **What It Is**: Fast version of SDXL
- **Speed**: Very fast (10+ images/second)
- **Quality**: Good, slightly less than regular SDXL
- **VRAM Needed**: 6GB+
- **Best For**: Quick iterations and testing

**Why Choose SDXL Turbo:**
- **Speed + Quality**: Best of both worlds
- **Real-time Use**: Fast enough for interactive use
- **Good Balance**: Quality close to SDXL, speed like SD1.5

**Perfect For:**
- Rapid prototyping
- Interactive applications
- Testing ideas quickly
- When you need speed AND quality

---

### Stable Diffusion 3 Family

#### SD3 Medium
- **What It Is**: Latest generation with improved architecture
- **Resolution**: 1024×1024 pixels
- **VRAM Needed**: 12GB minimum, 16GB recommended
- **Speed**: Medium-slow (1-2 images/second)
- **Best For**: Latest features, best prompt understanding

**Why Choose SD3:**
- **Best Prompt Understanding**: Understands complex sentences naturally
- **Improved Composition**: Better spatial relationships
- **Natural Results**: More realistic and coherent
- **Future-Proof**: Latest AI architecture

**Perfect For:**
- Complex, detailed prompts
- Natural language descriptions
- Users wanting the latest tech
- Professional quality work

---

### FLUX.1 Family

#### FLUX.1 Dev
- **What It Is**: State-of-the-art model from Black Forest Labs
- **Resolution**: 1024×1024+ (flexible)
- **VRAM Needed**: 12GB minimum, 16GB+ recommended
- **Speed**: Slow (0.5-1 images/second)
- **Best For**: Absolute best quality available

**Why Choose FLUX.1 Dev:**
- **Outstanding Quality**: Currently one of the best available
- **Natural Language**: Understands prompts like a person
- **Flexible Resolution**: Works at various sizes
- **Cutting Edge**: Latest AI technology

**Perfect For:**
- Professional art
- High-end commercial work
- When quality is the only priority
- Users with powerful GPUs

#### FLUX.1 Schnell
- **What It Is**: Fast version of FLUX.1
- **Speed**: Medium (2-4 images/second)
- **Quality**: Excellent (close to Dev)
- **VRAM Needed**: 12GB+
- **Best For**: Great quality with reasonable speed

**Why Choose FLUX.1 Schnell:**
- **Quality + Speed**: Best balance available
- **Open Model**: Fewer restrictions than Dev
- **Great Results**: Nearly Dev quality at better speed
- **Practical Choice**: Most practical FLUX option

**Perfect For:**
- High-quality art
- Professional work
- Users wanting FLUX quality without extreme slowness
- Balance of quality and speed

---

## 🎥 Video Generation Models

### LTX/LTX2 Family

#### LTX Base
- **What It Is**: Video generation model from Lightricks
- **Resolution**: 768×512 pixels
- **Length**: 4-10 seconds
- **VRAM Needed**: 8GB+
- **Speed**: Medium (1-2 minutes per video)
- **Best For**: Short video clips, animations

**Why Choose LTX:**
- **Good Quality**: Decent video generation
- **Reasonable Speed**: Faster than many video models
- **Consistent Results**: Reliable output quality
- **Growing Ecosystem**: Active development

**Perfect For:**
- Social media content
- Short animations
- Concept videos
- Video prototyping

#### LTX2 Base
- **What It Is**: Improved version of LTX
- **Improvements**: Better quality, more consistent
- **Features**: Enhanced motion and detail
- **VRAM Needed**: 8GB+
- **Best For**: Better video quality than original LTX

---

### HunyuanVideo Family

#### HunyuanVideo Base
- **What It Is**: Video model from Tencent
- **Resolution**: 720p to 1080p
- **Length**: 2-6 seconds
- **VRAM Needed**: 12GB+
- **Speed**: Slow (2-5 minutes per video)
- **Best For**: High-quality video generation

**Why Choose HunyuanVideo:**
- **High Quality**: Among the best video models
- **Chinese Content**: Excellent for Asian subjects
- **Professional Results**: Commercial-quality video
- **Advanced Features**: Latest video AI tech

**Perfect For:**
- Professional video content
- High-end animations
- Commercial video production
- Users wanting best video quality

---

### Cosmos Family

#### Cosmos Base
- **What It Is**: NVIDIA's video generation model
- **Resolution**: Variable (up to 4K)
- **Length**: 2-8 seconds
- **VRAM Needed**: 12GB+
- **Speed**: Variable (depends on resolution)
- **Best For**: High-end video production

**Why Choose Cosmos:**
- **NVIDIA Ecosystem**: Optimized for NVIDIA hardware
- **High Resolution**: Can generate 4K video
- **Professional Grade**: Built for professional use
- **Advanced Features**: Latest video AI research

**Perfect For:**
- 4K video content
- Professional video production
- High-end commercial work
- NVIDIA GPU users

---

##  Specialized Models

### Chroma Family

#### Chroma Base
- **What It Is**: Artistic style model
- **Specialty**: Artistic and creative styles
- **VRAM Needed**: 8GB+
- **Speed**: Medium (2-4 images/second)
- **Best For**: Artistic and creative work

**Why Choose Chroma:**
- **Artistic Focus**: Designed for creative work
- **Style Variety**: Can generate many art styles
- **Creative Results**: Unique and artistic outputs
- **Quality**: Good for artistic purposes

**Perfect For:**
- Digital art
- Creative projects
- Style experimentation
- Artistic content creation

---

### Lumina-Image 2.0 Family

#### Lumina2 Base
- **What It Is**: Photorealistic focused model
- **Specialty**: Photorealistic images
- **VRAM Needed**: 8GB+
- **Speed**: Medium (2-3 images/second)
- **Best For**: Photorealistic images

**Why Choose Lumina2:**
- **Photorealism**: Excellent for photo-like images
- **Detail Oriented**: Great for fine details
- **Professional Quality**: Commercial-ready results
- **Reliable**: Consistent photorealistic output

**Perfect For:**
- Product photography
- Realistic portraits
- Commercial imagery
- Photorealistic art

---

### Wan2.1/Wan2.2 Family

#### Wan2.1 Base
- **What It Is**: Multimodal model
- **Specialty**: Text-to-image with understanding
- **VRAM Needed**: 8GB+
- **Speed**: Medium (2-4 images/second)
- **Best For**: Complex prompt understanding

#### Wan2.2 Base
- **What It Is**: Improved version of Wan2.1
- **Improvements**: Better understanding, higher quality
- **Features**: Enhanced multimodal capabilities
- **VRAM Needed**: 8GB+
- **Best For**: Advanced multimodal generation

**Why Choose Wan Models:**
- **Deep Understanding**: Better comprehension of complex prompts
- **Multimodal**: Can handle various input types
- **Advanced Features**: Latest AI research
- **Quality**: Good for specialized use cases

---

### Qwen-Image Family

#### Qwen-Image Base
- **What It Is**: Chinese language optimized model
- **Specialty**: Chinese text understanding
- **VRAM Needed**: 8GB+
- **Speed**: Medium (2-4 images/second)
- **Best For**: Chinese language prompts

**Why Choose Qwen-Image:**
- **Chinese Optimization**: Excellent for Chinese text
- **Cultural Understanding**: Better for Chinese cultural elements
- **Quality**: Good for Chinese-focused content
- **Specialized**: Fills specific market need

**Perfect For:**
- Chinese language content
- Cultural elements
- Asian market content
- Chinese text prompts

---

### Z-Image Family

#### Z-Image Base
- **What It Is**: Experimental model
- **Specialty**: Cutting-edge features
- **VRAM Needed**: 8GB+
- **Speed**: Variable (depends on features)
- **Best For**: Experimental and advanced users

#### Z-Image Turbo
- **What It Is**: Fast version of Z-Image
- **Speed**: Fast (5+ images/second)
- **Quality**: Good for experimental model
- **VRAM Needed**: 8GB+
- **Best For**: Quick experimental results

**Why Choose Z-Image:**
- **Experimental Features**: Access to latest AI research
- **Cutting Edge**: Try new capabilities first
- **Innovation**: Part of AI development
- **Future Ready**: Prepares for upcoming features

**Perfect For:**
- AI researchers
- Experimental artists
- Early adopters
- Users wanting latest features

---

##  Model Comparison Tables

### Quality vs Speed Comparison

| Model | Quality (1-10) | Speed (1-10) | VRAM Needed | Best For |
|-------|----------------|----------------|---------------|-----------|
| SD1.5 | 6 | 9 | 4GB+ | Beginners, speed |
| SDXL | 8 | 5 | 8GB+ | Professional work |
| SD3 | 9 | 4 | 12GB+ | Latest features |
| FLUX.1 Dev | 10 | 2 | 12GB+ | Maximum quality |
| FLUX.1 Schnell | 9 | 6 | 12GB+ | Quality + speed |
| LTX | 7 | 5 | 8GB+ | Video content |
| HunyuanVideo | 8 | 3 | 12GB+ | Professional video |

### Use Case Recommendations

### For Absolute Beginners
1. **Start with SD1.5**: Learn the basics with fast, forgiving model
2. **Move to SDXL**: When ready for better quality
3. **Try FLUX.1 Schnell**: For quality boost without extreme slowness

### For Professional Artists
1. **SDXL Base**: Reliable professional quality
2. **FLUX.1 Schnell**: When you need the best quality
3. **SDXL Refiner**: For final polish on important work

### For Video Creators
1. **LTX2**: Good balance of quality and speed
2. **HunyuanVideo**: When you need the best video quality
3. **Cosmos**: For 4K professional video

### For Experimental Users
1. **Z-Image**: Try latest experimental features
2. **SD3**: Experience newest architecture
3. **Wan2.2**: Advanced multimodal capabilities

## 💡 Choosing Your First Model

### Consider Your Hardware

#### Low-End Systems (4-6GB VRAM)
- **SD1.5**: Your best option
- **SDXL Turbo**: If you have 6GB and want better quality
- **Avoid**: FLUX.1, SD3, video models

#### Mid-Range Systems (8-12GB VRAM)
- **SDXL**: Great quality, reasonable speed
- **FLUX.1 Schnell**: If you want cutting-edge quality
- **LTX2**: For video generation

#### High-End Systems (16GB+ VRAM)
- **FLUX.1 Dev**: Maximum quality
- **SD3**: Latest architecture
- **Any Model**: You can run everything well

### Consider Your Goals

#### Speed Priority
1. **SD1.5**: Fastest overall
2. **SDXL Turbo**: Good quality + speed
3. **FLUX.1 Schnell**: Best quality in fast category

#### Quality Priority
1. **FLUX.1 Dev**: Absolute best quality
2. **SD3**: Latest architecture, excellent quality
3. **SDXL + Refiner**: Professional quality

#### Learning Priority
1. **SD1.5**: Easiest to learn with
2. **SDXL**: Industry standard
3. **FLUX.1 Schnell**: Modern but manageable

##  What's Next?

Now that you know all the models, you're ready to:

1. **[Generation Parameters](generation-parameters.md)** - Learn how to control generation
2. **[Prompting Fundamentals](prompting-fundamentals.md)** - Master prompt writing
3. **[Practical Examples](practical-examples.md)** - Try real-world projects

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)


