# Getting Started

Welcome to LoRA Pilot! This section will guide you through installing and setting up your all-in-one Stable Diffusion workspace. LoRA Pilot bundles dataset preparation, model management, training, inference, and media workflow tools into a single, persistent Docker container.

## 📋 What You'll Learn

- **System Requirements** - Hardware and software needed
- **Installation** - Step-by-step setup instructions
- **First Run** - Initial configuration and verification
- **Troubleshooting** - Common issues and solutions
- **Stable Diffusion 101** - Fundamentals of generation and prompting
- **LoRA Training 101** - Core training concepts and workflows
- **Datasets 101** - Dataset quality, collection, and preparation

## 🎯 Quick Overview

LoRA Pilot provides:
- **30+ training model families** (SD1, SD2, SDXL, SD3, FLUX.1, and more)
- **Three training stacks**: Kohya SS, AI Toolkit, Diffusion Pipe
- **Two inference engines**: ComfyUI, InvokeAI
- **Management tools**: ControlPilot, TagPilot, MediaPilot
- **Development environment**: JupyterLab, Code Server

## 🚀 Recommended Path

1. **Check System Requirements** → [System Requirements](system-requirements.md)
2. **Install LoRA Pilot** → [Installation Guide](installation.md)
3. **First Run Setup** → [First Run](first-run.md)
4. **If Issues Occur** → [Troubleshooting](troubleshooting.md)

## 📘 Learning Tracks

After setup, continue with these chapter guides:
- [Stable Diffusion 101](stable-diffusion-101/README.md)
- [LoRA Training 101](loRA-training-101/README.md)
- [Datasets 101](datasets-101/README.md)

## 💡 Before You Begin

- **Docker Desktop** is required (Windows/Mac) or Docker Engine (Linux)
- **NVIDIA GPU** recommended for training (8GB+ VRAM)
- **100GB+ free disk space** for models and datasets
- **16GB+ RAM** recommended (32GB+ for intensive training)

## 🔧 Installation Options

### Option A: Docker Compose (Recommended)
```bash
git clone https://github.com/vavo/lora-pilot.git
cd lora-pilot
docker-compose up -d
```

### Option B: Docker Desktop GUI
1. Open Docker Desktop
2. Click "+" → "Compose"
3. Select `docker-compose.yml`
4. Click "Start"

### Option C: Pre-built Image
```bash
docker run -d --gpus all -p 7878:7878 -v $(pwd)/workspace:/workspace vavo/lora-pilot:latest
```

## 📚 Next Steps

After installation, continue with:
- [First Run Guide](first-run.md) - Initial setup and configuration
- [Stable Diffusion 101](stable-diffusion-101/README.md) - Learn generation fundamentals
- [LoRA Training 101](loRA-training-101/README.md) - Train custom adapters
- [Datasets 101](datasets-101/README.md) - Build high-quality training data
- [User Guide](../user-guide/README.md) - Learn the interface
- [Training Workflows](../user-guide/training-workflows.md) - Start training

## 🆘 Need Help?

- **Troubleshooting** → [Common Issues](troubleshooting.md)
- **Community** → [GitHub Discussions](https://github.com/vavo/lora-pilot/discussions)
- **Issues** → [GitHub Issues](https://github.com/vavo/lora-pilot/issues)

---

*Last updated: 2025-02-11*
