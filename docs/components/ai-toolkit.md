# AI Toolkit

AI Toolkit is a modern training stack for diffusion models, specifically designed for training FLUX.1 and other latest models. It provides a Next.js interface with Gradio backend and integrates seamlessly with the LoRA Pilot workspace.

##  Overview

AI Toolkit offers:
- **Modern Architecture**: Built for latest diffusion models
- **FLUX.1 Support**: Native support for FLUX.1 models
- **Next.js Interface**: Modern web-based UI
- **Gradio Backend**: Python-based training backend
- **Workspace Integration**: Full integration with LoRA Pilot

##  Quick Start

### Access AI Toolkit

1. **Via ControlPilot**: Services tab → Click "Open" next to AI Toolkit
2. **Direct URL**: http://localhost:8675
3. **CLI**: `docker exec lora-pilot supervisorctl status ai-toolkit`

### First Training

1. **Prepare Dataset**: Use TagPilot to create your dataset
2. **Configure Training**: Use the web interface to set parameters
3. **Start Training**: Monitor progress through the UI

##  Training Configuration

### Basic Configuration File

AI Toolkit uses YAML configuration files for training:

```yaml
---
job: "extension"
config:
  name: "my_flux_lora"
  process:
    - type: "diffusion_trainer"
      training_folder: "/workspace/outputs/ai-toolkit"
      sqlite_db_path: "/workspace/config/ai-toolkit/aitk_db.db"
      device: "cuda"
      trigger_word: "yasmine"
      performance_log_every: 10
      network:
        type: "lora"
        linear: 32
        linear_alpha: 32
        conv: 16
        conv_alpha: 16
      save:
        dtype: "bf16"
        save_every: 250
        max_step_saves_to_keep: 4
        save_format: "diffusers"
      datasets:
        - folder_path: "/workspace/datasets/images/1_yasmine"
          resolution: [512, 768, 1024]
          num_repeats: 1
      train:
        batch_size: 1
        steps: 3000
        gradient_accumulation: 1
        train_unet: true
        train_text_encoder: false
        gradient_checkpointing: true
        optimizer: "adamw8bit"
        lr: 0.0001
        dtype: "bf16"
      model:
        name_or_path: "black-forest-labs/FLUX.1-schnell"
        low_vram: false
      sample:
        sampler: "ddpm"
        sample_every: 250
        width: 1024
        height: 1024
        prompts:
          - "a woman holding a coffee cup, in a beanie, sitting at a cafe"
        seed: 42
```

### Configuration Sections

#### Network Configuration
```yaml
network:
  type: "lora"                    # Network type
  linear: 32                      # Linear layers rank
  linear_alpha: 32               # Linear layers alpha
  conv: 16                       # Convolutional layers rank
  conv_alpha: 16                 # Convolutional layers alpha
  lokr_full_rank: true           # LoKR full rank
  lokr_factor: -1                # LoKR factor
```

#### Dataset Configuration
```yaml
datasets:
  - folder_path: "/workspace/datasets/images/1_yasmine"
    mask_path: null               # Mask path (optional)
    default_caption: ""           # Default caption
    caption_ext: "txt"            # Caption file extension
    caption_dropout_rate: 0.05    # Caption dropout rate
    cache_latents_to_disk: false  # Cache latents to disk
    is_reg: false                 # Regularization dataset
    network_weight: 1             # Network weight
    resolution: [512, 768, 1024]  # Supported resolutions
    num_frames: 1                 # Number of frames (for video)
    flip_x: false                 # Flip horizontally
    flip_y: false                 # Flip vertically
    num_repeats: 1                # Dataset repeats
```

#### Training Configuration
```yaml
train:
  batch_size: 1                   # Batch size
  steps: 3000                     # Training steps
  gradient_accumulation: 1        # Gradient accumulation
  train_unet: true                # Train UNet
  train_text_encoder: false       # Train text encoder
  gradient_checkpointing: true    # Gradient checkpointing
  optimizer: "adamw8bit"           # Optimizer
  optimizer_params:
    weight_decay: 0.0001         # Weight decay
  lr: 0.0001                     # Learning rate
  ema_config:
    use_ema: false               # Use EMA
    ema_decay: 0.99              # EMA decay
  dtype: "bf16"                   # Data type
```

#### Model Configuration
```yaml
model:
  name_or_path: "black-forest-labs/FLUX.1-schnell"  # Model path
  quantize: false                 # Quantization
  qtype: "qfloat8"               # Quantization type
  quantize_te: false              # Quantize text encoder
  qtype_te: "qfloat8"            # Text encoder quantization
  arch: "flux"                   # Architecture
  low_vram: false                 # Low VRAM mode
  model_kwargs: {}               # Additional model arguments
```

## 🖥️ Interface Guide

### Web Interface

#### Main Dashboard
- **Job Queue**: View and manage training jobs
- **Active Jobs**: Monitor current training progress
- **Completed Jobs**: View finished training results
- **Configuration**: Create and edit training configs

#### Job Creation
1. **Select Model**: Choose base model (FLUX.1, SDXL, etc.)
2. **Configure Dataset**: Select dataset and settings
3. **Set Training Parameters**: Configure training options
4. **Start Training**: Submit job to queue

#### Progress Monitoring
- **Real-time Progress**: View training progress live
- **Sample Generation**: See generated samples
- **Resource Usage**: Monitor GPU and memory usage
- **Logs**: View detailed training logs

### Configuration Management

#### Creating New Config
1. Click "New Configuration"
2. Fill in configuration parameters
3. Test configuration with dry run
4. Save configuration

#### Editing Config
1. Select existing configuration
2. Modify parameters
3. Validate configuration
4. Save changes

##  Training Profiles

### Quick Test Profile
```yaml
# Quick FLUX.1 test (500 steps)
train:
  steps: 500
  batch_size: 1
  lr: 0.0001
network:
  linear: 16
  linear_alpha: 16
save:
  save_every: 100
```

### Medium Training Profile
```yaml
# Medium FLUX.1 training (1500 steps)
train:
  steps: 1500
  batch_size: 1
  lr: 0.0001
  gradient_checkpointing: true
network:
  linear: 32
  linear_alpha: 32
save:
  save_every: 250
```

### Full Training Profile
```yaml
# Full FLUX.1 training (3000+ steps)
train:
  steps: 3000
  batch_size: 1
  lr: 0.0001
  gradient_checkpointing: true
  gradient_accumulation: 2
network:
  linear: 64
  linear_alpha: 64
save:
  save_every: 250
  max_step_saves_to_keep: 8
```

##  Advanced Features

### Model Support

#### FLUX.1 Models
```yaml
# FLUX.1 Schnell
model:
  name_or_path: "black-forest-labs/FLUX.1-schnell"
  arch: "flux"

# FLUX.1 Dev
model:
  name_or_path: "black-forest-labs/FLUX.1-dev"
  arch: "flux"
```

#### SDXL Models
```yaml
# SDXL Base
model:
  name_or_path: "stabilityai/stable-diffusion-xl-base-1.0"
  arch: "sdxl"
```

#### SD3 Models
```yaml
# SD3 Medium
model:
  name_or_path: "stabilityai/stable-diffusion-3-medium"
  arch: "sd3"
```

### Optimization Techniques

#### Memory Optimization
```yaml
# Low VRAM mode
model:
  low_vram: true

# Gradient checkpointing
train:
  gradient_checkpointing: true

# Mixed precision
train:
  dtype: "bf16"
```

#### Speed Optimization
```yaml
# Gradient accumulation
train:
  gradient_accumulation: 2

# Cache latents
datasets:
  - cache_latents_to_disk: true
```

### Sampling Configuration

#### Custom Prompts
```yaml
sample:
  sampler: "ddpm"
  sample_every: 250
  width: 1024
  height: 1024
  prompts:
    - "a woman holding a coffee cup, in a beanie, sitting at a cafe"
    - "woman playing the guitar, on stage, singing a song"
    - "hipster man with a beard, building a chair, in a wood shop"
  neg: ""                       # Negative prompt
  seed: 42                       # Random seed
  walk_seed: true                # Vary seed
  guidance_scale: 6.0            # CFG scale
  sample_steps: 25               # Sampling steps
```

##  CLI Usage

### Command Line Interface

AI Toolkit also provides CLI access:

```bash
# Access container shell
docker exec -it lora-pilot bash

# Run training with config file
cd /opt/pilot/repos/ai-toolkit
python run.py /path/to/config.yaml

# List available configs
python run.py --list-configs

# Validate config
python run.py --validate /path/to/config.yaml
```

### Database Management

```bash
# Check database status
cd /opt/pilot/repos/ai-toolkit
npx prisma db status

# Reset database
npx prisma db push --force-reset

# View database content
sqlite3 /workspace/config/ai-toolkit/aitk_db.db ".tables"
```

##  Troubleshooting

### Common Issues

#### Model Download Errors
```bash
# Problem: 401 Unauthorized for FLUX.1 models
# Solution: Set Hugging Face token
export HF_TOKEN="your_hf_token_here"
huggingface-cli login
```

#### Database Connection Errors
```bash
# Problem: Database connection failed
# Solution: Check database path and permissions
mkdir -p /workspace/config/ai-toolkit
chmod 755 /workspace/config/ai-toolkit
```

#### Out of Memory Errors
```bash
# Problem: CUDA out of memory
# Solution: Enable low VRAM mode
model:
  low_vram: true

# Or reduce batch size
train:
  batch_size: 1
```

### Debug Commands

#### Check Service Status
```bash
# Check AI Toolkit service
docker exec lora-pilot supervisorctl status ai-toolkit

# View logs
docker exec lora-pilot supervisorctl tail -100 ai-toolkit
```

#### Validate Configuration
```bash
# Validate config file
cd /opt/pilot/repos/ai-toolkit
python run.py --validate /path/to/config.yaml
```

#### Test Model Access
```bash
# Test model download
python -c "
from huggingface_hub import hf_hub_download
try:
    hf_hub_download('black-forest-labs/FLUX.1-schnell', 'transformer/config.json')
    print('✅ FLUX.1 accessible')
except Exception as e:
    print('❌', e)
"
```

##  Best Practices

### Configuration Best Practices
1. **Start Small**: Test with 500 steps first
2. **Monitor Progress**: Check samples every 250 steps
3. **Save Frequently**: Save checkpoints every 250 steps
4. **Use Appropriate Learning Rate**: 1e-4 for most cases

### Dataset Preparation
1. **High-Quality Images**: Use 15-30 high-quality images
2. **Consistent Style**: Maintain consistent visual style
3. **Good Captions**: Detailed, descriptive captions
4. **Proper Resolution**: Use 1024x1024 for FLUX.1

### Performance Optimization
1. **Use BF16**: Reduces memory usage, maintains quality
2. **Enable Gradient Checkpointing**: Saves VRAM
3. **Cache Latents**: Faster training after initial setup
4. **Monitor Resources**: Keep an eye on GPU memory

##  Integration with Other Tools

### Using Trained Models

#### In ComfyUI
```bash
# Trained model location
/workspace/outputs/ai-toolkit/your_model_name/

# Load in ComfyUI
1. Add "Load LoRA" node
2. Set model path to trained LoRA
3. Connect to FLUX.1 model
4. Adjust strength (0.0-1.0)
```

#### In InvokeAI
```bash
# Copy LoRA to InvokeAI
cp /workspace/outputs/ai-toolkit/your_model_name/*.safetensors /workspace/models/loras/

# Load in InvokeAI
1. Select FLUX.1 model
2. Add LoRA from dropdown
3. Adjust weight
4. Generate images
```

### Workflow Integration
1. **Dataset Creation**: Use TagPilot for dataset preparation
2. **Training**: Use AI Toolkit for FLUX.1 training
3. **Testing**: Use ComfyUI for inference testing
4. **Management**: Use ControlPilot for overall management

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


