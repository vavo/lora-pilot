# First Run Guide

Congratulations on installing LoRA Pilot! This guide will walk you through the initial setup, configuration, and verification steps to ensure everything is working correctly.

## 🚀 Initial Startup

### 1. Verify Container Status

First, check that all services are running:

```bash
# Check container status
docker-compose ps

# You should see all services as "Up" or "running"
```

### 2. Access ControlPilot

Open your web browser and navigate to:
- **ControlPilot**: http://localhost:7878

The first load may take 2-5 minutes as services initialize. You'll see the LoRA Pilot dashboard once ready.

### 3. Verify GPU Access

If you have an NVIDIA GPU, verify it's detected:

```bash
# Check GPU from inside container
docker exec lora-pilot nvidia-smi

# You should see your GPU details
```

## 📋 Initial Configuration

### Environment Setup

Create your personal configuration:

```bash
# Create environment file
cp .env.example .env

# Edit configuration (optional)
nano .env
```

Key settings to consider:
- `TZ` - Set your timezone
- `SUPERVISOR_ADMIN_PASSWORD` - Secure supervisor access
- `HF_TOKEN` - Add Hugging Face token for private models

### Workspace Structure

LoRA Pilot creates this workspace structure:

```
/workspace/
├── datasets/           # Training datasets
├── outputs/           # Training outputs and checkpoints
├── models/            # Downloaded models
│   ├── checkpoints/   # Training checkpoints
│   └── stable-diffusion/  # Base models
├── cache/             # Caching and temporary files
├── config/            # Configuration files
└── home/              # User home directory
```

## 🎯 Service Verification

### Check All Services

In ControlPilot, navigate to the **Services** tab. Verify these services are running:

| Service | Port | Purpose |
|---------|------|---------|
| ControlPilot | 7878 | Main web interface |
| ComfyUI | 5555 | Node-based inference |
| Kohya SS | 6666 | LoRA training UI |
| InvokeAI | 9090 | Dedicated inference |
| JupyterLab | 8888 | Notebook environment |
| Code Server | 8443 | VS Code in browser |
| AI Toolkit | 8675 | Modern training interface |

### Test Individual Services

#### ComfyUI
1. Click "Open" next to ComfyUI in Services
2. Should load the node editor interface
3. Try loading a simple workflow

#### Kohya SS
1. Open Kohya SS from Services
2. Navigate to "Training" → "LoRA"
3. Should show training configuration options

#### JupyterLab
1. Open JupyterLab
2. Create a new Python notebook
3. Test with: `import torch; print(torch.cuda.is_available())`

## 📦 Download Base Models

### Using ControlPilot

1. Go to **Models** tab in ControlPilot
2. Click "Download Models"
3. Select essential models:
   - `sdxl-base` - SDXL 1.0 base model
   - `sdxl-refiner` - SDXL refiner (optional)
   - `sd15-base` - Stable Diffusion 1.5 (for compatibility)

### Using CLI

```bash
# Access container shell
docker exec -it lora-pilot bash

# Download essential models
models pull sdxl-base
models pull sd15-base

# List available models
models list
```

### Manual Download (Advanced)

```bash
# Download specific model from Hugging Face
cd /workspace/models/stable-diffusion
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

## 🧪 Quick Training Test

### Create Test Dataset

1. Navigate to **TagPilot** in ControlPilot
2. Upload 5-10 test images
3. Add simple captions (e.g., "a photo of a cat")
4. Export as dataset

### Run Quick Training

1. Go to **TrainPilot** in ControlPilot
2. Select your test dataset
3. Choose "quick_test" profile
4. Set 10-20 steps for testing
5. Start training

### Verify Results

After training completes:
1. Check `/workspace/outputs/` for your LoRA
2. Test in ComfyUI by loading your trained LoRA
3. Verify the training effect

## 🔧 Common First-Run Tasks

### Set Up Authentication

#### Hugging Face Token (Required for some models)
```bash
# In container shell
export HF_TOKEN="your_token_here"
huggingface-cli login
```

#### GitHub Copilot (Optional)
```bash
# In container shell
copilot
/login  # Follow authentication prompts
```

### Configure Storage

#### Check Disk Space
```bash
# Check workspace usage
df -h /workspace

# Check model sizes
du -sh /workspace/models/
```

#### Set Up External Storage (Optional)
```bash
# Mount external drive (Linux)
sudo mount /dev/sdb1 /mnt/external

# Update docker-compose.yml to mount external storage
volumes:
  - /mnt/external:/workspace/external
```

### Network Configuration

#### Port Forwarding (If needed)
If ports are blocked, you can change them in `docker-compose.yml`:

```yaml
services:
  lora-pilot:
    ports:
      - "8080:7878"    # Change ControlPilot to 8080
      - "5556:5555"    # Change ComfyUI to 5556
```

#### Remote Access
For accessing from other machines:
```bash
# Allow remote connections (development only)
# In docker-compose.yml:
ports:
  - "0.0.0.0:7878:7878"  # Allow all IPs
```

## 🐛 Troubleshooting First Issues

### Services Won't Start

```bash
# Check logs for specific service
docker-compose logs kohya
docker-compose logs comfyui

# Restart specific service
docker-compose restart kohya
```

### GPU Not Available

```bash
# Check GPU detection
docker exec lora-pilot nvidia-smi

# Check CUDA in Python
docker exec lora-pilot python -c "import torch; print(torch.cuda.is_available())"
```

### Out of Memory Errors

```bash
# Check memory usage
docker stats lora-pilot

# Reduce batch size in training configs
# Or use CPU-only mode for testing
```

### Slow Performance

```bash
# Check disk I/O
iotop  # Linux
Activity Monitor  # macOS
Task Manager  # Windows

# Consider moving workspace to faster storage
```

## 📱 Mobile Access

For tablet/mobile access:

1. **Find your IP address**:
   ```bash
   # Linux/macOS
   ip addr show | grep inet
   
   # Windows
   ipconfig
   ```

2. **Access from mobile**:
   - http://YOUR_IP:7878
   - Ensure firewall allows connections

## 🎯 Next Steps

Once everything is verified:

1. **[User Guide](../user-guide/README.md)** - Learn all features
2. **[Training Workflows](../user-guide/training-workflows.md)** - Start serious training
3. **[Model Management](../user-guide/model-management.md)** - Organize your models
4. **[Configuration](../configuration/README.md)** - Customize your setup

## 📊 Performance Baseline

Run this benchmark to establish your baseline:

```bash
# In container shell
python -c "
import torch
import time
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Device: {device}')
if device == 'cuda':
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB')
"
```

Record these metrics for future performance comparisons.

---

*Last updated: 2025-02-11*
