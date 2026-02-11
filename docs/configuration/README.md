# Configuration Overview

LoRA Pilot offers extensive configuration options to customize your AI workspace. This section covers all configuration aspects from basic environment variables to advanced custom setups.

## ⚙️ Configuration Hierarchy

LoRA Pilot uses a layered configuration system:

```
Configuration Priority (highest to lowest)
1. Environment Variables (runtime)
2. Docker Compose (-f flags)
3. .env files (local)
4. Default configurations (built-in)
```

## 📁 Configuration Files

### Core Configuration Files
```
lora-pilot/
├── .env.example                    # Environment variables template
├── .env                            # Your local configuration
├── docker-compose.yml              # Main service configuration
├── docker-compose.cpu.yml          # CPU-only configuration
├── docker-compose.dev.yml          # Development configuration
├── Dockerfile                      # Build configuration
└── config/
    ├── env.defaults                # Default environment values
    ├── models.manifest.default    # Available models list
    └── models.manifest             # Custom model configurations
```

### Runtime Configuration
```
/workspace/
├── config/
│   ├── ai-toolkit/                 # AI Toolkit database
│   ├── jupyter/                    # JupyterLab settings
│   ├── code-server/               # VS Code settings
│   └── supervisor/                 # Service configurations
```

## 🌍 Environment Variables

### Core Variables

#### System Configuration
```bash
# Timezone
TZ=America/New_York

# Supervisor admin password
SUPERVISOR_ADMIN_PASSWORD=your_secure_password

# Workspace directory (usually /workspace)
WORKSPACE_DIR=/workspace
```

#### Component Installation
```bash
# Component installation flags
INSTALL_GPU_STACK=1
INSTALL_INVOKE=1
INSTALL_KOHYA=1
INSTALL_COMFYUI=1
INSTALL_DIFFPIPE=1
INSTALL_COPILOT_CLI=1
INSTALL_AI_TOOLKIT=1
INSTALL_AI_TOOLKIT_UI=1
```

#### Authentication Tokens
```bash
# Hugging Face token (for private models)
HF_TOKEN=your_huggingface_token_here
HUGGINGFACE_HUB_TOKEN=your_huggingface_token_here

# GitHub Copilot token
COPILOT_GITHUB_TOKEN=your_github_token_here
```

#### AI Toolkit Configuration
```bash
# AI Toolkit settings
AI_TOOLKIT_REF=main
AI_TOOLKIT_DIFFUSERS_VERSION=0.36.0
DATABASE_URL=file:/workspace/config/ai-toolkit/aitk_db.db
```

#### Version Pins
```bash
# PyTorch versions
TORCH_VERSION=2.6.0
TORCHVISION_VERSION=0.21.0
TORCHAUDIO_VERSION=2.6.0
INVOKE_TORCH_VERSION=2.7.0
INVOKE_TORCHVISION_VERSION=0.22.0
INVOKE_TORCHAUDIO_VERSION=2.7.0

# Library versions
XFORMERS_VERSION=0.0.29.post3
TRANSFORMERS_VERSION=4.44.2
PEFT_VERSION=0.17.0
```

#### Port Configuration
```bash
# Service ports
JUPYTER_PORT=8888
CODE_SERVER_PORT=8443
COMFY_PORT=5555
KOHYA_PORT=6666
INVOKE_PORT=9090
DIFFPIPE_PORT=4444
```

#### GPU Configuration
```bash
# NVIDIA GPU settings
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility,display
CUDA_VISIBLE_DEVICES=0
```

### Performance Tuning Variables

#### Memory Management
```bash
# PyTorch memory settings
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"

# Triton settings
TRITON_DISABLE=1
TORCHINDUCTOR_DISABLE=1
```

#### Training Optimization
```bash
# Gradient settings
GRADIENT_ACCUMULATION_STEPS=1
GRADIENT_CHECKPOINTING=true

# Batch size settings
DEFAULT_BATCH_SIZE=1
MAX_BATCH_SIZE=4
```

## 🐳 Docker Compose Configuration

### Service Configuration

#### Main Service (lora-pilot)
```yaml
services:
  lora-pilot:
    image: vavo/lora-pilot:latest
    container_name: lora-pilot
    restart: unless-stopped
    
    # GPU support
    runtime: nvidia
    
    # Environment variables
    environment:
      - TZ=${TZ:-America/New_York}
      - HF_TOKEN=${HF_TOKEN}
      - INSTALL_AI_TOOLKIT=${INSTALL_AI_TOOLKIT:-1}
    
    # Port mappings
    ports:
      - "7878:7878"      # ControlPilot
      - "5555:5555"      # ComfyUI
      - "6666:6666"      # Kohya SS
      - "9090:9090"      # InvokeAI
      - "8888:8888"      # JupyterLab
      - "8443:8443"      # Code Server
      - "8675:8675"      # AI Toolkit UI
    
    # Volume mappings
    volumes:
      - ./workspace:/workspace
      - /var/run/docker.sock:/var/run/docker.sock  # Docker socket
    
    # Resource limits
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

### Volume Configuration

#### Workspace Volumes
```yaml
volumes:
  # Main workspace
  - ./workspace:/workspace
  
  # Model storage (optional external)
  - /path/to/models:/workspace/models
  
  # Dataset storage (optional external)
  - /path/to/datasets:/workspace/datasets
  
  # Output storage (optional external)
  - /path/to/outputs:/workspace/outputs
```

#### Development Volumes
```yaml
# Development mode mounts
volumes:
  - ./apps:/workspace/apps          # Source code
  - ./scripts:/workspace/scripts    # Scripts
  - ./config:/workspace/config      # Config files
```

### Network Configuration

#### Port Customization
```yaml
# Custom port mapping
ports:
  - "8080:7878"      # ControlPilot on 8080
  - "5556:5555"      # ComfyUI on 5556
  - "6667:6666"      # Kohya SS on 6667
```

#### Network Isolation
```yaml
# Custom network
networks:
  lora-pilot-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## 📋 Model Configuration

### Models Manifest

#### Model Entry Format
```yaml
models:
  sdxl-base:
    name: "Stable Diffusion XL Base 1.0"
    description: "SDXL 1.0 base model"
    type: "checkpoint"
    repo: "stabilityai/stable-diffusion-xl-base-1.0"
    files:
      - "sd_xl_base_1.0.safetensors"
    tags: ["sdxl", "base", "official"]
    size_gb: 6.9
    requirements:
      gpu_memory_gb: 8
      ram_gb: 16
```

#### Custom Model Addition
```yaml
# Add custom model to config/models.manifest
my-custom-model:
  name: "My Custom Model"
  description: "Custom trained model"
  type: "checkpoint"
  repo: "my-username/my-custom-model"
  files:
    - "my_model.safetensors"
  tags: ["custom", "experimental"]
  local_path: "/workspace/models/custom/my_model.safetensors"
```

### Model Categories

#### Supported Model Types
- **checkpoint**: Base models for training/inference
- **lora**: LoRA models for fine-tuning
- **textual-inversion**: Textual inversion models
- **hypernetwork**: Hypernetwork models
- **controlnet**: ControlNet models
- **vae**: VAE models
- **unet**: UNet models

#### Model Families
```yaml
families:
  sd15:
    name: "Stable Diffusion 1.5"
    base_resolution: [512, 512]
    supported_types: ["checkpoint", "lora", "textual-inversion"]
  
  sdxl:
    name: "Stable Diffusion XL"
    base_resolution: [1024, 1024]
    supported_types: ["checkpoint", "lora", "textual-inversion"]
  
  flux:
    name: "FLUX.1"
    base_resolution: [1024, 1024]
    supported_types: ["checkpoint", "lora"]
    requirements:
      gpu_memory_gb: 12
```

## 🔧 Service Configuration

### Supervisor Configuration

#### Service Definition
```ini
[program:kohya]
directory=/workspace
autostart=true
autorestart=true
startsecs=5
stdout_logfile=/workspace/logs/kohya.out.log
stderr_logfile=/workspace/logs/kohya.err.log
command=/bin/bash -lc 'source /opt/venvs/core/bin/activate && cd /workspace/apps/kohya && python gui.py --listen 0.0.0.0 --port 6666'
```

#### Environment Variables in Supervisor
```ini
[program:ai-toolkit]
environment=PATH="/opt/venvs/invoke/bin:%(ENV_PATH)s",HF_TOKEN="%(ENV_HF_TOKEN)s"
command=/bin/bash -lc 'source /opt/venvs/invoke/bin/activate && cd /opt/pilot/repos/ai-toolkit && python run.py'
```

### Component-Specific Configs

#### Kohya SS Configuration
```python
# kohya/config/config.json
{
  "training": {
    "batch_size": 1,
    "gradient_accumulation_steps": 1,
    "learning_rate": 1e-4,
    "max_train_steps": 1000,
    "save_every_n_steps": 100
  },
  "model": {
    "pretrained_model_name_or_path": "/workspace/models/stable-diffusion-xl-base-1.0",
    "v2": true,
    "resolution": 1024
  }
}
```

#### AI Toolkit Configuration
```yaml
# ai-toolkit/config/training_config.yaml
job: "extension"
config:
  name: "my_lora_training"
  process:
    - type: "diffusion_trainer"
      device: "cuda"
      network:
        type: "lora"
        linear: 32
      datasets:
        - folder_path: "/workspace/datasets/images/1_my_dataset"
      train:
        batch_size: 1
        steps: 1000
        lr: 0.0001
```

## 🚀 Advanced Configuration

### Custom Build Configuration

#### Dockerfile Build Args
```bash
# Custom build with specific versions
docker build \
  --build-arg TORCH_VERSION=2.6.0 \
  --build-arg TRANSFORMERS_VERSION=4.44.2 \
  --build-arg INSTALL_AI_TOOLKIT=1 \
  -t lora-pilot:custom .
```

#### Custom Environment File
```bash
# .env.custom
TZ=Europe/London
HF_TOKEN=hf_your_token_here
INSTALL_AI_TOOLKIT=1
AI_TOOLKIT_REF=specific_commit_hash
```

### Performance Optimization

#### GPU Memory Management
```bash
# Environment variables for memory optimization
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128,garbage_collection_threshold:0.8
CUDA_LAUNCH_BLOCKING=1
TORCH_CUDNN_V8_API_ENABLED=1
```

#### CPU Optimization
```bash
# CPU-only optimization
OMP_NUM_THREADS=8
MKL_NUM_THREADS=8
OPENBLAS_NUM_THREADS=8
```

### Security Configuration

#### Access Control
```bash
# Supervisor password
SUPERVISOR_ADMIN_PASSWORD=secure_password_here

# Service authentication
JUPYTER_TOKEN=your_jupyter_token
CODE_SERVER_PASSWORD=your_vscode_password
```

#### Network Security
```yaml
# Restrict access to localhost
ports:
  - "127.0.0.1:7878:7878"  # ControlPilot localhost only
  - "127.0.0.1:5555:5555"  # ComfyUI localhost only
```

## 📝 Configuration Management

### Environment Setup Script

```bash
#!/bin/bash
# setup-env.sh

# Copy template
cp .env.example .env

# Generate secure password
SUPERVISOR_PASSWORD=$(openssl rand -base64 32)
sed -i "s/SUPERVISOR_ADMIN_PASSWORD=/SUPERVISOR_ADMIN_PASSWORD=$SUPERVISOR_PASSWORD/" .env

# Set timezone
read -p "Enter timezone (e.g., America/New_York): " TZ
sed -i "s/TZ=America/New_York/TZ=$TZ/" .env

echo "Configuration complete! Edit .env for additional settings."
```

### Validation Script

```bash
#!/bin/bash
# validate-config.sh

# Check required files
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found"
    exit 1
fi

# Check GPU (optional)
if command -v nvidia-smi &> /dev/null; then
    echo "GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
else
    echo "Warning: No GPU detected"
fi

echo "Configuration validation complete!"
```

## 🔍 Troubleshooting Configuration

### Common Issues

#### Environment Variables Not Loading
```bash
# Check if .env is being loaded
docker-compose config
```

#### Port Conflicts
```bash
# Check what's using ports
netstat -tulpn | grep :7878
lsof -i :7878
```

#### Permission Issues
```bash
# Check workspace permissions
ls -la /workspace
chmod 755 /workspace
```

### Debug Configuration

#### Show Effective Configuration
```bash
# Show docker-compose configuration
docker-compose config

# Show environment variables in container
docker exec lora-pilot env | grep -E "(TORCH|HF_TOKEN|TZ)"
```

#### Test Service Configuration
```bash
# Test individual service
docker-compose run --rm lora-pilot bash -c 'echo $TORCH_VERSION'
```

---

*Last updated: 2025-02-11*
