# Kohya SS

Kohya SS is a battle-tested LoRA training interface that provides extensive configuration options and broad model support. It's one of the most popular tools for training custom Stable Diffusion models.

## 🎯 Overview

Kohya SS offers:
- **Extensive Model Support**: SD1.5, SDXL, SD3, and custom architectures
- **Advanced Configuration**: Fine-grained control over training parameters
- **Proven Track Record**: Used by thousands of artists and developers
- **Community Support**: Extensive documentation and community resources

## 🚀 Quick Start

### Access Kohya SS

1. **Via ControlPilot**: Services tab → Click "Open" next to Kohya SS
2. **Direct URL**: http://localhost:6666
3. **CLI**: `docker exec lora-pilot supervisorctl status kohya`

### First Training

1. **Prepare Dataset**: Use TagPilot to create and tag your dataset
2. **Configure Training**: Set basic parameters in the UI
3. **Start Training**: Monitor progress in real-time

## 📋 Training Configuration

### Basic Settings

#### Model Selection
```yaml
# Base Model Configuration
pretrained_model_name_or_path: "/workspace/models/stable-diffusion-xl-base-1.0"
v2: true                    # SDXL/SD3 support
v_parameterization: false   # Parameterization method
sdxl: true                  # SDXL specific settings
```

#### Training Parameters
```yaml
# Training Settings
training: {
  batch_size: 1                    # Images per batch
  gradient_accumulation_steps: 1   # Effective batch size
  learning_rate: 1e-4              # Learning rate
  max_train_steps: 1000           # Total training steps
  save_every_n_steps: 100          # Save checkpoint frequency
  mixed_precision: "fp16"         # Mixed precision training
  gradient_checkpointing: true     # Memory optimization
}
```

#### Dataset Configuration
```yaml
# Dataset Settings
dataset: {
  resolution: 1024                 # Image resolution
  enable_bucket: true              # Bucket resolution
  bucket_no_upscale: false         # Allow upscaling
  bucket_reso_steps: 64            # Bucket step size
  min_bucket_reso: 256             # Minimum resolution
  max_bucket_reso: 2048            # Maximum resolution
}
```

### Advanced Settings

#### Network Configuration
```yaml
# LoRA Network Settings
network: {
  network_type: "lora"            # Network type
  network_dim: 32                 # LoRA rank
  network_alpha: 32              # LoRA alpha
  network_weight_init: "normal"   # Weight initialization
  network_train_unet_only: false  # Train UNet only
  network_train_text_encoder_only: false  # Train text encoder only
}
```

#### Optimization Settings
```yaml
# Optimization
optimizer: {
  type: "AdamW8bit"              # Optimizer type
  lr_scheduler: "cosine"          # Learning rate schedule
  warmup_steps: 100              # Warmup steps
  weight_decay: 0.01             # Weight decay
  adam_beta1: 0.9                # Adam beta1
  adam_beta2: 0.999              # Adam beta2
  adam_epsilon: 1e-8             # Adam epsilon
}
```

#### Sampling Settings
```yaml
# Sample Generation
sample: {
  sampler: "ddim"                # Sampling method
  sample_every_n_steps: 100      # Sample frequency
  sample_steps: 20               # Sampling steps
  cfg_scale: 7.0                 # CFG scale
  seed: 42                       # Random seed
}
```

## 📊 Training Profiles

### Quick Test Profile
```yaml
# Quick testing (100 steps)
training: {
  max_train_steps: 100
  save_every_n_steps: 50
  learning_rate: 1e-4
  batch_size: 1
}
network: {
  network_dim: 16
  network_alpha: 16
}
```

### Medium Training Profile
```yaml
# Medium quality (500 steps)
training: {
  max_train_steps: 500
  save_every_n_steps: 100
  learning_rate: 5e-5
  batch_size: 1
}
network: {
  network_dim: 32
  network_alpha: 32
}
```

### Full Training Profile
```yaml
# Full quality (1000+ steps)
training: {
  max_train_steps: 1000
  save_every_n_steps: 100
  learning_rate: 1e-4
  batch_size: 1
  gradient_accumulation_steps: 2
}
network: {
  network_dim: 64
  network_alpha: 64
}
```

## 🖥️ Interface Guide

### Main Tabs

#### 1. Folders Tab
Configure input and output directories:
- **Train data directory**: Dataset location
- **Output directory**: Training outputs
- **Logging directory**: Log files
- **Model directory**: Base models

#### 2. Tools Tab
Dataset preparation and utilities:
- **Image bucketing**: Organize images by resolution
- **Captioning**: Add text captions
- **Latent caching**: Pre-compute latents

#### 3. Training Tab
Main training configuration:
- **Model settings**: Base model selection
- **Network settings**: LoRA configuration
- **Optimization**: Training parameters
- **Save settings**: Checkpoint configuration

#### 4. Advanced Tab
Advanced configuration options:
- **Memory optimization**: Gradient checkpointing
- **Mixed precision**: FP16/BF16 training
- **Custom settings**: Expert parameters

### Training Process

#### Step 1: Configure Folders
```bash
# Set paths in UI
Train data directory: /workspace/datasets/images/1_my_dataset
Output directory: /workspace/outputs/my_lora
Logging directory: /workspace/outputs/my_lora/_logs
Model directory: /workspace/models/stable-diffusion-xl-base-1.0
```

#### Step 2: Prepare Dataset
```bash
# Use bucketing for efficiency
Enable bucket: true
Bucket resolution steps: 64
Min bucket resolution: 256
Max bucket resolution: 1024
```

#### Step 3: Configure Training
```bash
# Basic settings
Network dim: 32
Network alpha: 32
Learning rate: 1e-4
Max train steps: 1000
Batch size: 1
```

#### Step 4: Start Training
```bash
# Click "Start training" button
Monitor progress in real-time
Check logs for any issues
```

## 📈 Performance Optimization

### Memory Optimization

#### Gradient Checkpointing
```yaml
# Enable gradient checkpointing
gradient_checkpointing: true

# Reduces memory usage by ~40%
# Slightly increases training time
```

#### Mixed Precision
```yaml
# Use mixed precision
mixed_precision: "fp16"

# Reduces memory usage by ~50%
# Maintains training quality
```

#### CPU Offloading
```yaml
# Enable CPU offloading (if needed)
cpu_offload: true

# Moves some computations to CPU
# Significantly slower, but reduces VRAM
```

### Speed Optimization

#### Batch Size
```yaml
# Increase batch size if VRAM allows
batch_size: 2  # If you have 12GB+ VRAM
batch_size: 4  # If you have 16GB+ VRAM
```

#### Gradient Accumulation
```yaml
# Effective batch size = batch_size * gradient_accumulation_steps
gradient_accumulation_steps: 2  # Effective batch size = 2
gradient_accumulation_steps: 4  # Effective batch size = 4
```

#### Latent Caching
```yaml
# Cache latents to disk
cache_latents: true
cache_latents_to_disk: true

# Faster training after initial cache
# Uses disk space for cache
```

## 🔧 Troubleshooting

### Common Issues

#### CUDA Out of Memory
```bash
# Solutions:
1. Reduce batch size to 1
2. Enable gradient checkpointing
3. Use mixed precision (fp16)
4. Reduce network dim
5. Clear GPU cache: docker exec lora-pilot python -c "import torch; torch.cuda.empty_cache()"
```

#### Training Not Progressing
```bash
# Check:
1. Dataset has images and captions
2. Model path is correct
3. Learning rate is appropriate
4. No errors in logs
```

#### Poor Quality Results
```bash
# Solutions:
1. Increase training steps
2. Improve dataset quality
3. Adjust learning rate
4. Try different network dim
5. Use better captions
```

### Debug Commands

#### Check Training Status
```bash
# Check if Kohya is running
docker exec lora-pilot supervisorctl status kohya

# View training logs
docker exec lora-pilot tail -f /workspace/outputs/my_lora/_logs/train.log

# Check GPU usage
docker exec lora-pilot nvidia-smi
```

#### Validate Dataset
```bash
# Check dataset structure
docker exec lora-pilot ls -la /workspace/datasets/images/1_my_dataset

# Check image count
docker exec lora-pilot find /workspace/datasets/images/1_my_dataset -name "*.jpg" | wc -l

# Check captions
docker exec lora-pilot find /workspace/datasets/images/1_my_dataset -name "*.txt" | wc -l
```

## 📚 Advanced Features

### Custom Training Scripts

#### DreamBooth Training
```yaml
# DreamBooth configuration
dreambooth: {
  concepts: [
    {
      instance_prompt: "photo of sks person"
      instance_data_dir: "/workspace/datasets/images/1_person"
      class_prompt: "photo of a person"
      class_data_dir: "/workspace/datasets/images/class_person"
    }
  ]
}
```

#### Textual Inversion
```yaml
# Textual inversion training
textual_inversion: {
  num_vectors_per_token: 10
  max_train_steps: 1000
  learning_rate: 3e-4
}
```

### Integration with Other Tools

#### Use Trained LoRA in ComfyUI
```bash
# Trained LoRA location
/workspace/outputs/my_lora/last.safetensors

# Load in ComfyUI
1. Add "Load LoRA" node
2. Set model path to trained LoRA
3. Connect to model input
4. Adjust strength (0.0-1.0)
```

#### Use Trained LoRA in InvokeAI
```bash
# Copy LoRA to InvokeAI models
cp /workspace/outputs/my_lora/last.safetensors /workspace/models/loras/

# Load in InvokeAI UI
1. Select LoRA from dropdown
2. Adjust weight
3. Generate images
```

## 🎯 Best Practices

### Dataset Preparation
1. **Quality over quantity**: 10-20 high-quality images better than 100 poor ones
2. **Consistent style**: Keep visual style consistent across dataset
3. **Good captions**: Detailed, descriptive captions improve results
4. **Proper resolution**: Use appropriate resolution for model (512x512 for SD1.5, 1024x1024 for SDXL)

### Training Configuration
1. **Start small**: Test with 100 steps first
2. **Monitor progress**: Check samples every 100 steps
3. **Adjust learning rate**: Too high = unstable, too low = slow learning
4. **Save frequently**: Save checkpoints every 100 steps

### Quality Improvement
1. **Multiple iterations**: Train multiple times with different settings
2. **Ensemble models**: Combine multiple LoRAs
3. **Fine-tune**: Continue training from best checkpoint
4. **Test thoroughly**: Test with various prompts and settings

---

*Last updated: 2025-02-11*
