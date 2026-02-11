# System Requirements

This guide outlines the hardware and software requirements for running LoRA Pilot effectively. Requirements vary based on your intended use case (inference vs training) and model complexity.

## 💻 Hardware Requirements

### Minimum Requirements (Inference Only)
- **CPU**: 4-core processor (Intel i5/AMD Ryzen 5 or better)
- **RAM**: 8GB (16GB recommended)
- **Storage**: 50GB free space (SSD recommended)
- **GPU**: Integrated graphics or any NVIDIA GPU with 4GB+ VRAM

### Recommended Requirements (Light Training)
- **CPU**: 8-core processor (Intel i7/AMD Ryzen 7 or better)
- **RAM**: 16GB (32GB recommended)
- **Storage**: 100GB+ free space (SSD required)
- **GPU**: NVIDIA RTX 20xx/30xx/40xx with 8GB+ VRAM

### Optimal Requirements (Heavy Training)
- **CPU**: 12+ core processor (Intel i9/AMD Ryzen 9 or better)
- **RAM**: 32GB+ (64GB recommended)
- **Storage**: 500GB+ NVMe SSD
- **GPU**: NVIDIA RTX 3080/4080/4090 with 16GB+ VRAM

## 🎮 GPU Compatibility

### Supported NVIDIA GPUs
| GPU Series | VRAM Range | Training Performance |
|------------|------------|---------------------|
| RTX 20xx | 6-11GB | Good for SD1.5/SDXL |
| RTX 30xx | 8-24GB | Excellent for all models |
| RTX 40xx | 8-24GB | Best performance, DLSS 3 |
| RTX Ada (40xx) | 12-48GB | Professional training |

### GPU-Specific Notes
- **RTX 3060 (12GB)**: Great value for SDXL training
- **RTX 3080 (10GB)**: Excellent balance of price/performance
- **RTX 4090 (24GB)**: Best consumer GPU for training
- **RTX 6000 Ada (48GB)**: Professional workstation choice

### CUDA Requirements
- **CUDA Version**: 12.4+ (included in Docker image)
- **Driver Version**: 525.60.13+ (Linux), 527.41+ (Windows)
- **Compute Capability**: 7.0+ (Turing architecture or newer)

## 🖥️ Software Requirements

### Docker Platform
#### Windows
- **Windows 10/11** (64-bit, Pro/Enterprise recommended)
- **Docker Desktop for Windows** 4.20+
- **WSL2** enabled (Windows Subsystem for Linux)
- **Hyper-V** enabled

#### macOS
- **macOS 11+** (Big Sur or newer)
- **Docker Desktop for Mac** 4.20+
- **Apple Silicon (M1/M2/M3)** or Intel-based Mac

#### Linux
- **Ubuntu 20.04+** / **CentOS 8+** / **Debian 11+**
- **Docker Engine** 20.10+
- **NVIDIA Container Toolkit** (for GPU support)
- **NVIDIA Drivers** 525.60.13+

### Optional Software
- **Git** - For cloning repository and version control
- **VS Code** - For configuration file editing
- **Terminal/PowerShell** - For command-line operations

## 📊 Storage Requirements

### Base Installation
- **Docker Image**: ~15-20GB
- **Base Models**: ~10GB (SD1.5, SDXL, FLUX.1)
- **Workspace**: ~5GB initial

### Per Training Project
- **Dataset**: 1-10GB (depending on image count)
- **Checkpoints**: 500MB-2GB per LoRA
- **Intermediate Files**: 5-20GB (latents, logs)
- **Final Models**: 100MB-1GB per trained model

### Recommended Storage Planning
- **SSD for Active Work**: 500GB+ (fast access for training)
- **HDD for Archive**: 2TB+ (model/dataset storage)
- **Cloud Backup**: Optional (Google Drive, AWS S3)

## 🌐 Network Requirements

### Internet Connection
- **Initial Setup**: 50+ Mbps (for downloading base models)
- **Model Downloads**: 100+ Mbps recommended
- **Dataset Uploads**: 10+ Mbps (if using cloud storage)

### Port Requirements
LoRA Pilot uses the following ports by default:
- **7878** - ControlPilot (main interface)
- **5555** - ComfyUI
- **6666** - Kohya SS
- **9090** - InvokeAI
- **8888** - JupyterLab
- **8443** - Code Server
- **8675** - AI Toolkit UI

## 🔍 Performance Benchmarks

### Training Speed (Images/Second)
| GPU | SD1.5 | SDXL | FLUX.1 |
|-----|-------|------|--------|
| RTX 3060 (12GB) | 2.5 | 1.2 | 0.4 |
| RTX 3080 (10GB) | 3.8 | 1.8 | 0.6 |
| RTX 4090 (24GB) | 6.2 | 3.1 | 1.1 |

### Inference Speed (Images/Second)
| GPU | SD1.5 | SDXL | FLUX.1 |
|-----|-------|------|--------|
| RTX 3060 (12GB) | 15 | 8 | 3 |
| RTX 3080 (10GB) | 22 | 12 | 5 |
| RTX 4090 (24GB) | 35 | 20 | 9 |

## ⚠️ Common Issues and Solutions

### GPU Memory Issues
- **Problem**: "CUDA out of memory" errors
- **Solution**: Reduce batch size, use gradient checkpointing, or upgrade GPU

### Storage Issues
- **Problem**: Slow training due to disk I/O
- **Solution**: Use SSD for workspace, increase RAM for caching

### Docker Issues
- **Problem**: Container fails to start
- **Solution**: Check Docker Desktop status, verify WSL2 setup (Windows)

## 📱 Virtualization Support

### Cloud Platforms
- **AWS**: G4/G5 instances (NVIDIA GPUs)
- **Google Cloud**: A2/A3 instances (NVIDIA GPUs)
- **Azure**: NCasT4_v3 instances (NVIDIA GPUs)
- **RunPod**: Various GPU options, cost-effective

### Virtual Machines
- **VMware**: GPU passthrough supported
- **VirtualBox**: Limited GPU support (CPU only)
- **Proxmox**: GPU passthrough with PCIe configuration

## 🎯 Recommendations by Use Case

### Casual Users (Inference Only)
- **GPU**: RTX 3060 (12GB) or M1/M2 Mac
- **RAM**: 16GB
- **Storage**: 256GB SSD

### Hobbyist Trainers
- **GPU**: RTX 4060 Ti (16GB) or RTX 3080 (10GB)
- **RAM**: 32GB
- **Storage**: 1TB NVMe SSD

### Professional Trainers
- **GPU**: RTX 4090 (24GB) or RTX 6000 Ada (48GB)
- **RAM**: 64GB+
- **Storage**: 2TB+ NVMe SSD + archive storage

---

*Last updated: 2025-02-11*
